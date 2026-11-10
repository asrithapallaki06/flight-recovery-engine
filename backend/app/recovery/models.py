"""The two core objects: a flight leg and a crew.

All times are minutes after midnight on the simulated day (e.g. 7:30 AM = 450).
"""
from dataclasses import dataclass, field


@dataclass
class Leg:
    id: int
    flight_no: str
    origin: str
    dest: str
    sched_dep: int
    block: int                 # scheduled flight time in minutes
    risk: float = 0.0          # predicted chance of a 15+ minute delay
    earliest_dep: int = 0      # earliest it can leave after the disruption
    original_crew: int | None = None
    surprise_delay: int = 0    # extra air/taxi time nobody knows about in advance

    @property
    def sched_arr(self) -> int:
        return self.sched_dep + self.block


@dataclass
class Crew:
    id: int
    location: str
    ready_at: int = 0               # earliest time the crew can depart again
    duty_start: int | None = None   # report time; None until the crew first works
    is_reserve: bool = False
    pairing: list[int] = field(default_factory=list)   # planned leg ids


@dataclass
class Assignment:
    leg_id: int
    crew_id: int | None   # None means the flight was cancelled
    actual_dep: int | None
