import unittest

from controlomics.benchmark import run_benchmark, wilson


class BenchmarkTests(unittest.TestCase):
    def test_development_cases_and_seeded_observations(self):
        report = run_benchmark(trials=20, seed=827)
        self.assertEqual(report["planted_software_findings"], {"detected": 6, "total": 6})
        self.assertEqual(report["synthetic_numerical_experiment"]["trials"], 20)
        self.assertIn("not an agent", " ".join(report["limitations"]))
        self.assertTrue(all(item["assessment"] == "INSUFFICIENT_EVIDENCE" for item in report["cases"]))
        self.assertEqual(wilson(0, 20)[0], 0)
        self.assertGreater(wilson(0, 20)[1], 0)
