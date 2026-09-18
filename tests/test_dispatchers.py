"""Unit tests for Traditional and Modern dispatch algorithms."""

import unittest
from models import Direction, Person, PersonState
from elevator import Elevator
from traditional import TraditionalDispatcher
from modern import ModernDispatcher


class TestDispatchers(unittest.TestCase):
    def test_traditional_dispatches_closest_eligible_moving_elevator(self):
        # Elevator 0: at floor 5 moving UP towards 20
        elev0 = Elevator(0, initial_floor=5)
        elev0.direction = Direction.UP
        elev0.add_stop(20)

        # Elevator 1: at floor 15 moving UP towards 25
        elev1 = Elevator(1, initial_floor=15)
        elev1.direction = Direction.UP
        elev1.add_stop(25)

        # Elevator 2: at floor 18 moving DOWN
        elev2 = Elevator(2, initial_floor=18)
        elev2.direction = Direction.DOWN
        elev2.add_stop(1)

        dispatcher = TraditionalDispatcher([elev0, elev1, elev2])

        # Person at floor 12 wanting to go UP
        person = Person(
            id=101, apartment_floor=12, parking_floor=3,
            wakeup_time=0, bedtime=50000, activity_floor=34,
            current_floor=12,
        )

        req = dispatcher.request_elevator(person, destination_floor=34, call_time=100.0)
        # elev0 is at 5 (dist 7), elev1 is at 15 (already passed 12!), elev2 is DOWN
        # So elev0 must be assigned
        self.assertEqual(req.assigned_elevator_id, elev0.id)
        self.assertIn(12, elev0.stops)

    def test_traditional_dispatches_idle_elevator_if_no_moving_eligible(self):
        # Elevator 0: moving UP at floor 20
        elev0 = Elevator(0, initial_floor=20)
        elev0.direction = Direction.UP
        elev0.add_stop(30)

        # Elevator 1: IDLE at floor 8
        elev1 = Elevator(1, initial_floor=8)

        dispatcher = TraditionalDispatcher([elev0, elev1])

        # Person at floor 10 wanting to go UP
        # elev0 already passed floor 10, so idle elev1 should be chosen
        person = Person(
            id=102, apartment_floor=10, parking_floor=2,
            wakeup_time=0, bedtime=50000, activity_floor=34,
            current_floor=10,
        )

        req = dispatcher.request_elevator(person, destination_floor=34, call_time=200.0)
        self.assertEqual(req.assigned_elevator_id, elev1.id)
        self.assertIn(10, elev1.stops)

    def test_modern_advance_destination_notice(self):
        # In modern algorithm, both pickup and destination are added immediately
        elev0 = Elevator(0, initial_floor=4)
        elev0.direction = Direction.UP
        elev0.add_stop(30)

        dispatcher = ModernDispatcher([elev0])

        person = Person(
            id=201, apartment_floor=15, parking_floor=4,
            wakeup_time=0, bedtime=50000, activity_floor=25,
            current_floor=15,
        )

        req = dispatcher.request_elevator(person, destination_floor=25, call_time=300.0)
        self.assertEqual(req.assigned_elevator_id, elev0.id)

        # Crucial Advance Destination Notice property:
        # BOTH pickup (15) and destination (25) are in the elevator's queue!
        self.assertIn(15, elev0.stops)
        self.assertIn(25, elev0.stops)


if __name__ == "__main__":
    unittest.main()
