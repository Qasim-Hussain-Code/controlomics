"""Synthetic regressions for review actions and untrusted project imports."""

import base64
import contextlib
import copy
import http.client
import io
import json
import threading
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from controlomics.artifacts import create_review_bundle, open_review_bundle
from controlomics.cli import main
from controlomics.models import MessagesProvider, MethodBaseline
from controlomics.privacy import canonical_json, digest
from controlomics.project import parse_project_json
from controlomics.server import LocalServer, handle_action
from controlomics.workflow import audit_project, propose_and_review_new
from tests.fixtures import payload, reviewed_project


def proposed_project():
    """Create both hosted and researcher proposals without a review action."""

    source = payload()
    source["candidates"] = []
    draft = MethodBaseline().propose(None, None).controls[0]
    hosted = draft.model_copy(update={"name": "Synthetic hosted tautological reference",
        "rationale": "Rerun the same pipeline on the same synthetic input.",
        "method_basis": "Synthetic hostile proposal fixture; this basis is not applicability evidence."})
    proposal = MethodBaseline().propose(None, None).model_copy(update={"controls": (hosted,)})
    with patch("controlomics.server.MessagesProvider.complete", return_value=proposal), \
            patch("socket.create_connection", side_effect=AssertionError("Unexpected network access")):
        project = handle_action("/api/model/run", {"project": source,
            "fields": {"claim": "A hypothetical public claim"}, "public_confirmed": True,
            "endpoint": "https://model.example/v1/chat/completions", "model": "synthetic-fixture"})["project"]
    return handle_action("/api/specify-control", {"project": project,
        "specification": {"claim_id": source["claims"][0]["claim_id"],
            "control": draft.model_dump(mode="json")}})["project"]


def contradiction_payloads():
    for index in (0, 1):
        data = reviewed_project()
        data["controls"][0]["supporting_evidence"][index]["entailment_check"]["reviewer_kind"] = "PROGRAMMATIC"
        yield "automated_statement_" + str(index), data
    for level in ("BIOLOGICAL", "MECHANISTIC"):
        data = reviewed_project("METHOD_BASED")
        data["controls"][0]["scientific_level"] = level
        yield "biological_method_" + level, data
    for status in ("AGENT_PROPOSED", "UNVERIFIED"):
        data = reviewed_project()
        data["controls"][0]["evidence_status"] = status
        yield "unreviewed_control_" + status, data


def archive_with_project(project_data):
    valid = parse_project_json(json.dumps(reviewed_project()))
    with zipfile.ZipFile(io.BytesIO(create_review_bundle(valid))) as archive:
        documents = {name: archive.read(name) for name in archive.namelist()}
    documents["project.json"] = canonical_json(project_data)
    manifest = json.loads(documents["manifest.json"])
    manifest["artifacts"]["project.json"] = {
        "sha256": digest(documents["project.json"]), "bytes": len(documents["project.json"])}
    documents["manifest.json"] = canonical_json(manifest)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in documents.items():
            archive.writestr(name, content)
    return output.getvalue()


