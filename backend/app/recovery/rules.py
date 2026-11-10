"""Crew legality rules, plus a checker that proves a plan follows them.

These are simplified versions of FAA Part 117 duty limits: a crew can't work
more than MAX_DUTY_MINUTES from report time to its last arrival, needs
MIN_TURN_MINUTES between flights, and must physically be at the departure airport.
"""
from app.config import MAX_DUTY_MINUTES, MIN_TURN_MINUTES, REPORT_MINUTES
from app.recovery.models import Assignment, Crew, Leg


def duty_start_if_flying(crew: Crew, dep: int) -> int:
    return crew.duty_start if crew.duty_start is not None else dep - REPORT_MINUTES


def duty_used_so_far(crew: Crew, dep: int) -> int:
    """Duty already used by `dep`, counting delays the crew actually experienced."""
    return dep - duty_start_if_flying(crew, dep)


def can_fly(crew: Crew, leg: Leg, dep: int) -> bool:
    """True if this crew can legally fly this leg departing at `dep`.

    Uses the scheduled block time, since that's all anyone knows before takeoff.
    """
    if crew.location != leg.origin or crew.ready_at > dep:
        return False
    return duty_used_so_far(crew, dep) + leg.block <= MAX_DUTY_MINUTES


def duty_left_after(crew: Crew, leg: Leg, dep: int) -> int:
    """Minutes of legal duty the crew would still have after landing."""
    return MAX_DUTY_MINUTES - (dep + leg.block - duty_start_if_flying(crew, dep))


def fly(crew: Crew, leg: Leg, dep: int) -> None:
    """Update the crew's state after it flies a leg.

    Planners only know the scheduled block time, but the crew lands when the
    flight actually lands, including any surprise holding or taxi delay.
    """
    crew.duty_start = duty_start_if_flying(crew, dep)
    crew.location = leg.dest
    crew.ready_at = dep + leg.block + leg.surprise_delay + MIN_TURN_MINUTES


def validate(legs: dict[int, Leg], crews: dict[int, Crew], plan: list[Assignment]) -> list[str]:
    """Replay a plan from each crew's starting state and list every rule it breaks.

    An empty list means the plan is legal. The tests run this on every strategy.
    """
    errors = []
    by_crew: dict[int, list[tuple[int, Leg]]] = {}
    for a in plan:
        if a.crew_id is not None:
            if a.actual_dep < legs[a.leg_id].earliest_dep:
                errors.append(f"leg {a.leg_id} departs before it is allowed to")
            by_crew.setdefault(a.crew_id, []).append((a.actual_dep, legs[a.leg_id]))
    for crew_id, flights in by_crew.items():
        start = crews[crew_id]
        crew = Crew(crew_id, start.location, start.ready_at, start.duty_start, start.is_reserve)
        for dep, leg in sorted(flights, key=lambda x: x[0]):
            if not can_fly(crew, leg, dep):
                errors.append(f"crew {crew_id} cannot legally fly leg {leg.id} at {dep}")
            fly(crew, leg, dep)
    return errors
