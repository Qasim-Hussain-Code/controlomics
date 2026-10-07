import importlib.util
import json
import unittest
from unittest.mock import patch

from controlomics.evaluation import EvaluationBundle
from tests.scientific.test_evaluation import bundle_payload
from tests.fixtures import ROOT

spec = importlib.util.spec_from_file_location('study_readiness', ROOT/'scripts/check_study_readiness.py')
readiness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(readiness)


class StudyReadinessTests(unittest.TestCase):
    def parse(self, data):
        return EvaluationBundle.model_validate_json(json.dumps(data))

    def expert_fixture(self, reviewer):
        data = bundle_payload()
        data['dataset']['annotation_origin'] = 'EXPERT_ATTESTATION'
        data['dataset']['annotator'] = 'Synthetic curator for a software test only'
        data['judgment_origin'] = 'EXPERT_ATTESTATION'
        data['annotator'] = reviewer
        return data

    def test_unassessed_development_cases_cannot_establish_readiness(self):
        bundle = EvaluationBundle.model_validate_json((ROOT/'examples/benchmark.design.unassessed.json').read_bytes())
        with patch('socket.create_connection', side_effect=AssertionError('unexpected network')):
            report = readiness.audit([bundle])
        self.assertEqual(report['record_contract_status'], 'INCOMPLETE')
        self.assertEqual(report['partition_case_counts'], {'DEVELOPMENT': 6})
        self.assertEqual(report['declared_distinct_expert_judgment_names'], 0)
        self.assertFalse(report['scientific_independence_verified'])

    def test_repeated_reviewer_name_is_not_two_declared_reviewers(self):
        first = self.parse(self.expert_fixture('Synthetic reviewer A'))
        second = self.parse(self.expert_fixture('synthetic reviewer a'))
        report = readiness.audit([first, second], 1, 1)
        self.assertFalse(report['checks']['two_distinct_expert_judgment_names_declared'])
        self.assertFalse(report['scientific_independence_verified'])

    def test_review_sheets_must_retain_same_predictions(self):
        first = self.parse(self.expert_fixture('Synthetic reviewer A'))
        other = self.expert_fixture('Synthetic reviewer B')
        other['predictions']['provider'] = 'different synthetic provider'
        report = readiness.audit([first, self.parse(other)], 1, 1)
        self.assertFalse(report['checks']['same_reference_and_prediction_snapshots'])
        self.assertEqual(report['record_contract_status'], 'INCOMPLETE')

    def test_local_readiness_omits_private_text_and_names(self):
        data = self.expert_fixture('private_name_sentinel')
        data['dataset']['cases'][0]['description'] = 'private_description_sentinel'
        data['judgments'][0]['rationale'] = 'private_rationale_sentinel'
        report = readiness.audit([self.parse(data)], 1, 1)
        encoded = json.dumps(report)
        for value in ('private_name_sentinel', 'private_description_sentinel', 'private_rationale_sentinel'):
            self.assertNotIn(value, encoded)
        self.assertIn('bundle_sha256', report)

    def test_empty_inputs_and_invalid_minima_refused(self):
        with self.assertRaises(ValueError):
            readiness.audit([])
        with self.assertRaises(ValueError):
            readiness.audit([self.parse(bundle_payload())], 201, 1)
