"""Unit tests for traffic balancing and same-path request batching."""

import unittest
import numpy as np
from elevator import Elevator
from models import Person, Direction
from traditional import TraditionalDispatcher
from modern import ModernDispatcher


class TestBalancingAndBatching(unittest.TestCase):
    def test_randomized_idle_selection(self):
        # 8 elevators at floor 1
        rng = np.random.RandomState(42)
        elevators = [Elevator(i, 1) for i in range(8)]
        disp = TraditionalDispatcher(elevators, rng=rng)

        # Make 8 independent requests when all elevators are idle
        assigned_ids = set()
        for i in range(8):
            p = Person(
                id=i + 1, apartment_floor=15 + i, parking_floor=2,
                wakeup_time=0, bedtime=50000, activity_floor=1,
                current_floor=15 + i,
            )
            req = disp.request_elevator(p, destination_floor=1, call_time=0.0)
            if req.assigned_elevator_id is not None:
                assigned_ids.add(req.assigned_elevator_id)

        # Ensure that assignments are distributed among different elevators (not all elevator 0)
        self.assertGreater(len(assigned_ids), 1)

    def test_same_path_batching_traditional(self):
        # 8 elevators at floor 1
        rng = np.random.RandomState(42)
        elevators = [Elevator(i, 1) for i in range(8)]
        disp = TraditionalDispatcher(elevators, rng=rng)

        # Person 1 at floor 30 going DOWN to floor 1
        p1 = Person(id=1, apartment_floor=30, parking_floor=2, wakeup_time=0, bedtime=50000, activity_floor=1, current_floor=30)
        req1 = disp.request_elevator(p1, destination_floor=1, call_time=0.0)
        first_elev_id = req1.assigned_elevator_id

        # Person 2 at floor 28 going DOWN to floor 1 (same path)
        p2 = Person(id=2, apartment_floor=28, parking_floor=2, wakeup_time=0, bedtime=50000, activity_floor=1, current_floor=28)
        req2 = disp.request_elevator(p2, destination_floor=1, call_time=0.0)

        # Should be batched onto the SAME elevator!
        self.assertEqual(req2.assigned_elevator_id, first_elev_id)

    def test_same_path_batching_modern(self):
        rng = np.random.RandomState(42)
        elevators = [Elevator(i, 1) for i in range(8)]
        disp = ModernDispatcher(elevators, rng=rng)

        p1 = Person(id=1, apartment_floor=30, parking_floor=2, wakeup_time=0, bedtime=50000, activity_floor=1, current_floor=30)
        req1 = disp.request_elevator(p1, destination_floor=1, call_time=0.0)
        first_elev_id = req1.assigned_elevator_id

        p2 = Person(id=2, apartment_floor=25, parking_floor=2, wakeup_time=0, bedtime=50000, activity_floor=1, current_floor=25)
        req2 = disp.request_elevator(p2, destination_floor=1, call_time=0.0)

        self.assertEqual(req2.assigned_elevator_id, first_elev_id)


if __name__ == "__main__":
    unittest.main()
