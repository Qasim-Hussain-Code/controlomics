import math
import unittest

from controlomics.statistics import bootstrap_difference, finite_mean, mean_difference, permutation_test, quantile, read_numeric_bytes


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

    def test_finite_large_group_means_do_not_overflow(self):
        self.assertEqual(mean_difference([1e308] * 4, [0, 0, 1, 1]), 0.0)
        result = bootstrap_difference([0.0, 0.0, 1e308, 1e308], [0, 0, 1, 1], draws=100)
        self.assertEqual((result['effect'], result['lower'], result['upper']), (1e308,) * 3)

    def test_permutation_summary_preserves_large_and_small_scales(self):
        for scale in (1e-200, 1e200, 1e307):
            with self.subTest(scale=scale):
                result = permutation_test([value * scale for value in (0, 1, 2, 3)], [0, 0, 1, 1])
                self.assertAlmostEqual(result['p_value'], 1 / 3)
                self.assertTrue(math.isfinite(result['null_sd']))
                self.assertAlmostEqual(result['null_sd'] / scale, math.sqrt(10 / 6))

    def test_overflowing_intermediate_sum_preserves_small_cancellation_residual(self):
        values = [1e308, 1e308, -1e308, -1e308, 1e-200]
        # The four large values cancel exactly; normalizing by 1e308 would
        # underflow the fifth value to zero before their cancellation.
        self.assertEqual(finite_mean(values), 1e-200 / 5)
        self.assertEqual(finite_mean(values[::-1]), 1e-200 / 5)

    def test_quantile_midpoint_does_not_overflow(self):
        for fraction, expected in ((0.25, -5e307), (0.5, 0.0), (0.75, 5e307)):
            self.assertEqual(quantile([-1e308, 1e308], fraction), expected)
        with self.assertRaises(ValueError):
            quantile([0.0, float('inf')], 0.5)

    def test_invalid_labels_and_unrepresentable_effect_are_rejected(self):
        for values, labels in (([0.0, 1.0, 2.0], [0, 1, 2]), ([-1e308, -1e308, 1e308, 1e308], [0, 0, 1, 1])):
            with self.assertRaises(ValueError):
                mean_difference(values, labels)
            with self.assertRaises(ValueError):
                bootstrap_difference(values, labels, draws=100)

    def test_utf8_bom_and_ambiguous_unit_identifiers(self):
        raw = b'unit,label,value\na,0,1\nb,0,1\nc,1,3\nd,1,3\n'
        self.assertEqual(read_numeric_bytes(b'\xef\xbb\xbf' + raw), read_numeric_bytes(raw))
        for identifier in (b' a', b'a ', b' '):
            with self.assertRaises(ValueError):
                read_numeric_bytes(raw.replace(b'a,0,1', identifier + b',0,1'))
