"""Simulation configuration and constants for the elevator comparison study.

Specification Details:
- 34 floors:
    - Floor 1: Lobby
    - Floors 2-9: Parking
    - Floor 10: Study floor
    - Floors 11-33: Residential (23 floors, 10 4-person apartments = 40 people/floor, 920 residents)
    - Floor 34: Sky lounge
- Assigned parking floor: floor([apartment_floor - 4] / 3) clamped to parking range [2, 9]
- 8 elevators, capacity 10, speed 1 floor/sec
- Boarding and exiting delay: 3 seconds per person
- Time step: 1 second
- Duration per trial: 24 hours (86,400 seconds), 6 a.m. to 6 a.m.
- Number of trials: 365
"""

import math

# Building layout
NUM_FLOORS = 34
LOBBY_FLOOR = 1
MIN_PARKING_FLOOR = 2
MAX_PARKING_FLOOR = 9
PARKING_FLOORS = list(range(MIN_PARKING_FLOOR, MAX_PARKING_FLOOR + 1))
STUDY_FLOOR = 10
MIN_RESIDENTIAL_FLOOR = 11
MAX_RESIDENTIAL_FLOOR = 33
RESIDENTIAL_FLOORS = list(range(MIN_RESIDENTIAL_FLOOR, MAX_RESIDENTIAL_FLOOR + 1))
SKY_LOUNGE_FLOOR = 34

APARTMENTS_PER_FLOOR = 10
PEOPLE_PER_APARTMENT = 4
PEOPLE_PER_FLOOR = APARTMENTS_PER_FLOOR * PEOPLE_PER_APARTMENT  # 40 people
TOTAL_RESIDENTS = len(RESIDENTIAL_FLOORS) * PEOPLE_PER_FLOOR    # 23 * 40 = 920

# Elevator parameters
NUM_ELEVATORS = 8
ELEVATOR_CAPACITY = 10          # 10 passengers max
ELEVATOR_SPEED = 1              # 1 floor per second
BOARDING_DELAY = 3              # 3 seconds per person
EXITING_DELAY = 3               # 3 seconds per person
TIME_STEP = 1                   # 1 second discrete time step

# Timing & trial parameters
SECONDS_PER_DAY = 24 * 3600     # 86,400 seconds (24 hours)
DEFAULT_NUM_TRIALS = 365
CALLS_PER_PERSON_PER_DAY = 2    # 1 morning wake-up call + 1 bedtime return call
TOTAL_CALLS_PER_TRIAL = TOTAL_RESIDENTS * CALLS_PER_PERSON_PER_DAY  # 1840 calls

# Daily routine timing (relative to simulation start at 6:00 AM)
# 6:00 AM is t = 0 seconds
# 12:00 PM is t = 6 hours = 21,600 seconds
# Wake-up: Normal distribution between 6am and 12pm
# Midpoint = 9:00 AM (t = 10,800s), std dev = 1.5h (5,400s)
WAKEUP_MIN_SEC = 0
WAKEUP_MAX_SEC = 6 * 3600
WAKEUP_MEAN_SEC = 3 * 3600       # 9:00 AM
WAKEUP_STD_SEC = 1.5 * 3600

# Bedtime: Normal distribution between 9pm and 3am next day
# 9:00 PM is t = 15 hours = 54,000 seconds
# 3:00 AM is t = 21 hours = 75,600 seconds
# Elevators and simulation continue operating through 6:00 AM (t = 86,400s)
# Midpoint = 12:00 AM midnight (t = 18 hours = 64,800s), std dev = 1.5h (5,400s)
BEDTIME_MIN_SEC = 15 * 3600
BEDTIME_MAX_SEC = 21 * 3600
BEDTIME_MEAN_SEC = 18 * 3600     # 12:00 AM midnight
BEDTIME_STD_SEC = 1.5 * 3600

# Activity choice probability distribution
PROB_LEAVE_BUILDING = 0.70
PROB_LEAVE_VIA_LOBBY = 0.50     # Given leaving building
PROB_LEAVE_VIA_PARKING = 0.50   # Given leaving building
PROB_STUDY_FLOOR = 0.20
PROB_SKY_LOUNGE = 0.10


def get_assigned_parking_floor(apartment_floor: int) -> int:
    """Calculates assigned parking floor: floor([apartment_floor - 4] / 3).
    
    Guarantees result falls within designated parking floors [2, 9].
    """
    raw_floor = math.floor((apartment_floor - 4) / 3)
    return max(MIN_PARKING_FLOOR, min(MAX_PARKING_FLOOR, raw_floor))
