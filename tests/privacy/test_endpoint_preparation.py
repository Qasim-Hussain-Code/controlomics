"""Endpoint previews and their ledgers share a local, redacted admission rule."""

import json
import socket
import ssl
import unittest
from unittest.mock import MagicMock, patch

from controlomics.artifacts import create_review_bundle, open_review_bundle, validated_ledger
from controlomics.evidence import Crossref, EuropePMC
from controlomics.models import MessagesProvider
from controlomics.privacy import ApprovalRequired, SafeField, SafeTransport, validate_outbound_url
from controlomics.project import parse_project_json
from controlomics.reports import render_report
from controlomics.server import handle_action
from tests.fixtures import payload


class EndpointPreparationTests(unittest.TestCase):
    def model_request(self, endpoint, transport=None):
        transport = transport or SafeTransport(frozenset({"model.example"}))
        return MessagesProvider(endpoint, "synthetic-fixture", transport).prepare(
            (SafeField("question", "Public synthetic scientific question", "SAFE"),))

    def restricted_urls(self):
        return (
            "https://model.example/v1/sk-syntheticprivatekey123456/complete",
            "https://model.example/v1/sk%2Dsyntheticprivatekey123456/complete",
            "https://model.example/v1/synthetic_person@example.invalid/complete",
            "https://model.example" + "/home/" + "synthetic_user/complete",
            "https://model.example/%68ome/synthetic_user/complete",
            "https://sk-syntheticprivatekey123456.example/complete",
        )

    def test_restricted_endpoint_components_reject_before_preview_or_network(self):
        with patch("socket.getaddrinfo") as lookup, patch("socket.create_connection") as connect, \
                patch("controlomics.privacy.SafeTransport.send") as send:
            for endpoint in self.restricted_urls():
                with self.subTest(endpoint=endpoint), self.assertRaises(ValueError) as caught:
                    handle_action("/api/model/preview", {"endpoint": endpoint, "model": "fixture",
                        "fields": {"question": "Public synthetic question"}, "public_confirmed": True})
                self.assertEqual(str(caught.exception), "outbound URL contains unsupported content")
                self.assertNotIn(endpoint, str(caught.exception))
            lookup.assert_not_called()
            connect.assert_not_called()
            send.assert_not_called()

    def test_nonpublic_literal_destinations_reject_without_dns_or_audit(self):
        hosts = ("127.0.0.1", "10.0.0.1", "169.254.169.254", "100.64.0.1", "224.0.0.1",
            "240.0.0.1", "[::1]", "[fe80::1]", "[fd00::1]", "[::ffff:127.0.0.1]")
        with patch("socket.getaddrinfo") as lookup, patch("socket.create_connection") as connect:
            for host in hosts:
                transport = SafeTransport(frozenset({host}))
                with self.subTest(host=host), self.assertRaisesRegex(ValueError, "not public"):
                    self.model_request("https://" + host + "/complete", transport)
                self.assertEqual(transport.audit, [])
            lookup.assert_not_called()
            connect.assert_not_called()

    def test_malformed_and_credential_urls_have_redacted_errors(self):
        for endpoint in (
            "http://model.example/complete", "https:///complete",
            "https://synthetic_user:synthetic_password" + "@model.example/complete",
            "https://model.example:synthetic_private_port/complete",
            "https://model.example/complete#synthetic_private_fragment",
            "https://[synthetic_private_host/complete",
        ):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError) as caught:
                self.model_request(endpoint)
            self.assertEqual(str(caught.exception), "outbound URL contains unsupported content")
            self.assertNotIn("synthetic_private", str(caught.exception))

    def test_ordinary_https_endpoints_and_public_literals_prepare_without_dns(self):
        with patch("socket.getaddrinfo") as lookup, patch("socket.create_connection") as connect:
            for endpoint in (
                "https://model.example/v1/chat/completions", "https://model.example:443/v1/complete",
                "https://api.institution.example/v1/complete", "https://93.184.216.34/v1/complete",
                "https://[2606:4700:4700::1111]/complete",
            ):
                with self.subTest(endpoint=endpoint):
                    self.assertEqual(self.model_request(endpoint).preview()["url"], endpoint)
            lookup.assert_not_called()
            connect.assert_not_called()

    def test_literature_public_queries_keep_the_exact_existing_binding(self):
        with patch("socket.getaddrinfo") as lookup:
            for cls in (EuropePMC, Crossref):
                request = cls(SafeTransport(frozenset({cls.host}))).prepare_search(
                    "Public synthetic contrast and robust analysis", 5)
                self.assertEqual(validate_outbound_url(request.url).hostname, cls.host)
                self.assertEqual(request.fields[0].value, "Public synthetic contrast and robust analysis")
                event = {**request.preview(), "request_sha256": request.approval_hash,
                    "sent_at": "2026-10-14T00:00:00Z", "status": "BLOCKED", "body_sha256": None,
                    "credential_supplied": False, "payload_transmission": "NOT_STARTED"}
                self.assertEqual(validated_ledger([event])[0]["url"], request.url)
            lookup.assert_not_called()

    def test_raw_url_whitespace_and_controls_reject_without_normalizing_approval(self):
        urls = (
            " https://model.example/complete", "\nhttps://model.example/complete",
            "https://model.exa\tmple/v1/complete", "https://model.example/v1/chat\n/completions",
            "https://model.example/complete\t", "https://model.example/complete ",
            "https://model.example/v1/private\rsegment/complete",
            "https://model.example/v1/public model/complete",
            "https://model.example/v1/\x00/complete", "https://model.example/v1/\x1f/complete",
            "https://model.example/v1/\x7f/complete",
        )
        with patch("socket.getaddrinfo") as lookup, patch("socket.create_connection") as connect:
            for endpoint in urls:
                with self.subTest(endpoint=endpoint), self.assertRaises(ValueError) as caught:
                    self.model_request(endpoint)
                self.assertEqual(str(caught.exception), "outbound URL contains unsupported content")
            lookup.assert_not_called()
            connect.assert_not_called()

    def test_encoded_ordinary_spaces_and_unicode_queries_remain_unchanged(self):
        endpoint = "https://model.example/v1/public%20model/complete"
        self.assertEqual(self.model_request(endpoint).preview()["url"], endpoint)
        for cls in (EuropePMC, Crossref):
            query = "Café statistical public comparison"
            request = cls(SafeTransport(frozenset({cls.host}))).prepare_search(query)
            self.assertIn("%C3%A9", request.url)
            self.assertEqual(request.fields[0].value, query)
            self.assertEqual(validate_outbound_url(request.url).geturl(), request.url)

    def test_prepared_url_size_matches_the_existing_typed_ledger_limit(self):
        prefix = "https://model.example/"
        endpoint = prefix + "z" * (12000 - len(prefix))
        request = self.model_request(endpoint)
        event = {**request.preview(), "body": None, "request_sha256": request.approval_hash,
            "sent_at": "2026-10-14T00:00:00Z", "status": "BLOCKED", "body_sha256": "a" * 64,
            "credential_supplied": False, "payload_transmission": "NOT_STARTED"}
        self.assertEqual(len(validated_ledger([event])[0]["url"]), 12000)
        with patch("socket.getaddrinfo") as lookup, patch("socket.create_connection") as connect:
            with self.assertRaisesRegex(ValueError, "unsupported content"):
                self.model_request(endpoint + "z")
            for cls in (EuropePMC, Crossref):
                with self.subTest(provider=cls.host), self.assertRaisesRegex(ValueError, "unsupported content"):
                    cls(SafeTransport(frozenset({cls.host}))).prepare_search("public method " * 855)
            lookup.assert_not_called()
            connect.assert_not_called()

    def test_approved_normal_model_request_keeps_a_usable_credential_free_ledger(self):
        endpoint = "https://model.example/v1/chat/completions"
        preview = handle_action("/api/model/preview", {"endpoint": endpoint, "model": "synthetic-fixture",
            "fields": {"question": "Public synthetic scientific question"}, "public_confirmed": True})
        transport = SafeTransport(frozenset({"model.example"}))
        request = self.model_request(endpoint, transport)
        self.assertEqual(preview["approve_hash"], request.approval_hash)
        connection = MagicMock()
        connection.getresponse.return_value.status = 200
        connection.getresponse.return_value.read.return_value = b"{}"
        context = MagicMock(spec=ssl.SSLContext)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        answer = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
        with patch("socket.getaddrinfo", return_value=answer), patch("socket.create_connection") as connect, \
                patch("ssl.create_default_context", return_value=context), \
                patch("http.client.HTTPSConnection", return_value=connection):
            self.assertEqual(transport.send(request, preview["approve_hash"], "synthetic_header_only_value"), {})
        connect.assert_called_once_with(("93.184.216.34", 443), timeout=20)
        self.assertEqual(context.wrap_socket.call_args.kwargs["server_hostname"], "model.example")
        self.assertNotIn("synthetic_header_only_value", json.dumps(transport.audit))
        self.assertNotIn("synthetic_header_only_value", json.dumps(preview))
        project = parse_project_json(json.dumps(payload()))
        ledger = validated_ledger(transport.audit)
        self.assertEqual(ledger[0]["status"], "COMPLETED")
        self.assertIn("model.example", render_report(project, ledger))
        self.assertEqual(open_review_bundle(create_review_bundle(project, ledger))[1], ledger)

    def test_prepared_hostname_resolving_to_private_address_stays_blocked_with_usable_ledger(self):
        transport = SafeTransport(frozenset({"model.example"}))
        request = self.model_request("https://model.example/complete", transport)
        answer = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]
        with patch("socket.getaddrinfo", return_value=answer), patch("socket.create_connection") as connect:
            with self.assertRaises(ValueError):
                transport.send(request, request.approval_hash)
            connect.assert_not_called()
        event = validated_ledger(transport.audit)[0]
        self.assertEqual(event["payload_transmission"], "NOT_STARTED")
        self.assertEqual(event["status"], "FAILED")
        self.assertNotIn("127.0.0.1", json.dumps(event))

    def test_exact_approval_is_still_required_before_any_resolution(self):
        transport = SafeTransport(frozenset({"model.example"}))
        request = self.model_request("https://model.example/complete", transport)
        with patch("socket.getaddrinfo") as lookup:
            with self.assertRaises(ApprovalRequired):
                transport.send(request, "wrong_hash")
            lookup.assert_not_called()
        self.assertEqual(transport.audit, [])


if __name__ == "__main__":
    unittest.main()
