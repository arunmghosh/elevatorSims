"""Elevator model implementing movement, capacity constraints, door delays, and metrics tracking."""

from typing import List, Set, Optional
from config import (
    ELEVATOR_CAPACITY,
    ELEVATOR_SPEED,
    BOARDING_DELAY,
    EXITING_DELAY,
    TIME_STEP,
    LOBBY_FLOOR,
)
from models import Direction, Person


class Elevator:
    """Represents a single elevator car operating across all building floors."""

    def __init__(self, elevator_id: int, initial_floor: int = LOBBY_FLOOR):
        self.id = elevator_id
        self.current_floor = initial_floor
        self.direction = Direction.IDLE
        self.passengers: List[Person] = []
        self.stops: Set[int] = set()

        # Operational state
        self.door_timer = 0  # Seconds remaining for doors open / boarding / exiting

        # Tracking metrics
        self.occupied_time = 0.0          # Total seconds with >= 1 passenger
        self.total_floors_traveled = 0    # Total distance moved (|floor change|)
        self.occupied_floors_traveled = 0 # Floors moved while carrying passengers

    @property
    def is_occupied(self) -> bool:
        return len(self.passengers) > 0

    @property
    def is_empty(self) -> bool:
        return len(self.passengers) == 0

    @property
    def available_capacity(self) -> int:
        return max(0, ELEVATOR_CAPACITY - len(self.passengers))

    @property
    def is_full(self) -> bool:
        return len(self.passengers) >= ELEVATOR_CAPACITY

    @property
    def is_busy(self) -> bool:
        """Returns True if elevator has passengers, assigned stops, or active door operations."""
        return self.is_occupied or bool(self.stops) or self.door_timer > 0

    def add_stop(self, floor: int) -> None:
        """Adds a target floor to the elevator's destination queue."""
        self.stops.add(floor)
        if self.direction == Direction.IDLE:
            if floor > self.current_floor:
                self.direction = Direction.UP
            elif floor < self.current_floor:
                self.direction = Direction.DOWN
            # If floor == current_floor, direction remains IDLE and doors will open next step

    def remove_stop(self, floor: int) -> None:
        self.stops.discard(floor)

    def update_direction(self) -> None:
        """Updates travel direction according to the LOOK/SCAN algorithm.
        
        Prioritizes the closest floor in the current direction of travel.
        If no more floors exist in the current direction, reverses direction
        if floors exist in the opposite direction; otherwise sets to IDLE.
        """
        if not self.stops:
            self.direction = Direction.IDLE
            return

        if self.direction == Direction.UP:
            stops_ahead = [s for s in self.stops if s >= self.current_floor]
            if not stops_ahead:
                stops_behind = [s for s in self.stops if s < self.current_floor]
                if stops_behind:
                    self.direction = Direction.DOWN
                else:
                    self.direction = Direction.IDLE

        elif self.direction == Direction.DOWN:
            stops_ahead = [s for s in self.stops if s <= self.current_floor]
            if not stops_ahead:
                stops_behind = [s for s in self.stops if s > self.current_floor]
                if stops_behind:
                    self.direction = Direction.UP
                else:
                    self.direction = Direction.IDLE

        elif self.direction == Direction.IDLE:
            if self.stops:
                # Pick the closest stop
                closest_stop = min(self.stops, key=lambda s: abs(s - self.current_floor))
                if closest_stop > self.current_floor:
                    self.direction = Direction.UP
                elif closest_stop < self.current_floor:
                    self.direction = Direction.DOWN

    def get_next_stop(self) -> Optional[int]:
        """Returns the next immediate stop in the current travel direction."""
        if not self.stops:
            return None

        if self.direction == Direction.UP:
            ahead = [s for s in self.stops if s >= self.current_floor]
            return min(ahead) if ahead else None
        elif self.direction == Direction.DOWN:
            ahead = [s for s in self.stops if s <= self.current_floor]
            return max(ahead) if ahead else None
        else:
            return min(self.stops, key=lambda s: abs(s - self.current_floor))

    def step(self) -> None:
        """Advances the elevator simulation state by 1 second (TIME_STEP)."""
        # Record occupancy time if at least one person is currently inside
        if self.is_occupied:
            self.occupied_time += TIME_STEP

        # If doors are open (boarding or exiting in progress)
        if self.door_timer > 0:
            self.door_timer -= TIME_STEP
            return

        # If no active stops, update direction to IDLE and remain stationary
        if not self.stops:
            self.direction = Direction.IDLE
            return

        self.update_direction()
        if self.direction == Direction.IDLE:
            return

        # Move 1 floor in the current direction (ELEVATOR_SPEED = 1 floor/sec)
        was_occupied = self.is_occupied
        if self.direction == Direction.UP:
            self.current_floor += 1
            self.total_floors_traveled += 1
            if was_occupied:
                self.occupied_floors_traveled += 1
        elif self.direction == Direction.DOWN:
            self.current_floor -= 1
            self.total_floors_traveled += 1
            if was_occupied:
                self.occupied_floors_traveled += 1

    def average_speed(self, use_occupied_distance: bool = True) -> float:
        """Computes average speed: (distance traveled / occupied time).
        
        When use_occupied_distance=True (default), computes (occupied distance / occupied time).
        Since elevator speed is 1 floor/s and stops introduce 3s delays, average speed is strictly <= 1.0.
        If elevator had no passengers, returns 0.0.
        """
        if self.occupied_time <= 0:
            return 0.0
        distance = self.occupied_floors_traveled if use_occupied_distance else self.total_floors_traveled
        return distance / self.occupied_time
