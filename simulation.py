"""Daily trial simulation engine for elevator performance comparison."""

import math
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import numpy as np

from config import (
    NUM_FLOORS,
    LOBBY_FLOOR,
    STUDY_FLOOR,
    SKY_LOUNGE_FLOOR,
    RESIDENTIAL_FLOORS,
    APARTMENTS_PER_FLOOR,
    PEOPLE_PER_APARTMENT,
    TOTAL_RESIDENTS,
    NUM_ELEVATORS,
    SECONDS_PER_DAY,
    WAKEUP_MIN_SEC,
    WAKEUP_MAX_SEC,
    WAKEUP_MEAN_SEC,
    WAKEUP_STD_SEC,
    BEDTIME_MIN_SEC,
    BEDTIME_MAX_SEC,
    BEDTIME_MEAN_SEC,
    BEDTIME_STD_SEC,
    PROB_LEAVE_BUILDING,
    PROB_LEAVE_VIA_LOBBY,
    PROB_STUDY_FLOOR,
    PROB_SKY_LOUNGE,
    get_assigned_parking_floor,
)
from models import Person, PersonState, Direction
from elevator import Elevator
from traditional import TraditionalDispatcher
from modern import ModernDispatcher


@dataclass
class TrialResult:
    """Stores all metrics tracked for a single 24-hour simulation trial."""
    algorithm: str
    seed: Optional[int]
    wait_times: List[float]               # All 1840 wait times
    percentile_90_wait_time: float        # 90th percentile wait time in seconds
    elevator_occupied_times: List[float]  # Occupied time per elevator
    elevator_distances: List[int]         # Distance traveled per elevator
    elevator_speeds: List[float]          # Average speed per elevator (distance / occupied time)
    slowest_elevator_speed: float         # Slowest speed among the 8 elevators
    elevator_pickups: List[int]           # Passenger pickups handled by each elevator
    residents_returned_count: int         # Residents back in apartment before 6:00 AM
    residents_returned_percentage: float  # Percentage of residents back in apartment before 6:00 AM
    total_calls_serviced: int


def generate_residents(rng: np.random.RandomState) -> List[Person]:
    """Generates the 920 building residents with randomized schedules and activity targets."""
    residents: List[Person] = []
    person_id = 1

    for floor in RESIDENTIAL_FLOORS:
        parking_floor = get_assigned_parking_floor(floor)
        for _ in range(APARTMENTS_PER_FLOOR):
            for _ in range(PEOPLE_PER_APARTMENT):
                # Sample wake-up time from normal distribution bounded [6am, 12pm] -> [0s, 21600s]
                raw_wakeup = rng.normal(WAKEUP_MEAN_SEC, WAKEUP_STD_SEC)
                wakeup_time = float(np.clip(raw_wakeup, WAKEUP_MIN_SEC, WAKEUP_MAX_SEC))

                # Sample bedtime from normal distribution bounded [9pm, 3am] -> [54000s, 75600s]
                raw_bedtime = rng.normal(BEDTIME_MEAN_SEC, BEDTIME_STD_SEC)
                bedtime = float(np.clip(raw_bedtime, BEDTIME_MIN_SEC, BEDTIME_MAX_SEC))

                # Ensure bedtime is strictly after wake-up time
                if bedtime <= wakeup_time:
                    bedtime = wakeup_time + 3600.0

                # Sample activity choice
                act_rand = rng.rand()
                if act_rand < PROB_LEAVE_BUILDING:
                    # 70% leave building: 50% lobby, 50% assigned parking floor
                    if rng.rand() < PROB_LEAVE_VIA_LOBBY:
                        activity_floor = LOBBY_FLOOR
                    else:
                        activity_floor = parking_floor
                elif act_rand < PROB_LEAVE_BUILDING + PROB_STUDY_FLOOR:
                    # 20% study floor
                    activity_floor = STUDY_FLOOR
                else:
                    # 10% sky lounge
                    activity_floor = SKY_LOUNGE_FLOOR

                resident = Person(
                    id=person_id,
                    apartment_floor=floor,
                    parking_floor=parking_floor,
                    wakeup_time=math.floor(wakeup_time),
                    bedtime=math.floor(bedtime),
                    activity_floor=activity_floor,
                    current_floor=floor,
                    state=PersonState.SLEEPING,
                )
                residents.append(resident)
                person_id += 1

    return residents


