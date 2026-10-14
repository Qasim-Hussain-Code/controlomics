"""Provider approval and verified TLS contexts, with all network operations mocked."""

import json
import socket
import ssl
import unittest
import warnings
from unittest.mock import MagicMock, patch

from controlomics.evidence import EuropePMC
from controlomics.privacy import ApprovalRequired, SafeTransport, TransportError


class TLSBoundaryTests(unittest.TestCase):
    def request(self, allowed=True):
        transport = SafeTransport(frozenset({EuropePMC.host}) if allowed else frozenset())
        return transport, EuropePMC(transport).prepare_search("public method")

    def test_approval_and_allowlist_precede_dns_context_or_connection(self):
        for allowed, approved, exception in (
            (True, False, ApprovalRequired), (False, True, TransportError),
        ):
            transport, request = self.request(allowed)
            with self.subTest(allowed=allowed, approved=approved), \
                    patch("socket.getaddrinfo") as lookup, \
                    patch("socket.create_connection") as connect, \
                    patch("ssl.create_default_context") as context, \
                    patch("http.client.HTTPSConnection") as https:
                with self.assertRaises(exception):
                    transport.send(request, request.approval_hash if approved else None)
                lookup.assert_not_called()
                connect.assert_not_called()
                context.assert_not_called()
                https.assert_not_called()
            self.assertEqual(transport.audit, [])

    def test_authorized_tls_floor_preserves_verification_and_stricter_defaults(self):
        for minimum in (ssl.TLSVersion.TLSv1, ssl.TLSVersion.TLSv1_2, ssl.TLSVersion.TLSv1_3):
            with self.subTest(original_minimum=minimum):
                context = ssl.create_default_context()
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", DeprecationWarning)
                    context.minimum_version = minimum
                options, flags = context.options, context.verify_flags
                transport, request = self.request()
                connection, raw_socket, tls_socket = MagicMock(), MagicMock(), MagicMock()
                connection.getresponse.return_value.status = 200
                connection.getresponse.return_value.read.return_value = b'{}'
                addresses = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]

                def wrap(actual_context, actual_socket, *, server_hostname):
                    self.assertIs(actual_context, context)
                    self.assertIs(actual_socket, raw_socket)
                    self.assertEqual(server_hostname, EuropePMC.host)
                    self.assertEqual(actual_context.minimum_version, max(minimum, ssl.TLSVersion.TLSv1_2))
                    self.assertTrue(actual_context.check_hostname)
                    self.assertEqual(actual_context.verify_mode, ssl.CERT_REQUIRED)
                    self.assertEqual(actual_context.options, options)
                    self.assertEqual(actual_context.verify_flags, flags)
                    return tls_socket

                with patch("socket.getaddrinfo", return_value=addresses), \
                        patch("socket.create_connection", return_value=raw_socket) as connect, \
                        patch("ssl.create_default_context", return_value=context) as factory, \
                        patch.object(ssl.SSLContext, "wrap_socket", autospec=True, side_effect=wrap) as wrapped, \
                        patch("http.client.HTTPSConnection", return_value=connection) as https:
                    self.assertEqual(transport.send(request, request.approval_hash), {})
                    factory.assert_called_once_with()
                    https.assert_called_once_with(EuropePMC.host, timeout=20, context=context)
                    connect.assert_called_once_with(("93.184.216.34", 443), timeout=20)
                    wrapped.assert_called_once()
                self.assertIs(connection.sock, tls_socket)
                connection.request.assert_called_once()
                connection.close.assert_called_once()
                self.assertEqual(transport.audit[0]["status"], "COMPLETED")

    def test_tls_failure_never_sends_payload_or_records_private_error_text(self):
        transport, request = self.request()
        connection = MagicMock()
        context = ssl.create_default_context()
        addresses = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
        sentinel = "synthetic_private_tls_failure"
        with patch("socket.getaddrinfo", return_value=addresses), \
                patch("socket.create_connection"), \
                patch("ssl.create_default_context", return_value=context), \
                patch.object(ssl.SSLContext, "wrap_socket", side_effect=ssl.SSLError(sentinel)), \
                patch("http.client.HTTPSConnection", return_value=connection):
            with self.assertRaises(TransportError) as caught:
                transport.send(request, request.approval_hash)
        connection.request.assert_not_called()
        connection.close.assert_called_once()
        self.assertEqual(transport.audit[0]["status"], "FAILED")
        self.assertEqual(transport.audit[0]["payload_transmission"], "NOT_STARTED")
        self.assertNotIn(sentinel, str(caught.exception))
        self.assertNotIn(sentinel, json.dumps(transport.audit))


if __name__ == "__main__":
    unittest.main()
