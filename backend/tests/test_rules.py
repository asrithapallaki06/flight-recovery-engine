"""Unit tests for crew legality: the rules everything else depends on."""
from app.config import MAX_DUTY_MINUTES, MIN_TURN_MINUTES, REPORT_MINUTES
from app.recovery.models import Assignment, Crew, Leg
from app.recovery.rules import can_fly, fly, validate


def make_leg(id=0, origin="ATL", dest="MCO", dep=600, block=90):
    return Leg(id=id, flight_no=str(id), origin=origin, dest=dest, sched_dep=dep, block=block,
               earliest_dep=dep)


def test_crew_must_be_at_the_departure_airport():
    crew = Crew(id=1, location="BOS")
    assert not can_fly(crew, make_leg(), 600)


def test_crew_must_be_ready_in_time():
    crew = Crew(id=1, location="ATL", ready_at=620)
    assert not can_fly(crew, make_leg(), 600)
    assert can_fly(crew, make_leg(), 620)


def test_duty_limit_blocks_a_flight_that_would_run_too_long():
    crew = Crew(id=1, location="ATL", duty_start=0)
    leg = make_leg(dep=MAX_DUTY_MINUTES - 60, block=90)   # would land 30 min over the limit
    assert not can_fly(crew, leg, leg.sched_dep)


def test_flying_moves_the_crew_and_starts_duty():
    crew = Crew(id=1, location="ATL")
    leg = make_leg(dep=600, block=90)
    fly(crew, leg, 600)
    assert crew.location == "MCO"
    assert crew.duty_start == 600 - REPORT_MINUTES
    assert crew.ready_at == 600 + 90 + MIN_TURN_MINUTES


def test_surprise_delay_makes_the_crew_land_later():
    crew = Crew(id=1, location="ATL")
    leg = make_leg()
    leg.surprise_delay = 25
    fly(crew, leg, 600)
    assert crew.ready_at == 600 + 90 + 25 + MIN_TURN_MINUTES


def test_validator_catches_a_double_booked_crew():
    legs = {0: make_leg(0, dep=600), 1: make_leg(1, dep=610)}
    crews = {1: Crew(id=1, location="ATL")}
    plan = [Assignment(0, 1, 600), Assignment(1, 1, 610)]   # same crew, two places at once
    assert validate(legs, crews, plan)
