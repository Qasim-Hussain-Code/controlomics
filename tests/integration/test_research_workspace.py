import contextlib
import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from controlomics.cli import main
from controlomics.models import MethodBaseline
from controlomics.execution import ExecutionConfig, build_package
from controlomics.project import parse_project_json
from controlomics.server import handle_action
from controlomics.workflow import HumanReview, apply_review, review_template
from tests.fixtures import ROOT, payload, reviewed_project


class ResearchWorkspaceTests(unittest.TestCase):
    def test_description_claim_and_candidate_round_trip_without_network(self):
        with patch("socket.create_connection", side_effect=AssertionError("Unexpected network access")):
            draft = handle_action("/api/interpret", {"description": "Question: A hypothetical question\nClaim: A stated conclusion"})["draft"]
            self.assertNotIn("observed_result", draft["fields"])
            data = handle_action("/api/analyze", {"project": payload()})
            initial = len(data["project"]["controls"])
            data = handle_action("/api/add-claim", {"project": data["project"], "claim": {
                "statement": "A second hypothetical predictive claim", "category": "PREDICTIVE", "computational_support": "PREDICTIVE"}})
            self.assertEqual(len(data["design_profiles"]), 2)
            self.assertGreater(len(data["project"]["controls"]), initial)
            claim_id = data["project"]["claims"][1]["claim_id"]
            draft_control = MethodBaseline().propose(None, None).controls[0].model_dump(mode="json")
            data = handle_action("/api/specify-control", {"project": data["project"], "specification": {
                "claim_id": claim_id, "control": draft_control}})
            candidate = data["project"]["candidates"][0]
            self.assertEqual(candidate["claim_tested"], claim_id)
            self.assertEqual(candidate["evidence_status"], "UNVERIFIED")
            saved = parse_project_json(json.dumps(data["project"]))
            self.assertEqual(saved.candidates[0].control_id, candidate["control_id"])
            reviewed = handle_action("/api/method-review", {"project": data["project"]})["project"]
            self.assertEqual(len(reviewed["candidates"]), 0)
            self.assertEqual(reviewed["controls"][-1]["evidence_status"], "METHOD_BASED")

    def test_browser_json_parser_retains_duplicate_key_rejection(self):
        for content in ('{"claim":"first","claim":"private_sentinel"}', '{"value":NaN}'):
            with self.assertRaises(ValueError):
                handle_action("/api/parse-json", {"content": content})
        self.assertEqual(handle_action("/api/parse-json", {"content": '{"value":2}'})["value"], {"value": 2})

    def test_hosted_multi_claim_binding_precedes_external_completion(self):
        project = handle_action("/api/add-claim", {"project": payload(), "claim": {
            "statement": "Another claim", "category": "DESCRIPTIVE", "computational_support": "DESCRIPTIVE"}})["project"]
        settings = {"project": project, "fields": {"claim": "Public claim"}, "public_confirmed": True,
            "endpoint": "https://model.example/v1/chat/completions", "model": "fixture", "approve_hash": "invalid"}
        with patch("controlomics.server.MessagesProvider.complete") as complete:
            for claim_id in (None, "unknown.claim"):
                with self.assertRaises(ValueError):
                    handle_action("/api/model/run", {**settings, "claim_id": claim_id})
            complete.assert_not_called()

    def test_re_review_requires_current_snapshot_and_preserves_conflict(self):
        project = parse_project_json(json.dumps(reviewed_project()))
        control = project.controls[0]
        template = review_template(project, control.control_id)
        submission = {"control_id": control.control_id, "reviewer": "synthetic_test_only", "limitations": ["Synthetic regression fixture, not human scientific review."],
            "statements": [{"evidence_id": project.evidence[0].evidence_id, "statement": statement, "relationship": relationship,
                "source_text": "Synthetic fixture text only.", "excerpt": "Synthetic fixture", "locator": "test fixture",
                "rationale": "Synthetic state transition fixture.", "source_context": {"organism": "Saccharomyces cerevisiae", "data_modality": "bulk transcript counts"}}
                for statement, relationship in zip(template["statements"], ("SUPPORTS", "CONTRADICTS"))]}
        for approval in (None, "0" * 64):
            with self.assertRaises(ValueError):
                apply_review(project, HumanReview.model_validate_json(json.dumps({**submission, "supersedes_review_sha256": approval})))
        revised = apply_review(project, HumanReview.model_validate_json(json.dumps({**submission, "supersedes_review_sha256": template["supersedes_review_sha256"]})))
        self.assertEqual(len(revised.controls), 1)
        self.assertEqual(revised.controls[0].evidence_status, "CONFLICTING_EVIDENCE")
        self.assertIn(template["supersedes_review_sha256"], revised.provenance[-1].warnings[0])
        self.assertNotEqual(review_template(revised, control.control_id)["supersedes_review_sha256"], template["supersedes_review_sha256"])

    def test_offline_evaluation_cli_and_api_preserve_unassessed_results(self):
        with TemporaryDirectory() as temporary, contextlib.redirect_stdout(io.StringIO()), patch("socket.create_connection", side_effect=AssertionError("Unexpected network access")):
            folder = Path(temporary)
            dataset = ROOT / "examples" / "benchmark.dataset.json"
            predictions, sheet, report = [folder / name for name in ("predictions.json", "sheet.json", "report.json")]
            self.assertEqual(main(["run-dataset", str(dataset), "--output", str(predictions)]), 0)
            self.assertEqual(main(["annotation-template", str(dataset), str(predictions), "--output", str(sheet)]), 0)
            self.assertEqual(main(["evaluate", str(sheet), "--output", str(report)]), 0)
            measured = json.loads(report.read_bytes())
            self.assertIsNone(measured["metrics"]["recommendation_precision"]["value"])
            returned = handle_action("/api/evaluate", {"bundle": json.loads(sheet.read_bytes())})["evaluation"]
            self.assertEqual(returned["metrics"], measured["metrics"])
            self.assertEqual(returned["coverage"]["cases"], 6)
            self.assertEqual(main(["evaluate", str(sheet), "--partition", "TEST", "--output", str(folder / "absent.json")]), 1)
            self.assertFalse((folder / "absent.json").exists())

    def test_numeric_adapter_rejects_unimplemented_scientific_mappings(self):
        raw = payload()
        raw["candidates"] = []
        project = parse_project_json(json.dumps(handle_action("/api/analyze", {"project": raw})["project"]))
        control = next(item for item in project.controls if item.scientific_level == "STATISTICAL")
        with TemporaryDirectory() as temporary:
            for kind in ("REFERENCE", "PERMUTATION", "BOOTSTRAP"):
                config = ExecutionConfig(kind=kind, expected_difference=0.0 if kind == "REFERENCE" else None, assumptions=("Synthetic unsupported-mapping regression.",))
                target = Path(temporary) / kind
                with self.assertRaises(ValueError):
                    build_package(project, control.control_id, config, target)
                self.assertFalse(target.exists())

    def test_description_cli_rejects_oversized_unicode_without_truncation(self):
        with TemporaryDirectory() as temporary, contextlib.redirect_stdout(io.StringIO()):
            source, target = Path(temporary) / "brief.txt", Path(temporary) / "draft.json"
            source.write_text("x" + "\u03bb" * 7000, encoding="utf-8")
            self.assertEqual(main(["interpret", str(source), "--output", str(target)]), 1)
            self.assertFalse(target.exists())
