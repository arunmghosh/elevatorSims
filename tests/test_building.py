"""Unit tests for building layout, parking formula, and resident generation."""

import unittest
import numpy as np
from config import (
    NUM_FLOORS,
    LOBBY_FLOOR,
    STUDY_FLOOR,
    SKY_LOUNGE_FLOOR,
    RESIDENTIAL_FLOORS,
    TOTAL_RESIDENTS,
    NUM_ELEVATORS,
    ELEVATOR_CAPACITY,
    get_assigned_parking_floor,
)
from simulation import generate_residents


class TestBuildingAndResidents(unittest.TestCase):
    def test_building_parameters(self):
        self.assertEqual(NUM_FLOORS, 34)
        self.assertEqual(LOBBY_FLOOR, 1)
        self.assertEqual(STUDY_FLOOR, 10)
        self.assertEqual(SKY_LOUNGE_FLOOR, 34)
        self.assertEqual(len(RESIDENTIAL_FLOORS), 23)
        self.assertEqual(NUM_ELEVATORS, 8)
        self.assertEqual(ELEVATOR_CAPACITY, 10)

    def test_assigned_parking_formula(self):
        """Spec updated formula: floor([apartment_floor - 3] / 3) clamped to [2, 9]."""
        # Floor 11: floor((11 - 3) / 3) = floor(8 / 3) = 2
        self.assertEqual(get_assigned_parking_floor(11), 2)
        # Floor 12: floor((12 - 3) / 3) = floor(9 / 3) = 3
        self.assertEqual(get_assigned_parking_floor(12), 3)
        # Floor 15: floor((15 - 3) / 3) = floor(12 / 3) = 4
        self.assertEqual(get_assigned_parking_floor(15), 4)
        # Floor 30: floor((30 - 3) / 3) = floor(27 / 3) = 9
        self.assertEqual(get_assigned_parking_floor(30), 9)
        # Floor 33: floor((33 - 3) / 3) = floor(30 / 3) = 10, clamped to max parking floor 9
        self.assertEqual(get_assigned_parking_floor(33), 9)

        # Ensure all residential floors map strictly within parking levels [2, 9]
        for f in RESIDENTIAL_FLOORS:
            parking = get_assigned_parking_floor(f)
            self.assertTrue(2 <= parking <= 9, f"Floor {f} mapped to invalid parking floor {parking}")

    def test_residents_generation(self):
        rng = np.random.RandomState(42)
        residents = generate_residents(rng)
        self.assertEqual(len(residents), TOTAL_RESIDENTS)
        self.assertEqual(len(residents), 920)

        for p in residents:
            self.assertTrue(11 <= p.apartment_floor <= 33)
            self.assertTrue(2 <= p.parking_floor <= 9)
            # Wake-up between 6am (0s) and 12pm (21600s)
            self.assertTrue(0 <= p.wakeup_time <= 21600, f"Invalid wake-up time: {p.wakeup_time}")
            # Bedtime between 9pm (54000s) and 3am (75600s)
            self.assertTrue(54000 <= p.bedtime <= 75600, f"Invalid bedtime: {p.bedtime}")
            # Bedtime strictly after wake-up
            self.assertGreater(p.bedtime, p.wakeup_time)
            # Activity floor is either Lobby (1), Parking (2-9), Study (10), or Sky Lounge (34)
            valid_destinations = {1, 10, 34, p.parking_floor}
            self.assertIn(p.activity_floor, valid_destinations)


if __name__ == "__main__":
    unittest.main()
