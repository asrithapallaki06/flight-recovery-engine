"""Run every strategy on the same disrupted day and score the results."""
from app.config import HUB, MAX_DUTY_MINUTES
from app.recovery.models import Assignment, Crew, Leg
from app.recovery.rules import fly, validate
from app.recovery.scenario import build_scenario, fresh_copy
from app.recovery.strategies import STRATEGIES


def format_time(minutes: int | None) -> str | None:
    if minutes is None:
        return None
    return f"{minutes // 60 % 24:02d}:{minutes % 60:02d}"


def crew_days(legs: list[Leg], start_crews: list[Crew], plan: list[Assignment]) -> list[dict]:
    """Replay the plan crew by crew: what each one flew, and where it ended up.

    The dashboard draws this as a crew timeline, the view real crew schedulers use.
    """
    by_id = {l.id: l for l in legs}
    crews = {c.id: Crew(c.id, c.location, c.ready_at, c.duty_start, c.is_reserve) for c in start_crews}
    flights: dict[int, list[dict]] = {c.id: [] for c in start_crews}
    for a in sorted((a for a in plan if a.crew_id is not None), key=lambda a: a.actual_dep):
        leg = by_id[a.leg_id]
        fly(crews[a.crew_id], leg, a.actual_dep)
        flights[a.crew_id].append({
            "flight_no": leg.flight_no, "origin": leg.origin, "dest": leg.dest,
            "dep": a.actual_dep, "arr": a.actual_dep + leg.block + leg.surprise_delay,
            "delay_min": a.actual_dep - leg.sched_dep,
        })
    days = []
    for c in start_crews:
        crew = crews[c.id]
        days.append({
            "crew": c.id,
            "reserve": c.is_reserve,
            "flights": flights[c.id],
            "duty_limit_at": crew.duty_start + MAX_DUTY_MINUTES if crew.duty_start is not None else None,
            "ends_at": crew.location,
            "stranded": bool(flights[c.id]) and crew.location != HUB,
        })
    return days


def score(legs: list[Leg], crews: list[Crew], plan: list[Assignment], gs_end: int) -> dict:
    by_id = {l.id: l for l in legs}
    flown = [a for a in plan if a.crew_id is not None]
    delays = [a.actual_dep - by_id[a.leg_id].sched_dep for a in flown]
    used = {a.crew_id for a in flown}
    days = crew_days(legs, crews, plan)

    # "Back on schedule": the scheduled time of the last flight that was
    # cancelled or left 30+ minutes late. Everything after it ran normally.
    status = {a.leg_id: a for a in plan}
    disrupted = [l.sched_dep for l in legs if status[l.id].crew_id is None
                 or status[l.id].actual_dep - l.sched_dep >= 30]
    recovered_at = max(disrupted) if disrupted else None

    # Cumulative flights flown by each hour, vs. the original schedule.
    curve = []
    for hour in range(5, 27):
        curve.append({
            "hour": hour,
            "scheduled": sum(1 for l in legs if l.sched_dep < hour * 60),
            "flown": sum(1 for a in flown if a.actual_dep < hour * 60),
        })

    return {
        "metrics": {
            "flights": len(legs),
            "completed": len(flown),
            "cancelled": len(legs) - len(flown),
            "completion_rate": round(len(flown) / len(legs), 3),
            "avg_delay_min": round(sum(delays) / len(delays), 1) if delays else 0,
            "on_time_rate": round(sum(d < 15 for d in delays) / len(legs), 3),
            "stranded_crews": sum(d["stranded"] for d in days),
            "reserves_used": sum(1 for cid in used if next(c for c in crews if c.id == cid).is_reserve),
            "last_disrupted_flight": format_time(recovered_at),
        },
        "curve": curve,
        "crews": days,
        "flights": [
            {
                "id": a.leg_id,
                "flight_no": by_id[a.leg_id].flight_no,
                "route": f"{by_id[a.leg_id].origin}-{by_id[a.leg_id].dest}",
                "sched_dep": format_time(by_id[a.leg_id].sched_dep),
                "actual_dep": format_time(a.actual_dep),
                "delay_min": None if a.crew_id is None else a.actual_dep - by_id[a.leg_id].sched_dep,
                "status": "cancelled" if a.crew_id is None else "flown",
                "crew": a.crew_id,
                "risk": by_id[a.leg_id].risk,
            }
            for a in sorted(plan, key=lambda a: by_id[a.leg_id].sched_dep)
        ],
    }


def run(gs_start: int, gs_end: int, reserves: int, use_risk: bool = True) -> dict:
    legs, crews = build_scenario(gs_start, gs_end, reserves)
    results = {}
    for name, strategy in STRATEGIES.items():
        work_legs, work_crews = fresh_copy(legs, crews)
        if name == "optimized":
            plan = strategy(work_legs, work_crews, use_risk=use_risk)
        else:
            plan = strategy(work_legs, work_crews)
        errors = validate({l.id: l for l in legs}, {c.id: c for c in crews}, plan)
        if errors:
            raise RuntimeError(f"{name} produced an illegal plan: {errors[:3]}")
        results[name] = score(legs, crews, plan, gs_end)
    return {
        "scenario": {"ground_stop": [format_time(gs_start), format_time(gs_end)], "reserve_crews": reserves,
                     "use_risk": use_risk, "planned_crews": sum(not c.is_reserve for c in crews)},
        "strategies": results,
    }