class ReviewActionTests(unittest.TestCase):
    def assert_old_candidates_preserved(self, original, updated):
        old_ids = {item["control_id"] for item in original["candidates"]}
        retained = [item for item in updated["candidates"] if item["control_id"] in old_ids]
        self.assertEqual(retained, original["candidates"])
        self.assertFalse(old_ids & {item["control_id"] for item in updated["controls"]})

    def test_analysis_and_claim_addition_do_not_review_existing_proposals(self):
        original = proposed_project()
        self.assertEqual([item["evidence_status"] for item in original["candidates"]],
            ["AGENT_PROPOSED", "UNVERIFIED"])
        for reasoner in ("design", "reference"):
            updated = handle_action("/api/analyze", {"project": original, "reasoner": reasoner})["project"]
            self.assert_old_candidates_preserved(original, updated)
            self.assertEqual(updated["controls"], [])
        added = handle_action("/api/add-claim", {"project": original, "claim": {
            "statement": "Another hypothetical claim", "category": "DESCRIPTIVE",
            "computational_support": "DESCRIPTIVE"}})["project"]
        self.assert_old_candidates_preserved(original, added)
        self.assertGreater(len(added["controls"]), 0)
        self.assertTrue(all(item["claim_tested"] == added["claims"][-1]["claim_id"]
            and item["evidence_status"] == "METHOD_BASED" for item in added["controls"]))
        events = [event for event in added["provenance"] if event["action"] == "CONTROL_REVIEW"]
        reviewed_ids = {item["control_id"] for item in added["controls"]}
        self.assertTrue(any(set(event["record_ids"]) == reviewed_ids for event in events))

    def test_saved_json_and_review_bundle_keep_candidates_unreviewed(self):
        original = proposed_project()
        parsed = parse_project_json(json.dumps(original))
        self.assertEqual(parsed.model_dump(mode="json"), original)
        raw = create_review_bundle(parsed)
        restored = handle_action("/api/open-bundle", {"archive_base64": base64.b64encode(raw).decode()})["project"]
        self.assertEqual(restored, original)
        updated = handle_action("/api/analyze", {"project": restored})["project"]
        self.assert_old_candidates_preserved(original, updated)
        self.assertEqual(updated["controls"], [])

    def test_candidate_execution_rejected_before_subprocess(self):
        original = proposed_project()
        updated = handle_action("/api/analyze", {"project": original})["project"]
        with patch("controlomics.execution.subprocess.run") as execute:
            for item in updated["candidates"]:
                with self.subTest(control=item["control_id"]), self.assertRaises(ValueError):
                    handle_action("/api/execute", {"project": updated, "control_id": item["control_id"],
                        "config": {"kind": "REFERENCE", "expected_difference": 2.0,
                            "assumptions": ["Synthetic rejection fixture."]},
                        "csv": "unit,label,value\na,0,0\nb,1,2\n"})
            execute.assert_not_called()

    def test_explicit_method_review_retains_its_existing_function(self):
        original = proposed_project()
        updated = handle_action("/api/method-review", {"project": original})["project"]
        self.assertEqual(updated["candidates"], [])
        self.assertEqual({item["control_id"] for item in updated["controls"]},
            {item["control_id"] for item in original["candidates"]})
        self.assertTrue(all(item["evidence_status"] == "METHOD_BASED" for item in updated["controls"]))

    def test_cli_analyze_and_add_claim_preserve_old_candidates_and_input(self):
        original = proposed_project()
        with TemporaryDirectory() as temporary, contextlib.redirect_stdout(io.StringIO()):
            folder = Path(temporary)
            source, output, claim = folder / "source.json", folder / "output.json", folder / "claim.json"
            source.write_bytes(canonical_json(original))
            original_bytes = source.read_bytes()
            claim.write_bytes(canonical_json({"statement": "A separate claim", "category": "DESCRIPTIVE",
                "computational_support": "DESCRIPTIVE"}))
            for reasoner in ("design", "reference"):
                self.assertEqual(main(["analyze", str(source), "--reasoner", reasoner,
                    "--output", str(output)]), 0)
                updated = json.loads(output.read_bytes())
                self.assert_old_candidates_preserved(original, updated)
                self.assertEqual(updated["controls"], [])
            self.assertEqual(main(["add-claim", str(source), str(claim), "--output", str(output)]), 0)
            updated = json.loads(output.read_bytes())
            self.assert_old_candidates_preserved(original, updated)
            self.assertGreater(len(updated["controls"]), 0)
            self.assertEqual(source.read_bytes(), original_bytes)

    def test_automatic_review_rejects_nonbuiltin_provider_before_proposal(self):
        source = payload()
        source["candidates"] = []
        project = parse_project_json(json.dumps(source))
        provider = MessagesProvider("https://model.example/v1/chat/completions", "fixture", None)
        with patch.object(provider, "propose") as propose:
            with self.assertRaises(ValueError):
                propose_and_review_new(project, provider)
            propose.assert_not_called()


