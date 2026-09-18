"""Data models for persons, requests, directions, and elevator states."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional


class Direction(Enum):
    DOWN = -1
    IDLE = 0
    UP = 1

    @classmethod
    def from_floors(cls, from_floor: int, to_floor: int) -> "Direction":
        if to_floor > from_floor:
            return cls.UP
        elif to_floor < from_floor:
            return cls.DOWN
        return cls.IDLE


class PersonState(Enum):
    SLEEPING = auto()
    WAITING_OUTBOUND = auto()
    TRAVELING_OUTBOUND = auto()
    AT_ACTIVITY = auto()
    WAITING_INBOUND = auto()
    TRAVELING_INBOUND = auto()
    FINISHED = auto()


@dataclass
class CallRequest:
    """Represents a passenger's request for elevator service."""
    id: int
    person_id: int
    source_floor: int
    destination_floor: int
    direction: Direction
    call_time: float
    assigned_elevator_id: Optional[int] = None
    is_picked_up: bool = False


@dataclass
class Person:
    """Represents a resident living in the building."""
    id: int
    apartment_floor: int
    parking_floor: int
    wakeup_time: float
    bedtime: float
    activity_floor: int
    current_floor: int
    state: PersonState = PersonState.SLEEPING

    # Timings for metrics tracking
    morning_call_time: Optional[float] = None
    morning_board_time: Optional[float] = None
    morning_arrival_time: Optional[float] = None

    night_call_time: Optional[float] = None
    night_board_time: Optional[float] = None
    night_arrival_time: Optional[float] = None

    @property
    def morning_wait_time(self) -> Optional[float]:
        if self.morning_board_time is not None and self.morning_call_time is not None:
            return self.morning_board_time - self.morning_call_time
        return None

    @property
    def night_wait_time(self) -> Optional[float]:
        if self.night_board_time is not None and self.night_call_time is not None:
            return self.night_board_time - self.night_call_time
        return None
