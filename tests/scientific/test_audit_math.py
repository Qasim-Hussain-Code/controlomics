import unittest
from decimal import Decimal, localcontext

from controlomics.benchmark import wilson


class WilsonAuditTests(unittest.TestCase):
    def test_boundary_intervals_contain_zero_and_one_exactly(self):
        for count in range(1, 2401):
            with self.subTest(count=count):
                lower, upper = wilson(0, count)
                self.assertEqual(lower, 0.0)
                self.assertGreater(upper, 0.0)
                lower, upper = wilson(count, count)
                self.assertLess(lower, 1.0)
                self.assertEqual(upper, 1.0)

    def test_intervals_match_independently_solved_score_inequality(self):
        with localcontext() as context:
            context.prec = 60
            z_squared = Decimal("1.959963984540054") ** 2
            for count in (2, 3, 7, 31, 1000, 2400):
                for successes in sorted({0, 1, count // 2, count - 1, count}):
                    with self.subTest(count=count, successes=successes):
                        n, k = Decimal(count), Decimal(successes)
                        # Solve n(p-k/n)^2 <= z^2 p(1-p) as a quadratic.
                        a, b, c = n + z_squared, -(2 * k + z_squared), k * k / n
                        discriminant = (b * b - 4 * a * c).sqrt()
                        expected = [float((-b - discriminant) / (2 * a)),
                                    float((-b + discriminant) / (2 * a))]
                        lower, upper = wilson(successes, count)
                        self.assertAlmostEqual(lower, expected[0], places=14)
                        self.assertAlmostEqual(upper, expected[1], places=14)
                        self.assertLessEqual(lower, successes / count)
                        self.assertGreaterEqual(upper, successes / count)
