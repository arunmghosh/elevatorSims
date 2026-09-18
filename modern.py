"""Modern elevator dispatch algorithm (Advance Destination Notice) with traffic balancing and batching.

Specification & Balancing Enhancements:
- Passengers input their destination floor at the hallway kiosk.
- Advance Destination Notice allows matching requests along the same corridor (up to 10 people),
  freeing remaining elevators for other routes.
- Randomized idle elevator selection: when multiple idle elevators are tied for minimum distance,
  randomly choose among them rather than deterministically picking the lowest ID.
- Dynamic idle rotation: newly idle elevators re-enter the pool for balanced random selection.
"""

from typing import List, Dict, Optional, Set, Tuple
import numpy as np
from models import Direction, Person, CallRequest
from elevator import Elevator
from config import BOARDING_DELAY, EXITING_DELAY, ELEVATOR_CAPACITY


class ModernDispatcher:
    """Manages elevator assignment and dispatching under the modern destination dispatch algorithm."""

    def __init__(self, elevators: List[Elevator], rng: Optional[np.random.RandomState] = None):
        self.elevators = elevators
        self.rng = rng if rng is not None else np.random.RandomState(42)

        # Unassigned destination calls: list of CallRequest
        self.unassigned_calls: List[CallRequest] = []
        # Mapping from person_id to their CallRequest
        self.active_calls: Dict[int, CallRequest] = {}
        # Mapping from person_id to Person object
        self.waiting_people: Dict[int, Person] = {}
        # Mapping from elevator_id to list of CallRequest assigned to it waiting for pickup
        self.elevator_pickups: Dict[int, List[CallRequest]] = {e.id: [] for e in elevators}

    def request_elevator(self, person: Person, destination_floor: int, call_time: float) -> CallRequest:
        """Called when a passenger enters their destination floor at the hallway kiosk."""
        direction = Direction.from_floors(person.current_floor, destination_floor)

        req = CallRequest(
            id=person.id,
            person_id=person.id,
            source_floor=person.current_floor,
            destination_floor=destination_floor,
            direction=direction,
            call_time=call_time,
        )

        self.active_calls[person.id] = req
        self.waiting_people[person.id] = person
        self.unassigned_calls.append(req)
        self._dispatch_calls()
        return req

    def _find_best_elevator(self, source_floor: int, dest_floor: int, direction: Direction) -> Optional[Elevator]:
        """Finds the closest elevator traveling towards dest_floor on a path that will pass
        by source_floor before it reaches dest_floor, or the closest idle elevator.
        
        Prioritizes:
        1. Elevators along the same path with capacity (< 10 booked passengers).
        2. Idle elevators, choosing randomly among ties.
        """
        candidate_moving: List[Tuple[int, Elevator]] = []
        candidate_idle: List[Tuple[int, Elevator]] = []

        for elev in self.elevators:
            dist = abs(elev.current_floor - source_floor)
            current_booked = len(elev.passengers) + len(self.elevator_pickups[elev.id])

            # 1. Check if elevator is already moving/scheduled along the path and has capacity
            if elev.direction == direction and current_booked < ELEVATOR_CAPACITY:
                if direction == Direction.UP:
                    if elev.current_floor <= source_floor < dest_floor:
                        candidate_moving.append((dist, elev))
                elif direction == Direction.DOWN:
                    if elev.current_floor >= source_floor > dest_floor:
                        candidate_moving.append((dist, elev))

            # 2. Check if elevator is ascending to turn around and do a DOWN run passing source_floor
            elif (
                direction == Direction.DOWN
                and current_booked < ELEVATOR_CAPACITY
                and elev.stops
            ):
                peak_stop = max(elev.stops)
                if source_floor <= peak_stop and dest_floor < source_floor:
                    candidate_moving.append((dist, elev))

            # 3. Check if elevator is completely idle
            elif (
                elev.direction == Direction.IDLE
                and elev.is_empty
                and not elev.stops
                and elev.door_timer == 0
            ):
                candidate_idle.append((dist, elev))

        # Break ties randomly among candidate moving elevators
        if candidate_moving:
            min_dist = min(c[0] for c in candidate_moving)
            tied_moving = [e for d, e in candidate_moving if d == min_dist]
            return self.rng.choice(tied_moving) if len(tied_moving) > 1 else tied_moving[0]

        # Break ties randomly among candidate idle elevators
        if candidate_idle:
            min_dist = min(c[0] for c in candidate_idle)
            tied_idle = [e for d, e in candidate_idle if d == min_dist]
            return self.rng.choice(tied_idle) if len(tied_idle) > 1 else tied_idle[0]

        return None

    def _dispatch_calls(self) -> None:
        """Attempts to assign pending unassigned destination calls to eligible elevators."""
        still_unassigned: List[CallRequest] = []
        for req in self.unassigned_calls:
            elev = self._find_best_elevator(req.source_floor, req.destination_floor, req.direction)
            if elev is not None:
                req.assigned_elevator_id = elev.id
                elev.add_stop(req.source_floor)
                elev.add_stop(req.destination_floor)
                self.elevator_pickups[elev.id].append(req)
            else:
                still_unassigned.append(req)
        self.unassigned_calls = still_unassigned

    def step(self, current_time: float) -> List[Person]:
        """Performs door operations, passenger exchange, and dispatches pending calls.
        
        Returns a list of passengers who boarded an elevator this second.
        """
        just_boarded: List[Person] = []

        # Try to assign any pending unassigned calls first
        self._dispatch_calls()

        # Check each elevator for arrivals
        for elev in self.elevators:
            current_floor = elev.current_floor

            has_exiting = any(
                p.activity_floor == current_floor or p.apartment_floor == current_floor 
                for p in elev.passengers
            )
            has_stop = current_floor in elev.stops

            if not has_stop and not has_exiting:
                continue

            # Remove current floor from stops
            elev.remove_stop(current_floor)

            # 1. Passengers exit
            exiting_passengers = []
            remaining_passengers = []
            for p in elev.passengers:
                target = (
                    p.apartment_floor
                    if p.night_call_time is not None and p.night_arrival_time is None
                    else p.activity_floor
                )
                if target == current_floor:
                    exiting_passengers.append(p)
                else:
                    remaining_passengers.append(p)

            elev.passengers = remaining_passengers

            for p in exiting_passengers:
                if p.night_call_time is not None and p.night_arrival_time is None:
                    p.night_arrival_time = current_time
                    p.current_floor = current_floor
                else:
                    p.morning_arrival_time = current_time
                    p.current_floor = current_floor
                # Clean up records for completed passenger
                if p.id in self.active_calls:
                    del self.active_calls[p.id]
                if p.id in self.waiting_people:
                    del self.waiting_people[p.id]

            # 2. Assigned passengers board
            pending_here = [r for r in self.elevator_pickups[elev.id] if r.source_floor == current_floor]
            num_boarded = 0

            for req in pending_here:
                if len(elev.passengers) >= ELEVATOR_CAPACITY:
                    break
                person = self.waiting_people.get(req.person_id)
                if person is not None:
                    elev.passengers.append(person)
                    num_boarded += 1
                    req.is_picked_up = True
                    self.elevator_pickups[elev.id].remove(req)
                    # Ensure passenger's destination is in the elevator stops
                    elev.add_stop(req.destination_floor)

                    if person.morning_call_time is not None and person.morning_board_time is None:
                        person.morning_board_time = current_time
                    elif person.night_call_time is not None and person.night_board_time is None:
                        person.night_board_time = current_time

                    just_boarded.append(person)

            # 3. Apply door delay
            door_time = (len(exiting_passengers) * EXITING_DELAY) + (num_boarded * BOARDING_DELAY)
            if door_time > 0:
                elev.door_timer = max(elev.door_timer, door_time)

            elev.update_direction()

        return just_boarded
