"""Smoke test for mini simulation run."""

import unittest
import numpy as np
from simulation import generate_residents
from elevator import Elevator
from models import PersonState
from traditional import TraditionalDispatcher
from modern import ModernDispatcher


class TestSimulationSmoke(unittest.TestCase):
    def test_mini_schedule_processing(self):
        # Create 2 residents and run 100 seconds to verify step mechanics
        rng = np.random.RandomState(42)
        residents = generate_residents(rng)[:2]

        elevators = [Elevator(0, initial_floor=1), Elevator(1, initial_floor=1)]
        dispatcher = TraditionalDispatcher(elevators)

        # Place a call for resident 0
        p = residents[0]
        p.state = PersonState.WAITING_OUTBOUND
        p.morning_call_time = 0.0
        dispatcher.request_elevator(p, p.activity_floor, 0.0)

        # Step 20 seconds
        for t in range(20):
            dispatcher.step(t)
            for e in elevators:
                e.step()

        # Check that state progressed without errors
        self.assertIsNotNone(elevators[0].current_floor)


if __name__ == "__main__":
    unittest.main()
