import contextlib
import hashlib
import io
import json
import math
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from controlomics.cli import main
from controlomics.execution import ExecutionConfig, execute_local
from controlomics.inputs import inspect_numeric_input
from controlomics.project import parse_project_json
from controlomics.server import handle_action
from controlomics.workflow import propose, review_methods
from tests.fixtures import payload

INDEPENDENT = b'unit,label,value\na,0,0\nb,0,1\nc,1,2\nd,1,3\n'
PAIRED = b'pair,condition,value\na,0,10\na,1,11\nb,0,20\nb,1,22\n'


class NumericInputTests(unittest.TestCase):
    def test_independent_summary_omits_raw_values_and_identifiers(self):
        summary = inspect_numeric_input(INDEPENDENT)
        self.assertEqual((summary.rows, summary.group_zero_units, summary.group_one_units), (4, 2, 2))
        self.assertIsNone(summary.complete_pairs)
        self.assertEqual(summary.input_sha256, hashlib.sha256(INDEPENDENT).hexdigest())
        self.assertEqual(summary.input_bytes, len(INDEPENDENT))
        self.assertEqual(set(summary.model_dump()) - {'schema_version', 'adapter', 'input_sha256', 'input_bytes', 'rows', 'group_zero_units', 'group_one_units', 'complete_pairs', 'utf8_bom', 'limitations'}, set())

    def test_pair_summary_keeps_original_bom_bytes(self):
        raw = b'\xef\xbb\xbf' + PAIRED
        summary = inspect_numeric_input(raw, 'PAIRED_DIFFERENCE')
        self.assertEqual((summary.rows, summary.complete_pairs), (4, 2))
        self.assertEqual(summary.group_zero_units + summary.group_one_units, 0)
        self.assertTrue(summary.utf8_bom)
        self.assertEqual(summary.input_sha256, hashlib.sha256(raw).hexdigest())

    def test_invalid_shapes_encoding_numbers_and_budgets_rejected(self):
        for raw, adapter in ((INDEPENDENT, 'unknown'), (INDEPENDENT, 'PAIRED_DIFFERENCE'),
            (PAIRED, 'INDEPENDENT_REFERENCE'), (INDEPENDENT.replace(b'1', b'NaN'), 'INDEPENDENT_REFERENCE'),
            (INDEPENDENT.replace(b'a,0', b'\xff,0'), 'INDEPENDENT_REFERENCE'), (b'x' * (2 * 1024 * 1024 + 1), 'INDEPENDENT_REFERENCE')):
            with self.subTest(adapter=adapter), self.assertRaises(ValueError):
                inspect_numeric_input(raw, adapter)

    def test_server_inspection_never_executes_or_sends(self):
        with patch('controlomics.server.execute_local', side_effect=AssertionError('unexpected execution')), patch('socket.create_connection', side_effect=AssertionError('unexpected network')):
            response = handle_action('/api/inspect-input', {'csv': INDEPENDENT.decode(), 'adapter': 'INDEPENDENT_REFERENCE'})
        self.assertEqual(response['input_summary']['rows'], 4)
        self.assertNotIn('project', response)

    def test_cli_inspection_and_redacted_failure(self):
        with TemporaryDirectory() as directory:
            source, output = Path(directory) / 'input.csv', Path(directory) / 'summary.json'
            source.write_bytes(PAIRED)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['inspect-input', str(source), '--adapter', 'PAIRED_DIFFERENCE', '--output', str(output)]), 0)
            self.assertEqual(json.loads(output.read_bytes())['complete_pairs'], 2)
            source.write_bytes(b'pair,condition,value\na,0,private_sentinel\n')
            failure_output = Path(directory) / 'invalid.json'
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                self.assertEqual(main(['inspect-input', str(source), '--adapter', 'PAIRED_DIFFERENCE', '--output', str(failure_output)]), 1)
            self.assertNotIn('private_sentinel', buffer.getvalue())
            self.assertNotIn(str(source), buffer.getvalue())
            self.assertFalse(failure_output.exists())

    def test_fixed_runner_accepts_bom_and_large_finite_measurements(self):
        data = payload()
        data['candidates'] = []
        project = review_methods(propose(parse_project_json(json.dumps(data))))
        raw = b'\xef\xbb\xbfunit,label,value\na,0,0\nb,0,1e200\nc,1,2e200\nd,1,3e200\n'
        config = ExecutionConfig(kind='PERMUTATION', assumptions=('Synthetic extreme-scale software fixture only.',))
        result = execute_local(project, project.controls[0].control_id, config, raw).results[0]
        self.assertAlmostEqual(result.p_value, 1 / 3)
        self.assertTrue(math.isfinite(result.null_distribution_summary.standard_deviation))
        self.assertEqual(result.input_hashes[0].sha256, hashlib.sha256(raw).hexdigest())
        self.assertEqual(result.outcome, 'INDETERMINATE')
