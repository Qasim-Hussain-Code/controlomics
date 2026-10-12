"""Synthetic regressions for screening, transport, ledger, and JSON boundaries."""

import io
import json
import socket
import unittest
import zipfile
from unittest.mock import patch

from controlomics.artifacts import create_review_bundle, open_review_bundle, validated_ledger
from controlomics.evidence import EuropePMC
from controlomics.privacy import ApprovalRequired, SafeField, SafeTransport, canonical_json, digest, screen_text
from controlomics.project import decode_json, parse_project_json
from controlomics.reports import render_report
from tests.fixtures import payload


class PrivacyAuditBoundaryTests(unittest.TestCase):
    def test_recognized_sensitive_forms_rejected_at_safe_field_boundary(self):
        samples = [
            "ACGU" * 20, "acgu" * 20, "prefix_" + "ACGT" * 20,
            "ACDEFGHIKLMNPQRSTVWY" * 3,
            "github_pat_" + "a" * 24, "ghp_" + "a" * 12,
            "Bearer " + "x" * 24, "bearer " + "x" * 24,
            "AKIA" + "A" * 16, "ASIA" + "A" * 16,
            "sk-" + "b" * 16, "hf_" + "c" * 16, "AIza" + "d" * 35,
            "MRN 00123456", "mrn: 00123456", "MRN #00123456", "MRN=00123456",
        ]
        samples.extend(prefix + " ".join(["ACGT" * bases] * (20 // bases))
            for prefix in ("", "sequence_") for bases in (1, 2, 4, 5))
        samples.extend("gh" + variant + "_" + "z" * 24 for variant in "ousr")
        for index, text in enumerate(samples):
            with self.subTest(index=index):
                self.assertEqual(screen_text(text), "RESTRICTED")
                for name in ("claim", "public_query"):
                    with self.assertRaisesRegex(ValueError, "privacy screening"):
                        SafeField(name, text, "SAFE")

    def test_ordinary_scientific_prose_is_not_reclassified_as_restricted(self):
        samples = (
            "RNA sequencing compares treatment and control samples using independent units.",
            "Protein abundance and ACTB expression require scientific interpretation.",
            "A method uses rank statistics; the recorded result remains uncertain.",
            "Medical record identifiers must remain local; no identifier is supplied here.",
            "ACGU" * 19,
            "ACDEFGHIKLMNPQRSTVWY" * 2 + "ACDEFGHIKLMNPQRSTVW",
        )
        for text in samples:
            with self.subTest(text=text):
                self.assertEqual(screen_text(text), "SENSITIVE_SCIENTIFIC")
                self.assertEqual(SafeField("claim", text, "SAFE").value, text)

    def request(self):
        transport = SafeTransport(frozenset({EuropePMC.host}))
        return transport, EuropePMC(transport).prepare_search("public method")

    def test_nonpublic_and_multicast_answers_never_start_connections(self):
        for address in ("127.0.0.1", "169.254.1.1", "100.64.0.1", "224.0.0.1",
                "239.255.255.250", "240.0.0.1", "2001:db8::1", "ff0e::1"):
            with self.subTest(address=address):
                transport, request = self.request()
                family = socket.AF_INET6 if ":" in address else socket.AF_INET
                answer = [(family, socket.SOCK_STREAM, 6, "", (address, 443))]
                with patch("socket.getaddrinfo", return_value=answer), \
                        patch("socket.create_connection") as connect, \
                        patch("http.client.HTTPSConnection") as https:
                    with self.assertRaises(ValueError):
                        transport.send(request, request.approval_hash)
                    connect.assert_not_called()
                    https.assert_not_called()
                self.assertEqual(transport.audit[0]["payload_transmission"], "NOT_STARTED")

    def test_mixed_dns_answers_reject_before_connection(self):
        transport, request = self.request()
        answer = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))
            for address in ("93.184.216.34", "224.0.0.1")]
        with patch("socket.getaddrinfo", return_value=answer), \
                patch("socket.create_connection") as connect:
            with self.assertRaises(ValueError):
                transport.send(request, request.approval_hash)
            connect.assert_not_called()

    def test_exact_approval_remains_required_before_dns(self):
        transport, request = self.request()
        with patch("socket.getaddrinfo") as lookup:
            with self.assertRaises(ApprovalRequired):
                transport.send(request, "0" * 64)
            lookup.assert_not_called()
        self.assertEqual(transport.audit, [])

    def event(self, status="BLOCKED", phase="NOT_STARTED"):
        _, request = self.request()
        return {**request.preview(), "request_sha256": request.approval_hash,
            "sent_at": "2026-10-11T00:00:00Z", "status": status,
            "body_sha256": None, "credential_supplied": False, "payload_transmission": phase}

    def project(self):
        return parse_project_json(json.dumps(payload()))

    def test_blocked_transmission_rejected_by_ledger_report_and_export(self):
        project = self.project()
        for phase in ("ATTEMPTED", "COMPLETED"):
            event = self.event(phase=phase)
            for operation in (lambda: validated_ledger([event]),
                    lambda: render_report(project, [event]),
                    lambda: create_review_bundle(project, [event])):
                with self.subTest(phase=phase), self.assertRaisesRegex(ValueError, "blocked request"):
                    operation()

    def test_consistent_blocked_failed_and_completed_ledgers_remain_accepted(self):
        events = [self.event()] + [self.event("FAILED", phase)
            for phase in ("NOT_STARTED", "ATTEMPTED", "COMPLETED")]
        completed = self.event("COMPLETED", "COMPLETED")
        completed.update(response_sha256=digest(b"{}"), response_bytes=2)
        events.append(completed)
        validated = validated_ledger(events)
        self.assertEqual([(item["status"], item["payload_transmission"]) for item in validated],
            [(item["status"], item["payload_transmission"]) for item in events])
        self.assertEqual(validated[-1]["response_sha256"], completed["response_sha256"])
        self.assertEqual(validated[-1]["response_bytes"], 2)
        _, restored, *_ = open_review_bundle(create_review_bundle(self.project(), events))
        self.assertEqual(restored, validated)

    def test_hash_consistent_archive_cannot_import_contradictory_ledger(self):
        raw = create_review_bundle(self.project(), [self.event()])
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            documents = {name: archive.read(name) for name in archive.namelist()}
        events = decode_json(documents["network_audit.json"])
        events[0]["payload_transmission"] = "COMPLETED"
        documents["network_audit.json"] = canonical_json(events)
        manifest = decode_json(documents["manifest.json"])
        manifest["artifacts"]["network_audit.json"] = {
            "sha256": digest(documents["network_audit.json"]),
            "bytes": len(documents["network_audit.json"])}
        documents["manifest.json"] = canonical_json(manifest)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in documents.items():
                archive.writestr(name, content)
        with self.assertRaisesRegex(ValueError, "blocked request"):
            open_review_bundle(buffer.getvalue())

    def test_literal_multicast_and_reserved_ledger_destinations_rejected(self):
        for host in ("224.0.0.1", "240.0.0.1", "[ff0e::1]", "[2001:db8::1]"):
            event = self.event()
            event.update(purpose="MODEL", method="POST", url="https://" + host + "/complete",
                body_sha256=digest(b"{}"))
            with self.subTest(host=host), self.assertRaisesRegex(ValueError, "not public"):
                validated_ledger([event])


class FiniteJsonBoundaryTests(unittest.TestCase):
    def test_overflowing_exponents_rejected_at_generic_decoder(self):
        for literal in ("1e400", "-1e400", "9.9e9999", "1e+999999"):
            for document in (literal, '{"x":' + literal + '}', '[0, {"x":' + literal + '}]'):
                for content in (document, document.encode()):
                    with self.subTest(literal=literal), self.assertRaisesRegex(ValueError, "nonfinite"):
                        decode_json(content)

    def test_finite_extreme_and_underflow_literals_remain_valid(self):
        result = decode_json('[1.7976931348623157e308,-1e308,1e-400,42,0.0]')
        self.assertEqual(result, [float.fromhex("0x1.fffffffffffffp+1023"), -1e308, 0.0, 42, 0.0])

    def test_existing_duplicate_constant_utf8_and_size_guards_remain_active(self):
        from controlomics.project import MAX_PROJECT_BYTES
        for content in ('{"x":1,"x":2}', '[NaN]', '[Infinity]', '[-Infinity]',
                b"\xff", b" " * (MAX_PROJECT_BYTES + 1)):
            with self.subTest(kind=type(content).__name__), self.assertRaises(ValueError):
                decode_json(content)
