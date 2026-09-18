"""Unit tests for Confidence Interval computation and overlap evaluation."""

import unittest
from stats import compute_confidence_interval, evaluate_confidence_interval_overlap, ConfidenceInterval


class TestStats(unittest.TestCase):
    def test_confidence_interval_computation(self):
        # 10 samples with known properties
        data = [10.0, 12.0, 11.0, 10.5, 11.5, 10.8, 11.2, 12.1, 9.9, 11.0]
        ci = compute_confidence_interval(data, "Test Metric", confidence=0.90)

        self.assertEqual(ci.sample_size, 10)
        self.assertAlmostEqual(ci.mean, sum(data) / len(data), places=4)
        self.assertGreater(ci.margin_of_error, 0)
        self.assertAlmostEqual(ci.lower_bound, ci.mean - ci.margin_of_error, places=4)
        self.assertAlmostEqual(ci.upper_bound, ci.mean + ci.margin_of_error, places=4)

    def test_overlap_detected(self):
        # Two intervals that overlap: [10, 15] and [14, 20]
        ci1 = ConfidenceInterval("A", 0.90, 100, 12.5, 1.0, 0.1, 2.5, 10.0, 15.0)
        ci2 = ConfidenceInterval("B", 0.90, 100, 17.0, 1.0, 0.1, 3.0, 14.0, 20.0)

        has_overlap, amount, text = evaluate_confidence_interval_overlap(ci1, ci2)
        self.assertTrue(has_overlap)
        self.assertAlmostEqual(amount, 1.0)
        self.assertIn("OVERLAP", text)
        self.assertIn("no or only marginal benefit", text)

    def test_no_overlap_detected(self):
        # Two intervals that do not overlap: [10, 14] and [16, 20]
        ci1 = ConfidenceInterval("A", 0.90, 100, 12.0, 1.0, 0.1, 2.0, 10.0, 14.0)
        ci2 = ConfidenceInterval("B", 0.90, 100, 18.0, 1.0, 0.1, 2.0, 16.0, 20.0)

        has_overlap, amount, text = evaluate_confidence_interval_overlap(ci1, ci2)
        self.assertFalse(has_overlap)
        self.assertEqual(amount, 0.0)
        self.assertIn("DO NOT OVERLAP", text)
        self.assertIn("statistically significant benefit", text)


if __name__ == "__main__":
    unittest.main()
