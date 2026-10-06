import csv
import io
import itertools
import unittest

from controlomics.statistics import bootstrap_difference, mean_difference, permutation_test, quantile, read_numeric_bytes


class StatisticsTests(unittest.TestCase):
    def test_exact_null_matches_independent_enumeration(self):
        values, labels = [0.0, 1.0, 2.0, 3.0], [0, 0, 1, 1]
        result = permutation_test(values, labels)
        # Independent calculation from selected group sums: two of six assignments are as extreme.
        self.assertEqual(result["effect"], 2.0)
        self.assertAlmostEqual(result["p_value"], 1 / 3)
        self.assertEqual(result["draws"], 6)
        self.assertTrue(result["exact"])

    def test_identical_groups_have_unit_null_probability(self):
        result = permutation_test([-1.0, 0.0, 1.0] * 2, [0] * 3 + [1] * 3)
        self.assertEqual(result["effect"], 0)
        self.assertEqual(result["p_value"], 1)

    def test_exact_tail_is_invariant_to_measurement_scale(self):
        for scale in (1e-15, 1.0, 1e15):
            result = permutation_test([value * scale for value in (0.0, 1.0, 2.0, 3.0)], [0, 0, 1, 1])
            self.assertAlmostEqual(result["p_value"], 1 / 3)

    def test_monte_carlo_seed_and_nonzero_p_value(self):
        values, labels = [0.0] * 8 + [5.0] * 8, [0] * 8 + [1] * 8
        result = permutation_test(values, labels, seed=7, draws=199, exact_limit=1)
        self.assertEqual(result, permutation_test(values, labels, seed=7, draws=199, exact_limit=1))
        self.assertGreaterEqual(result["p_value"], 1 / 200)
        self.assertFalse(result["exact"])

    def test_bootstrap_seed_and_constant_shift(self):
        result = bootstrap_difference([1.0, 1.0, 3.0, 3.0], [0, 0, 1, 1], seed=9, draws=199)
        self.assertEqual(result["lower"], 2)
        self.assertEqual(result["upper"], 2)
        self.assertEqual(result, bootstrap_difference([1.0, 1.0, 3.0, 3.0], [0, 0, 1, 1], seed=9, draws=199))
        self.assertEqual(quantile([0.0, 2.0], 0.25), 0.5)

    def test_csv_rejects_duplicate_units_and_nonfinite_values(self):
        for raw in (
            b"unit,label,value\na,0,1\na,1,2\n", b"unit,label,value\na,0,NaN\n",
            b"unit,label,value\na,0,1\nb,1,2\n", b"unit,label,value,patient\na,0,1,private\n",
        ):
            with self.assertRaises(ValueError):
                read_numeric_bytes(raw)
