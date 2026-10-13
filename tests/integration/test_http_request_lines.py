import socket
import threading
import unittest

from controlomics.server import LocalServer, SECURITY_HEADERS


class RequestLineTests(unittest.TestCase):
    def test_rejected_request_lines_have_status_and_security_headers(self):
        with LocalServer(0) as server:
            thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
            thread.start()
            try:
                for line, status in [(b'INVALID', 400), (b'GET / HTTP/garbage', 400), (b'GET / extra HTTP/1.0', 400),
                                     (b'POST /', 400), (b'GET /', 403), (b'GET / HTTP/0.9', 400),
                                     (b'POST / HTTP/0.9', 400),
                                     (b'GET / HTTP/2.0', 505), (b'GET /' + b'x' * 65536, 414)]:
                    with self.subTest(line=line[:40]):
                        with socket.create_connection(('127.0.0.1', server.server_port), timeout=5) as client:
                            client.sendall(line + b'\r\n\r\n')
                            received = bytearray()
                            while chunk := client.recv(65536):
                                received.extend(chunk)
                        header, _, body = bytes(received).partition(b'\r\n\r\n')
                        self.assertTrue(header.startswith(f'HTTP/1.0 {status} '.encode()), header[:100])
                        for name, value in SECURITY_HEADERS:
                            self.assertEqual(header.count(f'\r\n{name}: {value}'.encode()), 1)
                        self.assertTrue(body)
            finally:
                server.shutdown()
                thread.join(timeout=2)
                self.assertFalse(thread.is_alive())
