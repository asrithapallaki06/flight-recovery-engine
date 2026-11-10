"""End-to-end tests for the recovery strategies."""
import pytest

from app.recovery.rules import validate
from app.recovery.scenario import build_scenario, fresh_copy
from app.recovery.simulate import run
from app.recovery.strategies import STRATEGIES

SCENARIOS = [(14 * 60, 17 * 60, 6), (13 * 60, 18 * 60, 6), (15 * 60, 19 * 60, 0)]


@pytest.mark.parametrize("gs_start,gs_end,reserves", SCENARIOS)
@pytest.mark.parametrize("name", list(STRATEGIES))
def test_every_strategy_produces_a_legal_plan(name, gs_start, gs_end, reserves):
    legs, crews = build_scenario(gs_start, gs_end, reserves)
    work_legs, work_crews = fresh_copy(legs, crews)
    plan = STRATEGIES[name](work_legs, work_crews)
    assert len(plan) == len(legs)                          # every flight gets a decision
    assert len({a.leg_id for a in plan}) == len(legs)      # and only one decision
    assert validate({l.id: l for l in legs}, {c.id: c for c in crews}, plan) == []


def test_no_flight_leaves_during_the_ground_stop():
    result = run(14 * 60, 17 * 60, 6)
    for strategy in result["strategies"].values():
        for f in strategy["flights"]:
            if f["status"] == "flown" and f["route"].startswith("ATL"):
                assert not ("14:00" <= f["actual_dep"] < "17:00")


def test_optimizer_cancels_fewer_flights_than_doing_nothing():
    for gs_start, gs_end, reserves in SCENARIOS:
        s = run(gs_start, gs_end, reserves)["strategies"]
        assert s["optimized"]["metrics"]["cancelled"] <= s["original"]["metrics"]["cancelled"]
