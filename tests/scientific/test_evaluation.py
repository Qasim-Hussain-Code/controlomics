import unittest

from controlomics.evaluation import (EvaluationBundle, EvaluationDataset,
    annotation_template, compare_annotations, evaluate, run_dataset)


def bundle_payload():
    return {"dataset": {"dataset_id": "fixture", "annotation_origin": "DEVELOPMENT_FIXTURE", "limitations": ["Synthetic scoring fixture only."],
        "cases": [{"case_id": "case.a", "description": "Synthetic case", "partition": "DEVELOPMENT", "source_group": "source.a",
            "references": [{"reference_id": "positive", "description": "Synthetic reference", "control_class": "POSITIVE", "essential": True},
                           {"reference_id": "negative", "description": "Synthetic reference", "control_class": "NEGATIVE", "essential": True}],
            "expected_findings": ["missing_unit"]},
            {"case_id": "case.b", "description": "Synthetic abstention", "partition": "TEST", "source_group": "source.b",
             "references": [{"reference_id": "positive", "description": "Synthetic reference", "control_class": "POSITIVE", "essential": True}], "expected_findings": []}]},
        "predictions": {"run_id": "run.fixture", "provider": "synthetic_fixture", "limitations": ["Not a model evaluation."], "cases": [
            {"case_id": "case.a", "abstained": False, "findings": ["missing_unit", "extra_finding"], "execution_states": ["COMPLETED", "FAILED", "BLOCKED"],
             "controls": [{"control_id": "p1", "control_class": "POSITIVE", "scientific_level": "TECHNICAL", "description": "Synthetic recommendation", "probability_appropriate": 0.8},
                          {"control_id": "p2", "control_class": "NEGATIVE", "scientific_level": "TECHNICAL", "description": "Synthetic recommendation", "probability_appropriate": 0.2}]},
            {"case_id": "case.b", "controls": [], "abstained": True}]},
        "judgment_origin": "DEVELOPMENT_FIXTURE", "judgments": [
            {"case_id": "case.a", "control_id": "p1", "appropriate": True, "unsupported": False, "matched_reference_ids": ["positive"], "rationale": "Synthetic judgment."},
            {"case_id": "case.a", "control_id": "p2", "appropriate": False, "unsupported": True, "rationale": "Synthetic judgment."}],
        "evidence_decisions": [{"unit_id": "identity.1", "case_id": "case.a", "layer": "CITATION_IDENTITY", "predicted_decision": True, "reference_decision": False, "rationale": "Synthetic decision fixture."}]}


class EvaluationTests(unittest.TestCase):
    def test_offline_runner_handles_maximum_length_case_identifiers(self):
        import json
        from tests.fixtures import ROOT
        data = json.loads((ROOT / "examples" / "benchmark.dataset.json").read_bytes())
        data["cases"] = data["cases"][:1]
        data["cases"][0]["case_id"] = "c" * 100
        dataset = EvaluationDataset.model_validate_json(json.dumps(data))
        run = run_dataset(dataset)
        self.assertEqual(run.cases[0].case_id, "c" * 100)
        self.assertTrue(all(len(control.control_id) <= 100 for control in run.cases[0].controls))

    def parse(self, data):
        import json
        return EvaluationBundle.model_validate_json(json.dumps(data))

    def test_metrics_have_independently_specified_denominators(self):
        report = evaluate(self.parse(bundle_payload()))
        metrics = report["metrics"]
        self.assertEqual(metrics["recommendation_precision"]["value"], 0.5)
        self.assertAlmostEqual(metrics["critical_control_recall"]["value"], 1 / 3)
        self.assertEqual(metrics["unsupported_recommendation_rate"]["value"], 0.5)
        self.assertEqual(metrics["flaw_detection_precision"]["value"], 0.5)
        self.assertEqual(metrics["flaw_detection_recall"]["value"], 1)
        self.assertEqual(metrics["execution_success"]["value"], 0.5)
        self.assertEqual(metrics["citation_identity_accuracy"]["value"], 0)
        self.assertIsNone(metrics["statement_entailment_accuracy"]["value"])
        self.assertAlmostEqual(metrics["binary_quadratic_score"]["value"], 0.04)
        self.assertEqual(report["coverage"]["blocked_executions"], 1)

    def test_unknown_judgments_do_not_become_successes_or_complete_recall(self):
        data = bundle_payload()
        data["judgments"][1]["appropriate"] = None
        data["judgments"][1]["unsupported"] = None
        report = evaluate(self.parse(data))
        self.assertEqual(report["metrics"]["recommendation_precision"]["denominator"], 1)
        self.assertEqual(report["metrics"]["critical_control_recall"]["denominator"], 1)
        self.assertEqual(report["metrics"]["critical_control_recall"]["value"], 0)
        self.assertEqual(report["coverage"]["uncertain_or_missing_appropriateness"], 1)

    def test_unassessed_template_has_no_quality_score(self):
        source = self.parse(bundle_payload())
        template = annotation_template(source.dataset, source.predictions)
        report = evaluate(template)
        self.assertIsNone(report["metrics"]["recommendation_precision"]["value"])
        self.assertIsNone(report["metrics"]["reference_control_recall"]["value"])
        self.assertIsNone(report["metrics"]["unsupported_recommendation_rate"]["value"])
        self.assertEqual(template.judgment_origin, "UNASSESSED")

    def test_duplicate_or_foreign_reference_matches_are_rejected(self):
        data = bundle_payload()
        data["judgments"][0]["matched_reference_ids"] = ["unknown"]
        with self.assertRaises(ValueError):
            self.parse(data)
        data = bundle_payload()
        data["judgments"].append(data["judgments"][0])
        with self.assertRaises(ValueError):
            self.parse(data)

    def test_source_groups_cannot_cross_partitions(self):
        data = bundle_payload()
        data["dataset"]["cases"][1]["source_group"] = "source.a"
        with self.assertRaises(ValueError):
            self.parse(data)

    def test_partition_filter_includes_abstention_in_recall(self):
        report = evaluate(self.parse(bundle_payload()), "TEST")
        self.assertEqual(report["metrics"]["critical_control_recall"]["value"], 0)
        self.assertEqual(report["metrics"]["abstention_rate"]["value"], 1)
        self.assertIsNone(report["metrics"]["recommendation_precision"]["value"])

    def test_agreement_is_not_correctness_and_handles_degenerate_marginals(self):
        first = self.parse(bundle_payload())
        data = bundle_payload()
        data["judgments"][1]["appropriate"] = True
        second = self.parse(data)
        comparison = compare_annotations(first, second)
        self.assertEqual(comparison["observed_agreement"], 0.5)
        self.assertEqual(comparison["cohen_kappa"], 0)
        self.assertEqual(compare_annotations(first, first)["cohen_kappa"], 1)
        data["judgments"][0]["appropriate"] = True
        same = self.parse(data)
        self.assertIsNone(compare_annotations(same, same)["cohen_kappa"])

    def test_expert_origin_requires_an_explicit_supplied_name(self):
        data = bundle_payload()
        data["judgment_origin"] = "EXPERT_ATTESTATION"
        with self.assertRaises(ValueError):
            self.parse(data)
