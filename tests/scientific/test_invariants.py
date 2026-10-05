import json
import unittest

from pydantic import ValidationError

from controlomics.project import parse_project_json
from tests.fixtures import executed_project, payload, receipt, reviewed_project


class ScientificInvariantTests(unittest.TestCase):
    def test_publication_existence_does_not_imply_entailment(self):
        data = reviewed_project()
        data["controls"][0]["supporting_evidence"] = []
        with self.assertRaises(ValidationError):
            parse_project_json(json.dumps(data))

    def test_support_requires_identity_and_entailment_checks(self):
        for mutate in (
            lambda data: data["evidence"][0].update(existence_status="UNVERIFIED", existence_check=None),
            lambda data: data["evidence"][0].update(existence_check=None),
            lambda data: data["controls"][0]["supporting_evidence"][0].update(entailment_check=None),
            lambda data: data["controls"][0]["supporting_evidence"][0].update(statement="An unrelated statement."),
        ):
            data = reviewed_project()
            mutate(data)
            with self.assertRaises(ValidationError):
                parse_project_json(json.dumps(data))

    def test_review_timestamps_follow_the_evidence_checks(self):
        for mutate in (
            lambda data: data["evidence"][0]["existence_check"].update(checked_at="2026-10-05T00:00:00Z"),
            lambda data: data["controls"][0]["supporting_evidence"][0]["entailment_check"].update(checked_at="2026-10-05T00:00:00Z"),
            lambda data: data["controls"][0]["verification"].update(checked_at="2026-10-05T00:00:00Z"),
        ):
            data = reviewed_project()
            mutate(data)
            with self.assertRaises(ValidationError):
                parse_project_json(json.dumps(data))

    def test_known_context_mismatch_blocks_evidence_backed_status(self):
        data = reviewed_project()
        context = data["controls"][0]["context_compatibility"]
        context["status"] = "MISMATCH"
        context["comparisons"][0].update(status="MISMATCH", evidence_value="A different organism")
        with self.assertRaises(ValidationError):
            parse_project_json(json.dumps(data))

    def test_unassessed_context_cannot_be_declared_matching(self):
        data = reviewed_project()
        data["controls"][0]["context_compatibility"]["comparisons"] = []
        with self.assertRaises(ValidationError):
            parse_project_json(json.dumps(data))

    def test_partial_context_requires_explicit_limitations(self):
        data = reviewed_project()
        context = data["controls"][0]["context_compatibility"]
        context["status"] = "PARTIAL"
        context["comparisons"].append({"dimension": "tissue", "status": "UNKNOWN", "rationale": "Not supplied."})
        with self.assertRaises(ValidationError):
            parse_project_json(json.dumps(data))
        context["limitations"] = ["Tissue compatibility is unknown."]
        self.assertEqual(parse_project_json(json.dumps(data)).controls[0].context_compatibility.status, "PARTIAL")

    def test_conflicts_cannot_be_hidden(self):
        data = reviewed_project()
        contradiction = dict(data["controls"][0]["supporting_evidence"][0])
        contradiction["relationship"] = "CONTRADICTS"
        data["controls"][0]["supporting_evidence"].append(contradiction)
        with self.assertRaises(ValidationError):
            parse_project_json(json.dumps(data))
        data["controls"][0]["evidence_status"] = "CONFLICTING_EVIDENCE"
        self.assertEqual(parse_project_json(json.dumps(data)).controls[0].evidence_status, "CONFLICTING_EVIDENCE")

    def test_method_status_cannot_bypass_required_biological_evidence(self):
        data = reviewed_project("METHOD_BASED")
        data["controls"][0]["evidence_required"] = True
        with self.assertRaises(ValidationError):
            parse_project_json(json.dumps(data))

    def test_causal_mismatch_remains_visible(self):
        data = payload()
        data["claims"][0].update(category="CAUSAL", computational_support="ASSOCIATIONAL")
        claim = parse_project_json(json.dumps(data)).claims[0]
        self.assertEqual(claim.category, "CAUSAL")
        self.assertEqual(len(claim.interpretation_warnings), 1)

    def test_pass_fail_requires_prespecified_rule(self):
        for mutate in (
            lambda data: data["execution_plans"][0].update(decision_rule=None),
            lambda data: data["execution_plans"][0]["decision_rule"].update(specified_at="2026-10-05T02:00:00Z"),
            lambda data: data["results"][0].update(decision_rule_id="missing"),
            lambda data: data["results"][0].update(execution_status="FAILED", errors=["Synthetic error"]),
        ):
            data = executed_project()
            mutate(data)
            with self.assertRaises(ValidationError):
                parse_project_json(json.dumps(data))

    def test_finite_numbers_interval_order_and_null_assumptions(self):
        for field, value in (
            ("p_value", 1.1), ("p_value", -0.1), ("p_value", "0.05"),
            ("confidence_interval", {"lower": 2.0, "upper": 1.0, "coverage": 0.95, "method": "Synthetic fixture"}),
            ("null_distribution_summary", {"draws": 10, "mean": 0.0, "standard_deviation": 1.0,
                                            "null_hypothesis": "Synthetic null", "exchangeability_assumptions": []}),
        ):
            data = executed_project()
            data["results"][0][field] = value
            with self.assertRaises(ValidationError):
                parse_project_json(json.dumps(data))

    def test_audit_requires_traceable_appropriate_results(self):
        data = executed_project()
        data["audits"] = [{
            "audit_id": "audit.synthetic", "claim_id": data["claims"][0]["claim_id"],
            "assessment": "ROBUST", "rationale": "Synthetic audit fixture only.",
            "result_ids": ["result.synthetic"], "reviewer": receipt(),
            "uncertainties": ["No actual evaluation occurred."], "limitations": ["Synthetic fixture."],
        }]
        parse_project_json(json.dumps(data))
        data["results"][0]["outcome"] = "INDETERMINATE"
        with self.assertRaises(ValidationError):
            parse_project_json(json.dumps(data))
        data["audits"][0]["assessment"] = "CONTROL_FAILURE"
        with self.assertRaises(ValidationError):
            parse_project_json(json.dumps(data))