class ImportGateTests(unittest.TestCase):
    def test_project_parser_and_api_reject_contradictory_review_states(self):
        for label, source in contradiction_payloads():
            with self.subTest(case=label):
                with self.assertRaises(ValueError):
                    parse_project_json(json.dumps(source))
                with self.assertRaises(ValueError):
                    handle_action("/api/analyze", {"project": source})

    def test_cli_rejects_contradictory_states_without_export(self):
        with TemporaryDirectory() as temporary, contextlib.redirect_stdout(io.StringIO()):
            source, output = Path(temporary) / "source.json", Path(temporary) / "output.json"
            for label, data in contradiction_payloads():
                with self.subTest(case=label):
                    source.write_bytes(canonical_json(data))
                    original = source.read_bytes()
                    output.write_bytes(b"retained previous export")
                    self.assertEqual(main(["validate", str(source)]), 1)
                    self.assertEqual(main(["analyze", str(source), "--output", str(output)]), 1)
                    self.assertEqual(output.read_bytes(), b"retained previous export")
                    self.assertEqual(source.read_bytes(), original)

    def test_self_consistent_archive_hashes_do_not_bypass_scientific_gate(self):
        for label, source in contradiction_payloads():
            with self.subTest(case=label):
                raw = archive_with_project(source)
                with self.assertRaises(ValueError):
                    open_review_bundle(raw)
                with self.assertRaises(ValueError):
                    handle_action("/api/open-bundle", {"archive_base64": base64.b64encode(raw).decode()})

    def test_valid_unsuccessful_reviews_and_uncertain_links_remain_loadable(self):
        insufficient = reviewed_project("INSUFFICIENT_EVIDENCE")
        for link in insufficient["controls"][0]["supporting_evidence"]:
            link.update(relationship="UNCERTAIN", entailment_check=None)
        self.assertEqual(parse_project_json(json.dumps(insufficient)).controls[0].evidence_status,
            "INSUFFICIENT_EVIDENCE")
        conflict = reviewed_project("CONFLICTING_EVIDENCE")
        conflict["controls"][0]["supporting_evidence"][1]["relationship"] = "CONTRADICTS"
        self.assertEqual(parse_project_json(json.dumps(conflict)).controls[0].evidence_status,
            "CONFLICTING_EVIDENCE")
        partial = reviewed_project()
        context = partial["controls"][0]["context_compatibility"]
        context.update(status="PARTIAL", limitations=["Synthetic unknown tissue applicability."])
        context["comparisons"].append({"dimension": "tissue", "status": "UNKNOWN",
            "rationale": "Synthetic missing-context fixture."})
        parsed = parse_project_json(json.dumps(partial))
        self.assertEqual(parsed.controls[0].evidence_status, "EVIDENCE_BACKED")
        self.assertEqual(parsed.controls[0].context_compatibility.status, "PARTIAL")

    def test_statement_receipt_kinds_are_distinct_from_identity_receipt_kinds(self):
        data = reviewed_project()
        self.assertEqual(data["evidence"][0]["existence_check"]["reviewer_kind"], "PROGRAMMATIC")
        self.assertEqual(parse_project_json(json.dumps(data)).controls[0].evidence_status, "EVIDENCE_BACKED")
        data["evidence"][0]["existence_check"]["reviewer_kind"] = "HUMAN"
        for link in data["controls"][0]["supporting_evidence"]:
            link["entailment_check"]["reviewer_kind"] = "PROGRAMMATIC"
        with self.assertRaises(ValueError):
            parse_project_json(json.dumps(data))


class AuditTraceabilityTests(unittest.TestCase):
    def test_each_claim_audit_cites_only_its_linked_publications(self):
        data = reviewed_project()
        data["claims"].append({**data["claims"][0], "claim_id": "claim.secondary"})
        first = data["controls"][0]
        second = copy.deepcopy(first)
        second.update(control_id="control.secondary", claim_tested="claim.secondary")
        for link in second["supporting_evidence"]:
            link["evidence_id"] = "evidence.secondary"
        data["controls"].append(second)
        for suffix in ("secondary", "unlinked"):
            record = copy.deepcopy(data["evidence"][0])
            record["evidence_id"] = "evidence." + suffix
            record["identifiers"][0]["value"] = "synthetic-" + suffix
            data["evidence"].append(record)
        audited = audit_project(parse_project_json(json.dumps(data)))
        self.assertEqual([item.evidence_ids for item in audited.audits],
            [("evidence.synthetic",), ("evidence.secondary",)])
        self.assertTrue(all(item.assessment == "INSUFFICIENT_EVIDENCE" for item in audited.audits))
        first["supporting_evidence"] = []
        first["evidence_status"] = "INSUFFICIENT_EVIDENCE"
        audited = audit_project(parse_project_json(json.dumps(data)))
        self.assertEqual(audited.audits[0].evidence_ids, ())
        self.assertEqual(audited.audits[1].evidence_ids, ("evidence.secondary",))


class HttpReviewGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = LocalServer(0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def request(self, path, data):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            connection.request("POST", path, json.dumps(data), {
                "Origin": "http://127.0.0.1:" + str(self.server.server_port),
                "X-Controlomics-Token": self.server.session_token, "Content-Type": "application/json"})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_http_analyze_keeps_imported_candidates_and_explicit_review_promotes(self):
        original = proposed_project()
        status, returned = self.request("/api/analyze", {"project": original})
        self.assertEqual(status, 200)
        self.assertEqual(returned["project"]["candidates"], original["candidates"])
        self.assertEqual(returned["project"]["controls"], [])
        status, returned = self.request("/api/method-review", {"project": returned["project"]})
        self.assertEqual(status, 200)
        self.assertEqual(returned["project"]["candidates"], [])
        self.assertEqual(len(returned["project"]["controls"]), 2)

    def test_http_rejects_each_inconsistent_import_with_redacted_error(self):
        for label, source in contradiction_payloads():
            with self.subTest(case=label):
                source["controls"][0]["verification"]["reviewer"] = "private_sentinel"
                status, returned = self.request("/api/analyze", {"project": source})
                self.assertEqual(status, 400)
                self.assertNotIn("private_sentinel", json.dumps(returned))
