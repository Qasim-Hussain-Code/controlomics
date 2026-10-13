"""Synthetic scoped-consent records do not authorize an active hosted session."""

import io
import json
import socket
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pydantic import ValidationError

from controlomics.artifacts import create_review_bundle, open_review_bundle
from controlomics.execution import ExecutionConfig, build_package, execute_local
from controlomics.evaluation import EvaluationBundle, bundle_hash
from controlomics.hosting_privacy import (
    HOSTED_PROCESSING_POLICY_REVISION,
    HostedProcessingReceipt,
    describe_processing_privacy,
    hosted_processing_receipt,
    record_hosted_input_summary,
    record_hosted_processing,
)
from controlomics.inputs import inspect_numeric_input
from controlomics.privacy import canonical_json, digest
from controlomics.project import parse_project_json
from controlomics.reports import render_report
from controlomics.workflow import propose, review_methods
from tests.fixtures import ROOT, payload, reviewed_project
from tests.scientific.test_evaluation import bundle_payload

ORIGIN = "https://controlomics.example.test"
GRANT = datetime(2026, 10, 13, 5, 0, 0, tzinfo=timezone.utc)
BINDING = "8" * 64


def hosted(project, binding=BINDING):
    return record_hosted_processing(project, processor_origin=ORIGIN,
        session_binding_sha256=binding, granted_at=GRANT)


def scientific_snapshots(project):
    data = project.model_dump(mode="json")
    data.pop("privacy")
    return canonical_json(data)


def technical_project():
    data = payload()
    data["candidates"] = []
    return review_methods(propose(parse_project_json(json.dumps(data))))


