import unittest
from unittest.mock import patch

from controlomics.evidence import Crossref, EuropePMC, consolidate, resolved_match
from controlomics.privacy import ApprovalRequired, PreparedRequest, SafeField, SafeTransport
from controlomics.schemas import EvidenceIdentifier


class FakeTransport:
    def __init__(self, response):
        self.response = response

    def send(self, prepared, approval_hash):
        if approval_hash != prepared.approval_hash:
            raise ApprovalRequired()
        return self.response


class EvidenceTests(unittest.TestCase):
    def test_synthetic_provider_responses_parse_and_consolidate(self):
        epmc = EuropePMC(FakeTransport({"resultList": {"result": [{
            "source": "MED", "id": "123", "pmcid": "PMC456", "doi": "10.0000/TEST_ONLY",
            "title": "Synthetic adapter fixture", "pubYear": "2020",
        }]}}))
        crossref = Crossref(FakeTransport({"message": {"DOI": "10.0000/test_only",
            "title": ["Synthetic adapter fixture"], "issued": {"date-parts": [[2020]]}}}))
        request = epmc.prepare_search("synthetic fixture")
        records = epmc.search(request, request.approval_hash)
        requested = EvidenceIdentifier(namespace="PMID", value="123", authority="PubMed")
        self.assertEqual(resolved_match(records, requested).existence_status, "VERIFIED")
        request = crossref.prepare_resolve(records[0].identifiers[-1])
        merged = consolidate(records + crossref.search(request, request.approval_hash))
        self.assertEqual(len(merged), 1)
        self.assertEqual(len(merged[0].identifiers), 3)
        self.assertIsNone(merged[0].biological_context.organism)

    def test_exact_approval_precedes_network_access(self):
        provider = EuropePMC(SafeTransport(frozenset({EuropePMC.host})))
        prepared = provider.prepare_search("public method")
        with patch("socket.getaddrinfo", side_effect=AssertionError("Must not connect")):
            with self.assertRaises(ApprovalRequired):
                provider.search(prepared, "wrong")

    def test_private_fields_and_destinations_are_blocked(self):
        for text in ("C:\\private\\research.csv", "patient_id: private001", "ACGT" * 30, "api_key=example_secret"):
            with self.assertRaises(ValueError):
                SafeField("public_query", text, "SAFE")
        with self.assertRaises(ValueError):
            SafeField("dataset", "data", "SAFE")
        with self.assertRaises(ValueError):
            SafeField("claim", "private research", "RESTRICTED")
        with self.assertRaises(ValueError):
            PreparedRequest("LITERATURE", "GET", "https://unknown.example/", (SafeField("public_query", "method", "SAFE"),))

    def test_unapproved_fields_cannot_be_hidden_in_url(self):
        provider = EuropePMC(SafeTransport(frozenset({EuropePMC.host})))
        request = provider.prepare_search("safe public query")
        with self.assertRaises(ValueError):
            PreparedRequest("LITERATURE", "GET", request.url.replace("safe+public+query", "private+data"), request.fields)

    def test_missing_identity_cannot_resolve(self):
        with self.assertRaises(ValueError):
            resolved_match((), EvidenceIdentifier(namespace="PMID", value="123", authority="PubMed"))

    def test_malformed_provider_structures_fail_with_redacted_errors(self):
        for cls in (EuropePMC, Crossref):
            for response in (["private_sentinel"], {"resultList": "private_sentinel", "message": "private_sentinel"}):
                provider = cls(FakeTransport(response))
                request = provider.prepare_search("public method")
                with self.assertRaises(ValueError) as raised:
                    provider.search(request, request.approval_hash)
                self.assertNotIn("private_sentinel", str(raised.exception))