def run_single_trial(algorithm: str, seed: Optional[int] = None) -> TrialResult:
    """Runs a single 24-hour simulation trial using the specified algorithm.
    
    Args:
        algorithm: 'traditional' or 'modern'
        seed: Random seed for reproducibility
    """
    rng = np.random.RandomState(seed)
    residents = generate_residents(rng)

    # Initialize 8 elevators at the lobby (floor 1)
    elevators = [Elevator(elevator_id=i, initial_floor=LOBBY_FLOOR) for i in range(NUM_ELEVATORS)]

    if algorithm.lower() == "traditional":
        dispatcher = TraditionalDispatcher(elevators, rng=rng)
    elif algorithm.lower() == "modern":
        dispatcher = ModernDispatcher(elevators, rng=rng)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}. Choose 'traditional' or 'modern'.")

    # Group morning calls and night calls by trigger second
    morning_schedule: Dict[int, List[Person]] = {}
    night_schedule: Dict[int, List[Person]] = {}

    for person in residents:
        wake_sec = int(person.wakeup_time)
        bed_sec = int(person.bedtime)
        morning_schedule.setdefault(wake_sec, []).append(person)
        night_schedule.setdefault(bed_sec, []).append(person)

    # Track passenger pickups per elevator
    elevator_pickups = [0] * NUM_ELEVATORS

    # Execute discrete time loop for 24 hours (and drain if needed)
    current_time = 0
    max_sim_time = SECONDS_PER_DAY + 7200  # 24 hours + up to 2-hour drain buffer

    while current_time < SECONDS_PER_DAY or (current_time < max_sim_time and any(e.is_busy for e in elevators)):
        # 1. Trigger morning calls at wake-up second
        if current_time in morning_schedule:
            for person in morning_schedule[current_time]:
                person.state = PersonState.WAITING_OUTBOUND
                person.morning_call_time = current_time
                dispatcher.request_elevator(person, person.activity_floor, current_time)

        # 2. Trigger return calls at bedtime second
        if current_time in night_schedule:
            for person in night_schedule[current_time]:
                person.state = PersonState.WAITING_INBOUND
                person.night_call_time = current_time
                dispatcher.request_elevator(person, person.apartment_floor, current_time)

        # 3. Dispatcher steps (boarding, exiting, call assignment, door delays)
        boarded_passengers = dispatcher.step(current_time)
        for p in boarded_passengers:
            for e in elevators:
                if p in e.passengers:
                    elevator_pickups[e.id] += 1
                    break

        # 4. Elevator steps (movement, occupied tracking)
        for elev in elevators:
            elev.step()

        current_time += 1

    # Extract wait times (arrival of elevator at caller's floor -> boarding)
    wait_times: List[float] = []
    for p in residents:
        if p.morning_wait_time is not None:
            wait_times.append(p.morning_wait_time)
        if p.night_wait_time is not None:
            wait_times.append(p.night_wait_time)

    # 90th percentile wait time
    percentile_90 = float(np.percentile(wait_times, 90)) if wait_times else 0.0

    # Calculate speeds for the 8 elevators
    elevator_occupied_times = [e.occupied_time for e in elevators]
    elevator_distances = [e.total_floors_traveled for e in elevators]
    elevator_speeds = [e.average_speed() for e in elevators]
    slowest_speed = min(elevator_speeds) if elevator_speeds else 0.0

    # Count residents who successfully returned to their apartment before trial concluded
    returned_count = sum(
        1 for p in residents
        if p.night_arrival_time is not None
    )
    returned_pct = (returned_count / len(residents)) * 100.0 if residents else 0.0

    return TrialResult(
        algorithm=algorithm,
        seed=seed,
        wait_times=wait_times,
        percentile_90_wait_time=percentile_90,
        elevator_occupied_times=elevator_occupied_times,
        elevator_distances=elevator_distances,
        elevator_speeds=elevator_speeds,
        slowest_elevator_speed=slowest_speed,
        elevator_pickups=elevator_pickups,
        residents_returned_count=returned_count,
        residents_returned_percentage=returned_pct,
        total_calls_serviced=len(wait_times),
    )
