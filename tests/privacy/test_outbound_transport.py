import json
import socket
import unittest
from unittest.mock import MagicMock, patch

from controlomics.evidence import EuropePMC
from controlomics.models import MessagesProvider, MethodBaseline
from controlomics.privacy import PreparedRequest, SafeField, SafeTransport


class TransportTests(unittest.TestCase):
    def test_private_dns_resolution_is_blocked_before_connecting(self):
        transport = SafeTransport(frozenset({EuropePMC.host}))
        request = EuropePMC(transport).prepare_search("public method")
        addresses = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]
        with patch("socket.getaddrinfo", return_value=addresses), patch("socket.create_connection") as connect:
            with self.assertRaises(ValueError):
                transport.send(request, request.approval_hash)
            connect.assert_not_called()
        self.assertEqual(transport.audit[0]["payload_transmission"], "NOT_STARTED")

    def test_model_payload_cannot_hide_additional_user_data(self):
        provider = MessagesProvider("https://model.example/v1/chat/completions", "test_model", SafeTransport(frozenset({"model.example"})))
        request = provider.prepare((SafeField("claim", "A public scientific claim", "SAFE"),))
        body = json.loads(request.body)
        body["messages"][1]["hidden_dataset"] = "Unapproved research"
        with self.assertRaises(ValueError):
            PreparedRequest("MODEL", "POST", request.url, request.fields, json.dumps(body).encode())

    def test_credentials_are_sent_only_as_headers_and_not_audited(self):
        transport = SafeTransport(frozenset({"model.example"}))
        provider = MessagesProvider("https://model.example/v1/chat/completions", "test_model", transport, "synthetic_credential_only")
        request = provider.prepare((SafeField("claim", "A public scientific claim", "SAFE"),))
        response = {"choices": [{"message": {"content": MethodBaseline().propose(None, None).model_dump_json()}}]}
        connection = MagicMock()
        connection.getresponse.return_value.status = 200
        connection.getresponse.return_value.read.return_value = json.dumps(response).encode()
        addresses = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
        with patch("socket.getaddrinfo", return_value=addresses), patch("socket.create_connection"), \
             patch("ssl.create_default_context"), patch("http.client.HTTPSConnection", return_value=connection):
            proposal = provider.complete(request, request.approval_hash)
        self.assertEqual(len(proposal.controls), 2)
        headers = connection.request.call_args.kwargs["headers"]
        self.assertEqual(headers["Authorization"], "Bearer synthetic_credential_only")
        self.assertNotIn("synthetic_credential_only", json.dumps(transport.audit))
        self.assertNotIn("synthetic_credential_only", json.dumps(request.preview()))
        self.assertTrue(transport.audit[0]["credential_supplied"])

    def test_unapproved_data_cannot_be_hidden_in_generation_parameters(self):
        provider = MessagesProvider("https://model.example/v1/chat/completions", "test_model", SafeTransport(frozenset({"model.example"})))
        request = provider.prepare((SafeField("claim", "A public scientific claim", "SAFE"),))
        for name in ("max_tokens", "temperature", "stream"):
            body = json.loads(request.body)
            body[name] = "Unapproved research text"
            with self.assertRaises(ValueError):
                PreparedRequest("MODEL", "POST", request.url, request.fields, json.dumps(body).encode())
