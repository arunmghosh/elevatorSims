"""Traditional elevator dispatch algorithm with traffic balancing and request batching.

Specification & Balancing Enhancements:
- Hall calls UP/DOWN; destination floor entered upon boarding.
- Randomized idle elevator selection: when multiple idle elevators are tied for minimum distance,
  randomly choose among them rather than deterministically picking the lowest ID.
- Same-path request batching (up to 10 requests): when an elevator is moving or dispatched along
  a travel corridor, group up to 10 passengers on that path into the same elevator,
  freeing remaining elevators to service independent routes.
- Dynamic idle rotation: newly idle elevators re-enter the pool for balanced random selection.
"""

from typing import List, Dict, Optional, Set, Tuple
import numpy as np
from models import Direction, Person, CallRequest
from elevator import Elevator
from config import BOARDING_DELAY, EXITING_DELAY, ELEVATOR_CAPACITY


class TraditionalDispatcher:
    """Manages elevator assignment and dispatching under the traditional algorithm."""

    def __init__(self, elevators: List[Elevator], rng: Optional[np.random.RandomState] = None):
        self.elevators = elevators
        self.rng = rng if rng is not None else np.random.RandomState(42)

        # Unassigned hall calls: list of CallRequest
        self.unassigned_calls: List[CallRequest] = []

        # Waiting passengers at each floor grouped by direction:
        # floor -> {Direction.UP: [(Person, dest_floor)], Direction.DOWN: [(Person, dest_floor)]}
        self.waiting_passengers: Dict[int, Dict[Direction, List[Tuple[Person, int]]]] = {
            f: {Direction.UP: [], Direction.DOWN: []} for f in range(1, 35)
        }

        # Track planned service direction and booked request load for same-path batching
        self.service_direction: Dict[int, Optional[Direction]] = {e.id: None for e in elevators}
        self.booked_requests: Dict[int, List[CallRequest]] = {e.id: [] for e in elevators}

    def request_elevator(self, person: Person, destination_floor: int, call_time: float) -> CallRequest:
        """Called when a passenger presses the UP or DOWN button at their current floor."""
        direction = Direction.from_floors(person.current_floor, destination_floor)
        if direction == Direction.IDLE:
            return CallRequest(
                id=person.id,
                person_id=person.id,
                source_floor=person.current_floor,
                destination_floor=destination_floor,
                direction=direction,
                call_time=call_time,
            )

        req = CallRequest(
            id=person.id,
            person_id=person.id,
            source_floor=person.current_floor,
            destination_floor=destination_floor,
            direction=direction,
            call_time=call_time,
        )

        self.waiting_passengers[person.current_floor][direction].append((person, destination_floor))
        self.unassigned_calls.append(req)
        self._dispatch_calls()
        return req

    def _find_best_elevator(self, source_floor: int, direction: Direction) -> Optional[Elevator]:
        """Finds the closest eligible elevator.
        
        Prioritizes:
        1. Elevators already traveling or scheduled along the same path that have available
           capacity (< 10 passengers booked).
        2. Idle elevators, choosing randomly among ties.
        """
        candidate_moving: List[Tuple[int, Elevator]] = []
        candidate_idle: List[Tuple[int, Elevator]] = []

        for elev in self.elevators:
            dist = abs(elev.current_floor - source_floor)
            current_booked = len(elev.passengers) + len(self.booked_requests[elev.id])

            # 1. Check if elevator is actively moving in the desired direction
            if elev.direction == direction and current_booked < ELEVATOR_CAPACITY:
                if direction == Direction.UP and elev.current_floor <= source_floor:
                    candidate_moving.append((dist, elev))
                elif direction == Direction.DOWN and elev.current_floor >= source_floor:
                    candidate_moving.append((dist, elev))

            # 2. Check if elevator was dispatched to a turnaround floor to start a run in this direction
            elif (
                self.service_direction[elev.id] == direction
                and current_booked < ELEVATOR_CAPACITY
                and elev.stops
            ):
                if direction == Direction.DOWN:
                    peak_stop = max(elev.stops)
                    # Elevator is ascending to peak_stop, will come down through source_floor
                    if source_floor <= peak_stop:
                        candidate_moving.append((dist, elev))
                elif direction == Direction.UP:
                    lowest_stop = min(elev.stops)
                    if source_floor >= lowest_stop:
                        candidate_moving.append((dist, elev))

            # 3. Check if elevator is completely idle
            elif (
                elev.direction == Direction.IDLE
                and elev.is_empty
                and not elev.stops
                and elev.door_timer == 0
            ):
                candidate_idle.append((dist, elev))

        # If moving/scheduled elevators are available, pick closest; break ties randomly
        if candidate_moving:
            min_dist = min(c[0] for c in candidate_moving)
            tied_moving = [e for d, e in candidate_moving if d == min_dist]
            return self.rng.choice(tied_moving) if len(tied_moving) > 1 else tied_moving[0]

        # If only idle elevators are available, pick closest; break ties randomly
        if candidate_idle:
            min_dist = min(c[0] for c in candidate_idle)
            tied_idle = [e for d, e in candidate_idle if d == min_dist]
            return self.rng.choice(tied_idle) if len(tied_idle) > 1 else tied_idle[0]

        return None

    def _dispatch_calls(self) -> None:
        """Attempts to assign pending unassigned hall calls to eligible elevators."""
        still_unassigned: List[CallRequest] = []
        for req in self.unassigned_calls:
            elev = self._find_best_elevator(req.source_floor, req.direction)
            if elev is not None:
                req.assigned_elevator_id = elev.id
                elev.add_stop(req.source_floor)
                self.booked_requests[elev.id].append(req)
                # Mark planned service direction
                self.service_direction[elev.id] = req.direction
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

        # Check all elevators for arrivals at stops
        for elev in self.elevators:
            current_floor = elev.current_floor

            has_exiting = any(
                p.activity_floor == current_floor or p.apartment_floor == current_floor 
                for p in elev.passengers
            )
            has_stop = current_floor in elev.stops

            should_stop = False
            target_board_dir = elev.direction

            if has_exiting:
                should_stop = True
            elif has_stop:
                if elev.direction == Direction.UP:
                    stops_above = [s for s in elev.stops if s > current_floor]
                    if self.waiting_passengers[current_floor][Direction.UP]:
                        should_stop = True
                        target_board_dir = Direction.UP
                    elif not stops_above:
                        # Reached top turnaround of ascent!
                        should_stop = True
                        target_board_dir = Direction.DOWN if self.waiting_passengers[current_floor][Direction.DOWN] else Direction.UP
                elif elev.direction == Direction.DOWN:
                    stops_below = [s for s in elev.stops if s < current_floor]
                    if self.waiting_passengers[current_floor][Direction.DOWN]:
                        should_stop = True
                        target_board_dir = Direction.DOWN
                    elif not stops_below:
                        # Reached bottom turnaround of descent!
                        should_stop = True
                        target_board_dir = Direction.UP if self.waiting_passengers[current_floor][Direction.UP] else Direction.DOWN
                elif elev.direction == Direction.IDLE:
                    should_stop = True
                    if self.service_direction[elev.id] is not None:
                        target_board_dir = self.service_direction[elev.id]
                    elif self.waiting_passengers[current_floor][Direction.UP]:
                        target_board_dir = Direction.UP
                    elif self.waiting_passengers[current_floor][Direction.DOWN]:
                        target_board_dir = Direction.DOWN

            if not should_stop:
                # Reset service direction if elevator has become idle and empty
                if elev.is_empty and not elev.stops and elev.door_timer == 0:
                    self.service_direction[elev.id] = None
                    self.booked_requests[elev.id].clear()
                continue

            # Remove floor from stops since we are servicing this stop
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

            # 2. Passengers board
            num_boarded = 0
            if target_board_dir in (Direction.UP, Direction.DOWN):
                waiting_list = self.waiting_passengers[current_floor][target_board_dir]
                while waiting_list and len(elev.passengers) < ELEVATOR_CAPACITY:
                    passenger, dest = waiting_list.pop(0)
                    elev.passengers.append(passenger)
                    num_boarded += 1

                    # Remove from booked requests for this elevator
                    for r in list(self.booked_requests[elev.id]):
                        if r.person_id == passenger.id:
                            self.booked_requests[elev.id].remove(r)
                            break

                    # Passenger enters their destination floor inside the elevator
                    elev.add_stop(dest)

                    if passenger.morning_call_time is not None and passenger.morning_board_time is None:
                        passenger.morning_board_time = current_time
                    elif passenger.night_call_time is not None and passenger.night_board_time is None:
                        passenger.night_board_time = current_time

                    just_boarded.append(passenger)

                # If the elevator reached full capacity and passengers remain waiting,
                # release them from this elevator's booked requests and re-queue to unassigned_calls
                if waiting_list:
                    for p, dest in waiting_list:
                        for r in list(self.booked_requests[elev.id]):
                            if r.person_id == p.id:
                                self.booked_requests[elev.id].remove(r)
                                break
                        if not any(c.person_id == p.id for c in self.unassigned_calls):
                            self.unassigned_calls.append(CallRequest(
                                id=p.id,
                                person_id=p.id,
                                source_floor=current_floor,
                                destination_floor=dest,
                                direction=target_board_dir,
                                call_time=current_time,
                            ))

            # 3. Apply door delay
            door_time = (len(exiting_passengers) * EXITING_DELAY) + (num_boarded * BOARDING_DELAY)
            if door_time > 0:
                elev.door_timer = max(elev.door_timer, door_time)

            elev.update_direction()

            # Reset service direction if elevator is now empty and idle with no stops
            if elev.is_empty and not elev.stops and elev.door_timer == 0:
                self.service_direction[elev.id] = None
                self.booked_requests[elev.id].clear()

        return just_boarded
