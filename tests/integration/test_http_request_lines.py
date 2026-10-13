import socket
import threading
import unittest
from http.server import BaseHTTPRequestHandler
from unittest.mock import patch

from controlomics.server import Handler, LocalServer, SECURITY_HEADERS


class RequestLineTests(unittest.TestCase):
    def setUp(self):
        self.server = LocalServer(0)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.assertFalse(self.thread.is_alive())

    def request(self, raw):
        with socket.create_connection(('127.0.0.1', self.server.server_port), timeout=5) as client:
            client.sendall(raw)
            received = bytearray()
            while chunk := client.recv(65536):
                received.extend(chunk)
        header, separator, body = bytes(received).partition(b'\r\n\r\n')
        self.assertEqual(separator, b'\r\n\r\n', header[:100])
        for name, value in SECURITY_HEADERS:
            self.assertEqual(header.count(f'\r\n{name}: {value}'.encode()), 1)
        return header, body

    def assert_status(self, header, status):
        self.assertTrue(header.startswith(f'HTTP/1.0 {status} '.encode()), header[:100])

    def test_rejected_request_lines_have_status_and_security_headers(self):
        for line, status in [(b'INVALID', 400), (b'GET / HTTP/garbage', 400), (b'GET / extra HTTP/1.0', 400),
                             (b'POST /', 400), (b'GET /', 400), (b'GET / HTTP/0.9', 400),
                             (b'POST / HTTP/0.9', 400),
                             (b'GET / HTTP/00000000000.9', 400), (b'GET / HTTP/0.00000000000', 400),
                             (b'GET / HTTP/\xb2.0', 400), (b'GET / HTTP/2.0', 505),
                             (b'GET / HTTP/02.00', 505), (b'GET /' + b'x' * 65536, 414)]:
            with self.subTest(line=line[:40]):
                header, body = self.request(line + b'\r\n\r\n')
                self.assert_status(header, status)
                self.assertTrue(body)

    def test_versionless_requests_cannot_access_session_or_assets_with_valid_host(self):
        with patch.object(Handler, 'do_GET') as get:
            for path in ('/api/session', '/', '/app.js', '/style.css'):
                with self.subTest(path=path):
                    raw = f'GET {path}\r\nHost: 127.0.0.1:{self.server.server_port}\r\n\r\n'.encode()
                    header, body = self.request(raw)
                    self.assert_status(header, 400)
                    self.assertTrue(body)
                    self.assertNotIn(self.server.session_token.encode(), body)
            get.assert_not_called()

    def test_legacy_versions_cannot_access_session_with_valid_host(self):
        with patch.object(Handler, 'do_GET') as get:
            for version in ('HTTP/0.0', 'HTTP/0.8', 'HTTP/0.9', 'HTTP/00.9', 'HTTP/0.09', 'HTTP/0.0009'):
                with self.subTest(version=version):
                    raw = f'GET /api/session {version}\r\nHost: 127.0.0.1:{self.server.server_port}\r\n\r\n'.encode()
                    header, body = self.request(raw)
                    self.assert_status(header, 400)
                    self.assertTrue(body)
                    self.assertNotIn(self.server.session_token.encode(), body)
            get.assert_not_called()

    def test_legacy_requests_do_not_wait_for_a_header_terminator(self):
        # A versionless HTTP/0.9 request has only a request line. Keep the
        # client write side open so EOF cannot accidentally finish parsing.
        lines = [b'GET /api/session', b'POST / HTTP/0.9']
        lines.extend(f'GET /api/session {version}'.encode() for version in
                     ('HTTP/0.0', 'HTTP/0.8', 'HTTP/0.9', 'HTTP/00.9', 'HTTP/0.09', 'HTTP/0.0009'))
        for line in lines:
            with self.subTest(line=line):
                header, body = self.request(line + b'\r\n')
                self.assert_status(header, 400)
                self.assertTrue(body)

    def test_legacy_syntax_is_rejected_before_stdlib_parsing(self):
        with patch.object(BaseHTTPRequestHandler, 'parse_request', side_effect=AssertionError('Legacy parser reached')) as parse:
            for line in (b'GET /api/session', b'GET /api/session HTTP/0.9'):
                with self.subTest(line=line):
                    header, body = self.request(line + b'\r\n')
                    self.assert_status(header, 400)
                    self.assertTrue(body)
            parse.assert_not_called()

    def test_http_1_requests_still_require_host_and_serve_session(self):
        for version in ('HTTP/1.0', 'HTTP/1.1'):
            for valid_host in (False, True):
                with self.subTest(version=version, valid_host=valid_host):
                    raw = f'GET /api/session {version}\r\n'.encode()
                    if valid_host:
                        raw += f'Host: 127.0.0.1:{self.server.server_port}\r\n'.encode()
                    header, body = self.request(raw + b'\r\n')
                    self.assert_status(header, 200 if valid_host else 403)
                    self.assertEqual(self.server.session_token.encode() in body, valid_host)
