import json
import unittest

from controlomics.models import MethodBaseline, Proposal
from controlomics.project import parse_project_json
from controlomics.reports import render_report
from controlomics.workflow import HumanReview, Intake, apply_review, audit_project, compare_context, new_project, propose, review_methods
from controlomics.schemas import BiologicalContext
from tests.fixtures import payload, reviewed_project


class WorkflowTests(unittest.TestCase):
    def test_baseline_vertical_slice_across_two_contexts(self):
        for name in ("transcriptomics.project.json", "microscopy_ml.project.json"):
            data = payload(name)
            data["candidates"] = []
            project = propose(parse_project_json(json.dumps(data)), MethodBaseline())
            self.assertEqual({item.control_class for item in project.candidates}, {"POSITIVE", "NEGATIVE"})
            self.assertTrue(all(item.evidence_status == "AGENT_PROPOSED" for item in project.candidates))
            project = audit_project(review_methods(project))
            self.assertEqual(len(project.controls), 2)
            self.assertTrue(all(item.evidence_status == "METHOD_BASED" for item in project.controls))
            self.assertEqual(project.audits[0].assessment, "INSUFFICIENT_EVIDENCE")
            self.assertIn("No biological recommendation", project.audits[0].uncertainties[0])
            self.assertIn("Controlomics scientific audit", render_report(project))

    def test_intake_preserves_claim_and_causal_mismatch(self):
        intake = Intake(question="A hypothetical question", analysis_description="A descriptive analysis",
            methods=("An arbitrary method not enumerated by the framework",), observed_result="Reported association",
            claim="A causal assertion", claim_category="CAUSAL", computational_support="ASSOCIATIONAL")
        project = new_project(intake)
        self.assertEqual(project.claims[0].statement, intake.claim)
        self.assertTrue(project.claims[0].interpretation_warnings)

    def test_unknown_and_mismatched_context_are_not_matches(self):
        analysis = BiologicalContext(organism="Saccharomyces cerevisiae", assay_type="counts")
        self.assertEqual(compare_context(analysis, BiologicalContext()).status, "UNKNOWN")
        self.assertEqual(compare_context(analysis, BiologicalContext(organism="Different organism")).status, "MISMATCH")
        self.assertEqual(compare_context(analysis, BiologicalContext(organism="Saccharomyces cerevisiae")).status, "PARTIAL")

    def test_report_escapes_untrusted_text(self):
        data = payload()
        data["claims"][0]["statement"] = "<script>alert('test')</script>"
        report = render_report(parse_project_json(json.dumps(data)))
        self.assertNotIn("<script>", report)
        self.assertIn("&lt;script&gt;", report)

    def test_model_cannot_return_verification_or_citation_fields(self):
        proposal = MethodBaseline().propose(None, None).model_dump(mode="json")
        proposal["controls"][0]["evidence_status"] = "EVIDENCE_BACKED"
        with self.assertRaises(ValueError):
            Proposal.model_validate_json(json.dumps(proposal))

    def test_human_review_requires_matching_source_excerpt(self):
        data = reviewed_project()
        control = data["controls"].pop()
        control.pop("verification")
        control["evidence_status"] = "UNVERIFIED"
        control["supporting_evidence"] = []
        data["candidates"] = [control]
        project = parse_project_json(json.dumps(data))
        reviews = [{"evidence_id": "evidence.synthetic", "statement": statement, "relationship": "SUPPORTS",
            "source_text": "Synthetic fixture excerpt.", "excerpt": "Synthetic fixture", "locator": "fixture",
            "rationale": "Synthetic human-review input for software testing, not an actual scientific review.",
            "source_context": {"organism": "Saccharomyces cerevisiae", "data_modality": "bulk transcript counts"}}
            for statement in (control["scientific_rationale"], control["expected_behavior"])]
        submission = {"control_id": control["control_id"], "reviewer": "synthetic_test_only",
                      "statements": reviews, "limitations": ["Synthetic review fixture only."]}
        reviewed = apply_review(project, HumanReview.model_validate_json(json.dumps(submission)))
        self.assertEqual(reviewed.controls[0].evidence_status, "EVIDENCE_BACKED")
        submission["statements"][0]["excerpt"] = "Not in source"
        with self.assertRaises(ValueError):
            apply_review(project, HumanReview.model_validate_json(json.dumps(submission)))
