import hashlib
import importlib.util
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.fixtures import ROOT

spec = importlib.util.spec_from_file_location('numerical_validation', ROOT/'scripts/run_numerical_validation.py')
validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation)


class NumericalProtocolTests(unittest.TestCase):
    def test_freeze_records_exact_sources_without_computing_outcomes(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/'protocol.json'
            validation.freeze(path)
            plan = json.loads(path.read_bytes())
            self.assertNotIn('results', plan)
            self.assertNotIn('numeric_reference_agreement', plan)
            for name, expected in plan['source_sha256'].items():
                self.assertEqual(expected, hashlib.sha256((ROOT/name).read_bytes()).hexdigest())
            retained = path.read_bytes()
            with self.assertRaises(ValueError):
                validation.freeze(path)
            self.assertEqual(path.read_bytes(), retained)

    def test_reference_cases_preserve_whole_pair_indices_and_sample_bounds(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/'protocol.json'
            validation.freeze(path)
            cases = validation.make_cases(json.loads(path.read_bytes()))
        self.assertEqual(len(cases), 128)
        for case in cases:
            paired = case['adapter'] == 'PAIRED_DIFFERENCE'
            self.assertEqual(len(case['indices']), 1 if paired else 2)
            if paired:
                self.assertEqual(len(case['left']), len(case['right']))
            for column, rows in enumerate(case['indices']):
                size = len(case['left'] if column == 0 else case['right'])
                self.assertEqual(len(rows), case['draws'])
                self.assertTrue(all(len(row) == size and all(0 <= index < size for index in row) for row in rows))