class HostedPrivacyTests(unittest.TestCase):
    def test_legacy_project_retains_fail_closed_local_default(self):
        project = parse_project_json(json.dumps(payload()))
        self.assertEqual(project.privacy.hosted_processing_receipts, ())
        self.assertFalse(project.privacy.network_enabled)
        self.assertEqual(project.privacy.storage, "LOCAL_ONLY")
        self.assertIn("project and raw inputs remain local", describe_processing_privacy(project))

    def test_legacy_archive_without_receipts_keeps_its_evaluation_binding(self):
        project = parse_project_json(json.dumps(payload()))
        evaluation = EvaluationBundle.model_validate_json(json.dumps(bundle_payload()))
        raw = create_review_bundle(project, evaluation=evaluation)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            documents = {name: archive.read(name) for name in archive.namelist()}
        legacy = json.loads(documents["project.json"])
        legacy["privacy"].pop("hosted_processing_receipts")
        documents["project.json"] = canonical_json(legacy)
        manifest = json.loads(documents["manifest.json"])
        manifest["artifacts"]["project.json"] = {
            "sha256": digest(documents["project.json"]), "bytes": len(documents["project.json"])}
        documents["manifest.json"] = canonical_json(manifest)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in documents.items():
                archive.writestr(name, content)
        restored, _, restored_evaluation, _, _ = open_review_bundle(buffer.getvalue())
        self.assertEqual(restored.privacy.hosted_processing_receipts, ())
        self.assertEqual(scientific_snapshots(restored), scientific_snapshots(project))
        self.assertEqual(bundle_hash(restored_evaluation), bundle_hash(evaluation))

    def test_receipt_changes_no_scientific_record_or_reviewed_control_hash(self):
        project = parse_project_json(json.dumps(reviewed_project()))
        previous = digest(canonical_json(project.controls[0].model_dump(mode="json")))
        updated = hosted(project)
        self.assertEqual(scientific_snapshots(updated), scientific_snapshots(project))
        self.assertEqual(digest(canonical_json(updated.controls[0].model_dump(mode="json"))), previous)
        self.assertEqual(updated.privacy.rationale, project.privacy.rationale)
        self.assertTrue(updated.controls[0].privacy_requirements.raw_data_must_remain_local)
        self.assertFalse(updated.controls[0].privacy_requirements.external_transmission_allowed)
        self.assertFalse(updated.privacy.network_enabled)
        receipt = updated.privacy.hosted_processing_receipts[0]
        self.assertFalse(receipt.provider_project_forwarding_allowed)
        self.assertFalse(receipt.project_persistence_allowed)

    def test_repeat_request_deduplicates_and_new_session_preserves_old_receipt(self):
        project = hosted(parse_project_json(json.dumps(payload())))
        repeated = hosted(project)
        self.assertEqual(repeated.model_dump_json(), project.model_dump_json())
        updated = hosted(repeated, "9" * 64)
        self.assertEqual(len(updated.privacy.hosted_processing_receipts), 2)
        self.assertEqual(updated.privacy.hosted_processing_receipts[0], project.privacy.hosted_processing_receipts[0])

    def test_conflicting_grant_cannot_rewrite_existing_session_receipt(self):
        project = hosted(parse_project_json(json.dumps(payload())))
        with self.assertRaises(ValidationError):
            record_hosted_processing(project, processor_origin=ORIGIN,
                session_binding_sha256=BINDING,
                granted_at=GRANT.replace(hour=6))
        self.assertEqual(project.privacy.hosted_processing_receipts[0].granted_at, GRANT)

    def test_receipt_forbids_noncanonical_origin_and_malformed_grant(self):
        for origin in (
            "http://controlomics.example.test", "https://controlomics.example.test/",
            "https://CONTROLomics.example.test", "https://secret@example.com",
            "https://controlomics.example.test:443", "https://controlomics.example.test/path",
            "https://controlomics.example.test?private=value", "https://controlomics.example.test#fragment",
            "https://controlomics..example.test", "https://controlomics.example.test\n",
        ):
            with self.subTest(origin=origin), self.assertRaises(ValidationError):
                hosted_processing_receipt(processor_origin=origin, session_binding_sha256=BINDING, granted_at=GRANT)
        for binding, grant in (("session credential", GRANT), (BINDING, GRANT.replace(tzinfo=None))):
            with self.subTest(binding=binding, grant=grant), self.assertRaises(ValidationError):
                hosted_processing_receipt(processor_origin=ORIGIN, session_binding_sha256=binding, granted_at=grant)

    def test_receipt_flags_and_policy_revision_fail_closed(self):
        receipt = hosted_processing_receipt(processor_origin=ORIGIN,
            session_binding_sha256=BINDING, granted_at=GRANT).model_dump(mode="json")
        for change in (
            {"project_persistence_allowed": True}, {"provider_project_forwarding_allowed": True},
            {"project_persistence_allowed": 0}, {"provider_project_forwarding_allowed": "false"},
            {"policy_revision": "unapproved-policy"}, {"authorization_kind": "IMPORTED_PERMISSION"},
            {"raw_input": "synthetic private data"},
        ):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                HostedProcessingReceipt.model_validate_json(json.dumps({**receipt, **change}))
        self.assertEqual(receipt["policy_revision"], HOSTED_PROCESSING_POLICY_REVISION)

    def test_imported_receipt_remains_metadata_and_never_enables_network(self):
        exported = hosted(parse_project_json(json.dumps(payload()))).model_dump_json()
        with patch.object(socket.socket, "connect", side_effect=AssertionError("Unexpected network")), \
                patch("socket.create_connection", side_effect=AssertionError("Unexpected network")):
            imported = parse_project_json(exported)
            self.assertFalse(imported.privacy.network_enabled)
            self.assertFalse(imported.privacy.hosted_processing_receipts[0].provider_project_forwarding_allowed)
            self.assertIn("unauthenticated historical attestations", render_report(imported))

    def test_report_and_bundle_preserve_cloud_exception_without_claiming_current_location(self):
        project = hosted(parse_project_json(json.dumps(reviewed_project())))
        report = render_report(project)
        self.assertNotIn("; project and raw inputs remain local", report)
        self.assertIn("default local baseline", report)
        self.assertIn(ORIGIN, report)
        self.assertIn("do not assert where this report was generated", report)
        self.assertIn("grant no active session permission", report)
        imported, ledger, evaluation, revisions, manifest = open_review_bundle(create_review_bundle(project))
        self.assertEqual(imported.model_dump_json(), project.model_dump_json())
        self.assertEqual(ledger, [])
        self.assertIsNone(evaluation)
        self.assertEqual(revisions, [])
        self.assertEqual(manifest.project_id, project.manifest.project_id)

    def test_summary_discloses_cloud_processing_without_changing_numeric_observations(self):
        raw = b"unit,label,value\na,0,1\nb,0,2\nc,1,4\nd,1,5\n"
        original = inspect_numeric_input(raw)
        receipt = hosted_processing_receipt(processor_origin=ORIGIN,
            session_binding_sha256=BINDING, granted_at=GRANT)
        updated = record_hosted_input_summary(original, receipt)
        before, after = original.model_dump(), updated.model_dump()
        before.pop("limitations")
        after.pop("limitations")
        self.assertEqual(before, after)
        self.assertEqual(updated.limitations[:-1], original.limitations)
        self.assertIn(ORIGIN, updated.limitations[-1])
        self.assertEqual(record_hosted_input_summary(updated, receipt).model_dump_json(), updated.model_dump_json())

    def test_receipt_collection_is_bounded_and_duplicate_sessions_rejected(self):
        data = hosted(parse_project_json(json.dumps(payload()))).model_dump(mode="json")
        receipt = data["privacy"]["hosted_processing_receipts"][0]
        data["privacy"]["hosted_processing_receipts"] = [receipt, receipt]
        with self.assertRaises(ValidationError):
            parse_project_json(json.dumps(data))
        data["privacy"]["hosted_processing_receipts"] = [
            {**receipt, "session_binding_sha256": f"{value:064x}"} for value in range(129)]
        with self.assertRaises(ValidationError):
            parse_project_json(json.dumps(data))

    def test_hosted_package_preserves_receipts_and_fixed_runner_bytes(self):
        original = technical_project()
        project = hosted(original)
        config = ExecutionConfig(kind="REFERENCE", expected_difference=2.0,
            assumptions=("Independent synthetic units for software tests.",))
        with TemporaryDirectory() as temporary:
            local_folder, hosted_folder = Path(temporary) / "local", Path(temporary) / "hosted"
            local_package = build_package(original, original.controls[0].control_id, config, local_folder)
            hosted_package = build_package(project, project.controls[0].control_id, config, hosted_folder)
            self.assertEqual(hosted_package.privacy.hosted_processing_receipts, project.privacy.hosted_processing_receipts)
            self.assertEqual(hosted_package.execution_plans[0].code_sha256, local_package.execution_plans[0].code_sha256)
            for filename in ("run_control.py", "stats.py", "export_storage.py", "verify_results.py"):
                self.assertEqual((local_folder / filename).read_bytes(), (hosted_folder / filename).read_bytes())
            self.assertFalse((local_folder / "hosting_processing.json").exists())
            receipt_bytes = (hosted_folder / "hosting_processing.json").read_bytes()
            metadata = json.loads(receipt_bytes)
            self.assertEqual(metadata["hosted_processing_receipts"],
                [item.model_dump(mode="json") for item in project.privacy.hosted_processing_receipts])
            manifest = json.loads((hosted_folder / "manifest.json").read_bytes())
            self.assertEqual(manifest["artifact_hashes"]["hosting_processing.json"], digest(receipt_bytes))
            self.assertIn("historical consent attestations", (hosted_folder / "README.md").read_text(encoding="utf-8"))

    def test_hosted_fixed_execution_retains_receipts_and_numeric_reference_outcome(self):
        project = hosted(technical_project())
        config = ExecutionConfig(kind="REFERENCE", expected_difference=2.0,
            assumptions=("Independent synthetic units for software tests.",))
        updated = execute_local(project, project.controls[0].control_id, config,
            (ROOT / "examples" / "positive_reference.csv").read_bytes())
        self.assertEqual(updated.privacy.hosted_processing_receipts, project.privacy.hosted_processing_receipts)
        self.assertEqual(updated.results[0].outcome, "PASS")
        self.assertEqual(updated.results[0].effect_estimate.value, 2.0)


if __name__ == "__main__":
    unittest.main()
