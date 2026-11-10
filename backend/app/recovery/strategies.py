"""Three ways to recover the day after a ground stop.

1. original  - keep every crew on its planned trip, never reassign.
               This is what happens when the crew-tracking system can't keep up.
2. greedy    - go flight by flight and grab the earliest legal crew nearby.
               Simple, fast, but short-sighted.
3. optimized - every hour, solve an assignment problem with OR-Tools CP-SAT
               that looks at all open flights and all crews together.
"""
from ortools.sat.python import cp_model

from app.config import BATCH_MINUTES, HUB, MAX_DELAY_MINUTES, MIN_TURN_MINUTES
from app.recovery.models import Assignment, Crew, Leg
from app.recovery.rules import can_fly, duty_left_after, fly

# A 100%-risk flight reserves an extra 30 minutes of duty. Tested 30/60/90 across
# ten scenarios; 30 gave the fewest cancellations.
RISK_CUSHION_MINUTES = 30


def original_plan(legs: list[Leg], crews: list[Crew]) -> list[Assignment]:
    crew_by_id = {c.id: c for c in crews}
    plan = []
    for leg in sorted(legs, key=lambda l: (l.earliest_dep, l.id)):
        crew = crew_by_id[leg.original_crew]
        dep = max(leg.earliest_dep, crew.ready_at)
        if dep - leg.earliest_dep <= MAX_DELAY_MINUTES and can_fly(crew, leg, dep):
            fly(crew, leg, dep)
            plan.append(Assignment(leg.id, crew.id, dep))
        else:
            plan.append(Assignment(leg.id, None, None))
    return plan


def greedy(legs: list[Leg], crews: list[Crew]) -> list[Assignment]:
    plan = []
    for leg in sorted(legs, key=lambda l: (l.earliest_dep, l.id)):
        best = None
        for crew in crews:
            dep = max(leg.earliest_dep, crew.ready_at)
            if dep - leg.earliest_dep > MAX_DELAY_MINUTES or not can_fly(crew, leg, dep):
                continue
            # Earliest departure wins; ties go to the planned crew, then non-reserves.
            key = (dep, crew.id != leg.original_crew, crew.is_reserve)
            if best is None or key < best[0]:
                best = (key, crew, dep)
        if best:
            _, crew, dep = best
            fly(crew, leg, dep)
            plan.append(Assignment(leg.id, crew.id, dep))
        else:
            plan.append(Assignment(leg.id, None, None))
    return plan


def _return_leg_block(leg: Leg) -> int:
    """Outbound flights must leave the crew enough duty to fly home again."""
    return leg.block if leg.origin == HUB else 0


def optimized(legs: list[Leg], crews: list[Crew], use_risk: bool = True) -> list[Assignment]:
    open_legs = {l.id: l for l in legs}
    plan: list[Assignment] = []
    t = min(l.earliest_dep for l in legs)
    end = max(l.earliest_dep for l in legs) + MAX_DELAY_MINUTES

    while open_legs and t <= end:
        window_end = t + BATCH_MINUTES
        # Cancel flights that can no longer leave within the delay limit.
        for leg in list(open_legs.values()):
            if leg.earliest_dep + MAX_DELAY_MINUTES < t:
                plan.append(Assignment(leg.id, None, None))
                del open_legs[leg.id]

        model = cp_model.CpModel()
        options = []   # (variable, leg, crew, departure)
        for leg in open_legs.values():
            if leg.earliest_dep >= window_end:
                continue
            for crew in crews:
                dep = max(leg.earliest_dep, crew.ready_at, t)
                if dep >= window_end or dep - leg.earliest_dep > MAX_DELAY_MINUTES:
                    continue
                if not can_fly(crew, leg, dep):
                    continue
                left = duty_left_after(crew, leg, dep)
                score = 1000 - 2 * (dep - leg.earliest_dep)
                if crew.id == leg.original_crew:
                    score += 60          # keep planned trips together when possible
                if crew.is_reserve:
                    score -= 40          # save reserves for when they're really needed
                # Look ahead: don't send a crew out that can't legally come back.
                needed = _return_leg_block(leg) + MIN_TURN_MINUTES
                # Use the delay model: a risky flight may land late, so the crew
                # needs a cushion of duty time on top of the return trip.
                if use_risk:
                    needed += int(leg.risk * RISK_CUSHION_MINUTES)
                score += 400 if left >= needed else -700
                var = model.NewBoolVar(f"x_{leg.id}_{crew.id}")
                options.append((var, leg, crew, dep, score))

        if options:
            for leg_id in {o[1].id for o in options}:
                model.AddAtMostOne(o[0] for o in options if o[1].id == leg_id)
            for crew_id in {o[2].id for o in options}:
                model.AddAtMostOne(o[0] for o in options if o[2].id == crew_id)
            model.Maximize(sum(o[4] * o[0] for o in options))
            solver = cp_model.CpSolver()
            # One worker and a fixed seed make results identical on every computer.
            # Each hourly problem is small, so the solver still proves the best answer quickly.
            solver.parameters.num_workers = 1
            solver.parameters.random_seed = 42
            solver.parameters.max_time_in_seconds = 10.0
            solver.Solve(model)
            for var, leg, crew, dep, _ in options:
                if solver.Value(var):
                    fly(crew, leg, dep)
                    plan.append(Assignment(leg.id, crew.id, dep))
                    del open_legs[leg.id]
        t = window_end

    plan += [Assignment(leg_id, None, None) for leg_id in open_legs]
    return plan


STRATEGIES = {
    "original": original_plan,
    "greedy": greedy,
    "optimized": optimized,
}
