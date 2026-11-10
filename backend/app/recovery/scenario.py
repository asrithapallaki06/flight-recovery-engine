"""Build one operating day at the hub, plan crews for it, then apply a ground stop.

The day uses the same spoke airports and block times as the training data.
Every crew is based at the hub and flies out-and-back trips ("rotations").
"""
import copy

import numpy as np
import pandas as pd

from app.config import HUB, MAX_DUTY_MINUTES, MIN_TURN_MINUTES, REPORT_MINUTES, SPOKES
from app.predictor.model import predict_risk
from app.recovery.models import Crew, Leg

SIM_DATE = "2026-07-19"   # a summer Sunday, peak thunderstorm season
TURN_AT_SPOKE = 45        # planned minutes on the ground at the outstation
PLANNING_BUFFER = 45      # planners leave a little slack below the legal duty limit


def build_schedule(seed: int = 11) -> list[Leg]:
    """Out-and-back rotations to every spoke across the day."""
    rng = np.random.default_rng(seed)
    legs, next_id = [], 0
    for spoke, block in SPOKES.items():
        # Busy hub: short routes run many times a day, long routes fewer.
        n_rotations = 5 if block <= 120 else 3 if block <= 200 else 2
        first = 6 * 60 + int(rng.integers(0, 4)) * 15
        last = 22 * 60 + 30 - (2 * block + TURN_AT_SPOKE)   # home by 10:30 PM
        starts = np.linspace(first, max(first, last), n_rotations)
        for start in starts:
            out_dep = int(round(start / 15) * 15)
            ret_dep = out_dep + block + TURN_AT_SPOKE
            for origin, dest, dep in ((HUB, spoke, out_dep), (spoke, HUB, ret_dep)):
                legs.append(Leg(next_id, f"{100 + next_id}", origin, dest, dep, block))
                next_id += 1
    return sorted(legs, key=lambda l: l.sched_dep)


def build_crews(legs: list[Leg], reserves: int) -> list[Crew]:
    """Chain rotations into crew trips that stay well inside duty limits."""
    by_id = {l.id: l for l in legs}
    rotations = [(l, by_id[l.id + 1]) for l in legs if l.origin == HUB]
    rotations.sort(key=lambda r: r[0].sched_dep)
    crews: list[Crew] = []
    for out_leg, ret_leg in rotations:
        best = None
        for crew in crews:
            last = by_id[crew.pairing[-1]]
            fits_turn = last.sched_arr + MIN_TURN_MINUTES <= out_leg.sched_dep
            fits_duty = ret_leg.sched_arr - crew.duty_start <= MAX_DUTY_MINUTES - PLANNING_BUFFER
            if fits_turn and fits_duty and (best is None or last.sched_arr > by_id[best.pairing[-1]].sched_arr):
                best = crew
        if best is None:
            best = Crew(len(crews), HUB, duty_start=out_leg.sched_dep - REPORT_MINUTES)
            best.ready_at = out_leg.sched_dep
            crews.append(best)
        best.pairing += [out_leg.id, ret_leg.id]
        out_leg.original_crew = ret_leg.original_crew = best.id
    for i in range(reserves):
        crews.append(Crew(len(crews), HUB, ready_at=5 * 60, is_reserve=True))
    return crews


def storm_weather(gs_start: int, gs_end: int) -> pd.DataFrame:
    """Hourly hub weather for the simulated day: storms around the ground stop."""
    rows = []
    for hour in range(24):
        storm = gs_start // 60 - 1 <= hour < -(-gs_end // 60)
        rows.append({"HOUR": hour, "TEMP_F": 88 if 11 <= hour <= 18 else 76,
                     "PRECIP_IN": 0.8 if storm else 0.0, "WIND_KT": 25 if storm else 8,
                     "VIS_MI": 1.5 if storm else 10, "THUNDER": int(storm)})
    return pd.DataFrame(rows)


def score_risk(legs: list[Leg], weather: pd.DataFrame) -> None:
    """Attach the model's delay risk to every leg.

    The model was trained on hub departures. For flights flying into the hub we
    use the hub weather at arrival time, since that's what holds them up.
    """
    rows = []
    for leg in legs:
        hour = (leg.sched_dep if leg.origin == HUB else leg.sched_arr) // 60 % 24
        spoke = leg.dest if leg.origin == HUB else leg.origin
        rows.append({"FL_DATE": SIM_DATE, "HOUR": hour, "OP_CARRIER": "DL", "DEST": spoke,
                     "DISTANCE": int(SPOKES[spoke] * 7.2)})
    frame = pd.DataFrame(rows).merge(weather, on="HOUR", how="left")
    for leg, risk in zip(legs, predict_risk(frame)):
        leg.risk = risk


def add_surprise_delays(legs: list[Leg], seed: int = 23) -> None:
    """Some flights hold in the air or taxi longer than planned, more often when risky.

    Fixed by a seed, so every strategy faces exactly the same surprises.
    """
    rng = np.random.default_rng(seed)
    for leg in legs:
        if rng.random() < 0.6 * leg.risk:
            leg.surprise_delay = int(rng.gamma(2.0, 20.0))


def apply_ground_stop(legs: list[Leg], gs_start: int, gs_end: int) -> None:
    """No departures from or arrivals into the hub between gs_start and gs_end."""
    for leg in legs:
        leg.earliest_dep = leg.sched_dep
        if leg.origin == HUB and gs_start <= leg.sched_dep < gs_end:
            leg.earliest_dep = gs_end
        if leg.dest == HUB and gs_start <= leg.sched_arr < gs_end:
            leg.earliest_dep = max(leg.sched_dep, gs_end - leg.block)


def build_scenario(gs_start: int, gs_end: int, reserves: int):
    """Return (legs, crews) ready for any recovery strategy to work on."""
    legs = build_schedule()
    crews = build_crews(legs, reserves)
    score_risk(legs, storm_weather(gs_start, gs_end))
    add_surprise_delays(legs)
    apply_ground_stop(legs, gs_start, gs_end)
    return legs, crews


def fresh_copy(legs, crews):
    """Each strategy gets its own copy so one can't change another's starting point."""
    return copy.deepcopy(legs), copy.deepcopy(crews)
