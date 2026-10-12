"""Missing dimensions and explicit uncertainty are distinct annotation states."""

import json
import unittest
from copy import deepcopy

from controlomics.evaluation import (
    AnnotationSubmission, EvaluationBundle, annotation_template, apply_annotations,
    bundle_hash, compare_annotations, evaluate,
)
from tests.fixtures import ROOT
from tests.scientific.test_evaluation import bundle_payload


def parse(value):
    return EvaluationBundle.model_validate_json(json.dumps(value))


def agreement_payload(second=False, uncertain=False):
    value = bundle_payload()
    first_prediction = value["predictions"]["cases"][0]
    for index in range(3, 8):
        control = deepcopy(first_prediction["controls"][0])
        control["control_id"] = f"p{index}"
        first_prediction["controls"].append(control)
        value["judgments"].append({
            "case_id": "case.a", "control_id": f"p{index}",
            "appropriate": None, "unsupported": None,
            "appropriate_assessed": uncertain and index == 3,
            "unsupported_assessed": False, "rationale": "Synthetic state fixture.",
        })
    if second:
        value["judgments"][1]["appropriate"] = True
    return value


class JudgmentStateTests(unittest.TestCase):
    def test_untouched_rows_cannot_inflate_agreement(self):
        result = compare_annotations(parse(agreement_payload()), parse(agreement_payload(second=True)))
        self.assertEqual(result["paired_recommendations"], 2)
        self.assertEqual(result["observed_agreement"], 0.5)
        self.assertEqual(result["expected_marginal_agreement"], 0.5)
        self.assertEqual(result["cohen_kappa"], 0.0)

    def test_explicit_uncertainty_remains_a_nominal_category(self):
        result = compare_annotations(parse(agreement_payload(uncertain=True)),
            parse(agreement_payload(second=True, uncertain=True)))
        self.assertEqual(result["paired_recommendations"], 3)
        self.assertAlmostEqual(result["observed_agreement"], 2 / 3)
        self.assertAlmostEqual(result["expected_marginal_agreement"], 1 / 3)
        self.assertAlmostEqual(result["cohen_kappa"], 0.5)

    def test_unsupported_only_judgment_does_not_supply_appropriateness(self):
        value = agreement_payload()
        value["judgments"][2].update(unsupported=True, unsupported_assessed=True)
        source = parse(value)
        result = compare_annotations(source, source)
        self.assertEqual(result["paired_recommendations"], 2)
        report = evaluate(source)
        self.assertEqual(report["metrics"]["recommendation_precision"]["denominator"], 2)
        self.assertEqual(report["metrics"]["unsupported_recommendation_rate"]["denominator"], 3)
        self.assertEqual(report["coverage"]["appropriateness_uncertain"], 0)
        self.assertEqual(report["coverage"]["appropriateness_missing"], 5)

    def test_explicit_uncertainty_and_missing_have_separate_coverage(self):
        report = evaluate(parse(agreement_payload(uncertain=True)))
        self.assertEqual(report["coverage"]["appropriateness_uncertain"], 1)
        self.assertEqual(report["coverage"]["appropriateness_missing"], 4)
        self.assertEqual(report["coverage"]["uncertain_or_missing_appropriateness"], 5)

    def test_false_flags_cannot_hide_asserted_values_or_matches(self):
        for dimension in ("appropriate", "unsupported"):
            for decision in (True, False):
                with self.subTest(dimension=dimension, decision=decision):
                    value = bundle_payload()
                    item = value["judgments"][0]
                    item[dimension] = decision
                    item[f"{dimension}_assessed"] = False
                    with self.assertRaises(ValueError):
                        parse(value)
        value = bundle_payload()
        value["judgments"][0].update(appropriate=None, appropriate_assessed=False)
        with self.assertRaises(ValueError):
            parse(value)
        value = bundle_payload()
        value["evidence_decisions"][0]["reference_assessed"] = False
        with self.assertRaises(ValueError):
            parse(value)

    def test_unassessed_origin_rejects_explicit_uncertain_dimensions(self):
        source = parse(bundle_payload())
        blank = annotation_template(source.dataset, source.predictions).model_dump(mode="json")
        for flag in ("appropriate_assessed", "unsupported_assessed"):
            with self.subTest(flag=flag):
                value = deepcopy(blank)
                value["judgments"][0][flag] = True
                with self.assertRaises(ValueError):
                    parse(value)
        blank["evidence_decisions"] = [{"unit_id": "identity.1", "case_id": "case.a",
            "layer": "CITATION_IDENTITY", "predicted_decision": True,
            "reference_decision": None, "reference_assessed": True, "rationale": "Synthetic uncertainty."}]
        with self.assertRaises(ValueError):
            parse(blank)

    def test_legacy_snapshots_serialize_without_invented_flags(self):
        legacy = json.loads((ROOT / "examples/benchmark.design.unassessed.json").read_bytes())
        source = parse(legacy)
        self.assertEqual(source.model_dump(mode="json"), legacy)
        from controlomics.privacy import canonical_json, digest
        self.assertEqual(bundle_hash(source), digest(canonical_json(legacy)))
        value = bundle_payload()
        value["judgments"][0].update(appropriate=None, matched_reference_ids=[])
        assessed = parse(value)
        self.assertIsNone(assessed.judgments[0].appropriate_assessed)
        self.assertNotIn("appropriate_assessed", assessed.judgments[0].model_dump(mode="json"))
        self.assertEqual(compare_annotations(assessed, assessed)["paired_recommendations"], 2)

    def test_new_template_marks_dimensions_unjudged(self):
        source = parse(bundle_payload())
        blank = annotation_template(source.dataset, source.predictions)
        self.assertTrue(all(item.appropriate_assessed is False and item.unsupported_assessed is False
            for item in blank.judgments))
        self.assertIsNone(evaluate(blank)["metrics"]["recommendation_precision"]["value"])

    def test_partial_revision_preserves_evidence_predictions_and_flags(self):
        value = agreement_payload()
        value["judgments"] = value["judgments"][:3]
        value["judgments"][2].update(unsupported=True, unsupported_assessed=True)
        value["evidence_decisions"][0].update(reference_decision=None, reference_assessed=False)
        original = parse(value)
        data = {"bundle_sha256": bundle_hash(original), "judgment_origin": "DEVELOPMENT_FIXTURE",
            "annotator": "Synthetic software fixture", "human_attested": True,
            "judgments": [item.model_dump(mode="json") for item in original.judgments],
            "evidence_decisions": [item.model_dump(mode="json") for item in original.evidence_decisions]}
        submission = AnnotationSubmission.model_validate_json(json.dumps(data))
        updated, revision = apply_annotations(original, submission)
        restored = EvaluationBundle.model_validate_json(updated.model_dump_json())
        self.assertEqual(restored, updated)
        self.assertEqual(updated.dataset, original.dataset)
        self.assertEqual(updated.predictions, original.predictions)
        self.assertEqual(updated.evidence_decisions[0].predicted_decision, True)
        self.assertIs(updated.evidence_decisions[0].reference_assessed, False)
        self.assertEqual(compare_annotations(updated, updated)["paired_recommendations"], 2)
        self.assertIsNone(evaluate(updated)["metrics"]["citation_identity_accuracy"]["value"])
        self.assertEqual(revision.previous_sha256, bundle_hash(original))
        self.assertEqual(revision.updated_sha256, bundle_hash(updated))

    def test_no_supplied_appropriateness_produces_no_agreement(self):
        value = agreement_payload()
        value["judgments"] = value["judgments"][2:]
        source = parse(value)
        result = compare_annotations(source, source)
        self.assertEqual(result["paired_recommendations"], 0)
        self.assertIsNone(result["observed_agreement"])
        self.assertIsNone(result["cohen_kappa"])
