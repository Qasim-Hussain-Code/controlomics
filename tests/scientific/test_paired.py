import itertools
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from controlomics.execution import ExecutionConfig, build_package, execute_local, specify_paired_control
from controlomics.project import parse_project_json
from controlomics.statistics import read_paired_bytes, paired_mean, paired_permutation, paired_bootstrap
from controlomics.workflow import propose, review_methods
from tests.fixtures import payload

CSV = b'pair,condition,value\na,0,10\na,1,11\nb,0,20\nb,1,22\nc,0,30\nc,1,33\n'


class PairedTests(unittest.TestCase):
    def project(self):
        data = payload()
        data['candidates'] = []
        project = review_methods(propose(parse_project_json(json.dumps(data))))
        return specify_paired_control(project, project.claims[0].claim_id,
            'Hypothetical complete pairs are the units for this software fixture.', ['Synthetic independent pairs; sign-invariant null.'])

    def config(self, kind='PERMUTATION'):
        return ExecutionConfig(adapter='PAIRED_DIFFERENCE', kind=kind, adapter_rationale='Complete pairs correspond to the specified unit.',
            assumptions=('Synthetic independent pairs and sign invariance under the tested null.',), draws=199, random_seed=7)

    def test_complete_pair_parser_is_order_invariant(self):
        self.assertEqual(read_paired_bytes(CSV), [1.0, 2.0, 3.0])
        rows = CSV.decode().splitlines()
        self.assertEqual(read_paired_bytes((rows[0] + '\n' + '\n'.join(reversed(rows[1:]))).encode()), [1.0, 2.0, 3.0])
        self.assertEqual(read_paired_bytes(b'\xef\xbb\xbf' + CSV), [1.0, 2.0, 3.0])

    def test_pair_mean_retains_representable_subnormal_values(self):
        self.assertEqual(paired_mean([5e-324, 5e-324]), 5e-324)
        self.assertEqual(paired_permutation([5e-324, 5e-324])['p_value'], 0.5)

    def test_incomplete_duplicate_nonfinite_and_oversized_pairs_rejected(self):
        for raw in (CSV.replace(b'c,1,33\n', b''), CSV + b'a,0,10\n', CSV.replace(b'11', b'nan'),
            b'pair,condition,value\na,0,0\na,1,1\n', CSV.replace(b'a,0,10', b'a,2,10'), CSV.replace(b'a,0,10', b' a,0,10'), b'x' * (2 * 1024 * 1024 + 1)):
            with self.subTest(raw=raw[:40]), self.assertRaises(ValueError):
                read_paired_bytes(raw)

    def test_exact_tail_matches_independent_enumeration(self):
        values = [1.0, 2.0, 3.0]
        null = [sum(sign * value for sign, value in zip(signs, values)) / 3 for signs in itertools.product((-1, 1), repeat=3)]
        result = paired_permutation(values)
        self.assertEqual(result['p_value'], sum(abs(value) >= 2 for value in null) / 8)
        self.assertEqual(result['p_value'], 0.25)
        self.assertEqual(result['draws'], 8)
        self.assertTrue(result['exact'])

    def test_sign_flip_tail_is_scale_invariant_and_monte_carlo_seeded(self):
        for scale in (1e-200, 1e200):
            self.assertEqual(paired_permutation([scale, 2 * scale, 3 * scale])['p_value'], 0.25)
        first = paired_permutation([1.0] * 13, draws=199, seed=17)
        self.assertEqual(first, paired_permutation([1.0] * 13, draws=199, seed=17))
        self.assertFalse(first['exact'])
        self.assertGreaterEqual(first['p_value'], 1 / 200)

    def test_whole_pair_bootstrap_keeps_constant_difference(self):
        result = paired_bootstrap([2.0] * 4, seed=18, draws=199)
        self.assertEqual((result['lower'], result['upper']), (2.0, 2.0))
        self.assertEqual(paired_bootstrap([1.0, 2.0, 3.0], seed=18), paired_bootstrap([1.0, 2.0, 3.0], seed=18))

    def test_actual_local_paired_runner_and_binding(self):
        project = self.project()
        for kind in ('PERMUTATION', 'BOOTSTRAP'):
            result_project = execute_local(project, project.controls[-1].control_id, self.config(kind), CSV)
            result = result_project.results[-1]
            self.assertEqual(result.outcome, 'INDETERMINATE')
            self.assertEqual(result.effect_estimate.value, 2.0)
            self.assertEqual(result.input_hashes[0].input_id, 'paired_units')
            if kind == 'PERMUTATION':
                self.assertEqual(result.p_value, 0.25)
            else:
                self.assertIn('Complete-pair', result.confidence_interval.method)

    def test_adapter_cannot_silently_execute_other_specifications(self):
        project = self.project()
        with TemporaryDirectory() as temporary:
            folder = Path(temporary) / 'package'
            with self.assertRaises(ValueError):
                build_package(project, project.controls[0].control_id, self.config(), folder)
            self.assertFalse(folder.exists())
            with self.assertRaises(ValueError):
                build_package(project, project.controls[-1].control_id, ExecutionConfig(kind='PERMUTATION', assumptions=('Synthetic units',)), folder)

    def test_paired_reference_and_missing_rationale_rejected(self):
        for change in ({'kind': 'REFERENCE', 'expected_difference': 2.0}, {'adapter_rationale': None}):
            data = self.config().model_dump(mode='json')
            data.update(change)
            with self.assertRaises(ValueError):
                ExecutionConfig.model_validate_json(json.dumps(data))

    def test_specifying_paired_control_does_not_review_unrelated_candidates(self):
        project = parse_project_json(json.dumps(payload()))
        previous_ids = {item.control_id for item in project.candidates}
        updated = specify_paired_control(project, project.claims[0].claim_id, 'Synthetic complete-pair fixture.', ['Synthetic independent pairs.'])
        self.assertEqual({item.control_id for item in updated.candidates}, previous_ids)
        self.assertTrue(all(item.evidence_status == 'UNVERIFIED' for item in updated.candidates))
        self.assertEqual(len(updated.controls), 1)
