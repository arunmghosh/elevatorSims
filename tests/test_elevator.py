"""Unit tests for Elevator movement, LOOK/SCAN routing, door timing, and speed metrics."""

import unittest
from elevator import Elevator
from models import Direction, Person, PersonState
from config import ELEVATOR_CAPACITY, BOARDING_DELAY, EXITING_DELAY


class TestElevator(unittest.TestCase):
    def test_initial_state(self):
        elev = Elevator(elevator_id=0, initial_floor=1)
        self.assertEqual(elev.current_floor, 1)
        self.assertEqual(elev.direction, Direction.IDLE)
        self.assertTrue(elev.is_empty)
        self.assertEqual(elev.available_capacity, ELEVATOR_CAPACITY)
        self.assertEqual(elev.occupied_time, 0.0)
        self.assertEqual(elev.total_floors_traveled, 0)

    def test_look_scan_routing_up_and_down(self):
        elev = Elevator(elevator_id=0, initial_floor=5)
        elev.add_stop(10)
        elev.add_stop(15)
        elev.add_stop(2)

        # Initially at 5, with stops at 10, 15, 2. Current direction is UP
        self.assertEqual(elev.direction, Direction.UP)
        self.assertEqual(elev.get_next_stop(), 10)

        # Step 5 times: floor becomes 10
        for _ in range(5):
            elev.step()
        self.assertEqual(elev.current_floor, 10)
        self.assertEqual(elev.direction, Direction.UP)

        # Remove stop 10 (as if doors opened), next stop should be 15
        elev.remove_stop(10)
        elev.update_direction()
        self.assertEqual(elev.get_next_stop(), 15)

        # Step 5 times: floor becomes 15
        for _ in range(5):
            elev.step()
        self.assertEqual(elev.current_floor, 15)

        # Remove stop 15, now only stop 2 remains -> direction reverses to DOWN
        elev.remove_stop(15)
        elev.update_direction()
        self.assertEqual(elev.direction, Direction.DOWN)
        self.assertEqual(elev.get_next_stop(), 2)

    def test_door_delay_pauses_movement(self):
        elev = Elevator(elevator_id=0, initial_floor=1)
        elev.add_stop(5)
        elev.door_timer = 6  # 6 seconds of door operations

        elev.step()
        # Should NOT have moved because door_timer > 0
        self.assertEqual(elev.current_floor, 1)
        self.assertEqual(elev.door_timer, 5)

    def test_occupied_time_and_speed(self):
        elev = Elevator(elevator_id=0, initial_floor=1)
        person = Person(
            id=1, apartment_floor=15, parking_floor=3,
            wakeup_time=0, bedtime=50000, activity_floor=1,
            current_floor=1,
        )
        elev.passengers.append(person)
        elev.add_stop(10)

        # Step 9 seconds: moves 9 floors from 1 to 10
        for _ in range(9):
            elev.step()

        self.assertEqual(elev.current_floor, 10)
        self.assertEqual(elev.total_floors_traveled, 9)
        self.assertEqual(elev.occupied_time, 9.0)
        # Average speed = 9 floors / 9 seconds = 1.0 floor/s
        self.assertAlmostEqual(elev.average_speed(), 1.0)


if __name__ == "__main__":
    unittest.main()
