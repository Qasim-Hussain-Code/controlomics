import http.client
import json
import socket
import threading
import unittest
from unittest.mock import Mock, patch

from controlomics.server import Handler, LocalServer, handle_action
from tests.fixtures import payload


class ServerTests(unittest.TestCase):
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

    def request(self, path, data=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        connection.request("POST" if data is not None else "GET", path,
            body=json.dumps(data) if data is not None else None, headers=headers or {})
        response = connection.getresponse()
        status, content, response_headers = response.status, response.read(), dict(response.getheaders())
        connection.close()
        return status, content, response_headers

    def headers(self):
        return {"Origin": f"http://127.0.0.1:{self.server.server_port}", "X-Controlomics-Token": self.server.session_token,
                "Content-Type": "application/json"}

    def test_assets_and_session_are_local_and_no_store(self):
        for path in ("/", "/app.js", "/style.css", "/api/session"):
            status, content, headers = self.request(path)
            self.assertEqual(status, 200)
            self.assertEqual(headers["Cache-Control"], "no-store")
            self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(self.request("/../pyproject.toml")[0], 404)

    def test_host_origin_and_token_are_required(self):
        self.assertEqual(self.request("/api/session", headers={"Host": "attacker.example"})[0], 403)
        self.assertEqual(self.request("/api/analyze", {"project": payload()})[0], 403)
        headers = self.headers()
        headers["Origin"] = "https://attacker.example"
        self.assertEqual(self.request("/api/analyze", {"project": payload()}, headers)[0], 403)

    def test_nonascii_token_rejected_and_server_remains_usable(self):
        headers = self.headers()
        headers['X-Controlomics-Token'] = '\u00e9'
        self.assertEqual(self.request('/api/inspect-input', {'csv': 'private_sentinel', 'adapter': 'INDEPENDENT_REFERENCE'}, headers)[0], 403)
        self.assertEqual(self.request('/api/session')[0], 200)

    def test_unauthorized_request_rejected_before_body_read(self):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=2)
        connection.putrequest('POST', '/api/analyze')
        connection.putheader('Content-Length', '1000')
        connection.putheader('Content-Type', 'application/json')
        connection.endheaders()
        response = connection.getresponse()
        self.assertEqual(response.status, 403)
        response.read()
        connection.close()

    def test_local_analyze_and_report_end_to_end(self):
        status, content, headers = self.request("/api/analyze", {"project": payload()}, self.headers())
        self.assertEqual(status, 200)
        project = json.loads(content)["project"]
        self.assertEqual(project["audits"][0]["assessment"], "INSUFFICIENT_EVIDENCE")
        status, content, headers = self.request("/api/report", {"project": project}, self.headers())
        self.assertEqual(status, 200)
        self.assertIn(b"Controlomics scientific audit", content)
        self.assertIn("attachment", headers["Content-Disposition"])

    def test_privacy_failure_is_redacted(self):
        headers = self.headers()
        status, content, _ = self.request("/api/literature/preview", {
            "provider": "europepmc", "query": "patient_id: private_sentinel", "public_confirmed": True}, headers)
        self.assertEqual(status, 400)
        self.assertNotIn(b"private_sentinel", content)

    def test_local_execution_and_package_are_explicit_actions(self):
        raw = payload()
        raw["candidates"] = []
        data = handle_action("/api/analyze", {"project": raw})
        project = data["project"]
        from tests.fixtures import ROOT
        settings = {"project": project, "control_id": project["controls"][0]["control_id"],
            "config": {"kind": "REFERENCE", "expected_difference": 2.0, "assumptions": ["Synthetic fixture."]}}
        package = handle_action("/api/package", settings)
        self.assertTrue(package["package_base64"])
        self.assertEqual(len(package["project"]["execution_plans"]), 1)
        settings["csv"] = (ROOT / "examples" / "positive_reference.csv").read_text()
        executed = handle_action("/api/execute", settings)["project"]
        self.assertEqual(executed["execution_plans"][0]["pathway"], "LOCAL")
        result = executed["results"][0]
        self.assertEqual(result["outcome"], "PASS")

    def test_invalid_project_is_rejected_before_external_send(self):
        with patch("controlomics.server.EuropePMC.search") as search:
            with self.assertRaises(ValueError):
                handle_action("/api/literature/retrieve", {"project": {}, "provider": "europepmc",
                    "query": "public method", "public_confirmed": True, "approve_hash": "invalid"})
            search.assert_not_called()

    def test_rejected_delayed_body_is_discarded_and_server_remains_usable(self):
        original_reply = Handler.reply
        original_recv = socket.socket.recv
        original_shutdown = self.server.shutdown_request
        for token in (b'', b'X-Controlomics-Token: \xff\r\n'):
            with self.subTest(nonascii_token=bool(token)):
                replied, body_sent, closed = threading.Event(), threading.Event(), threading.Event()
                discarded = []
                peer = None
                body = b'x' * 8192

                def reply(handler, status, *args, **kwargs):
                    original_reply(handler, status, *args, **kwargs)
                    if handler.server is self.server and handler.client_address == peer and status == 403:
                        replied.set()

                def shutdown(request):
                    if request.getpeername() != peer:
                        original_shutdown(request)
                        return
                    try:
                        self.assertTrue(body_sent.wait(2), 'Delayed fixture body was not sent')
                    finally:
                        try:
                            original_shutdown(request)
                        finally:
                            closed.set()

                def recv(request, *args, **kwargs):
                    owned = request.getsockname() == self.server.server_address
                    received = original_recv(request, *args, **kwargs)
                    if owned:
                        discarded.append(len(received))
                    return received

                with patch.object(Handler, 'reply', reply), patch.object(self.server, 'shutdown_request', shutdown), \
                     patch.object(socket.socket, 'recv', recv), patch('controlomics.server.handle_action') as action:
                    try:
                        with socket.create_connection(self.server.server_address, timeout=5) as client:
                            peer = client.getsockname()
                            client.sendall(f'POST /api/analyze HTTP/1.1\r\nHost: 127.0.0.1:{self.server.server_port}\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\n'.encode() + token + b'\r\n')
                            self.assertTrue(replied.wait(2), 'Authorization reply waited for a request body')
                            client.sendall(body)
                            body_sent.set()
                            received = bytearray()
                            while chunk := client.recv(65536):
                                received.extend(chunk)
                        self.assertTrue(closed.wait(2), 'Rejected connection did not finish shutdown')
                        header, separator, response_body = bytes(received).partition(b'\r\n\r\n')
                        self.assertTrue(header.startswith(b'HTTP/1.0 403 '), header[:100])
                        self.assertEqual(separator, b'\r\n\r\n')
                        self.assertEqual(json.loads(response_body), {'error': 'Local request authorization failed.'})
                        self.assertEqual(sum(discarded), len(body))
                        action.assert_not_called()
                    finally:
                        body_sent.set()
                self.assertEqual(self.request('/api/session')[0], 200)


    def test_ambiguous_headers_are_rejected_before_body_read(self):
        for header, value, expected in (("Host", f"127.0.0.1:{self.server.server_port}", 403),
                ("Origin", self.headers()["Origin"], 403), ("X-Controlomics-Token", self.server.session_token, 403),
                ("Content-Length", "1000", 400), ("Content-Type", "application/json", 400), ("Transfer-Encoding", "chunked", 400)):
            with self.subTest(header=header):
                connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
                try:
                    connection.putrequest("POST", "/api/analyze")
                    for name, content in self.headers().items():
                        connection.putheader(name, content)
                    connection.putheader("Content-Length", "1000")
                    connection.putheader(header, value)
                    connection.endheaders()
                    response = connection.getresponse()
                    self.assertEqual(response.status, expected)
                    response.read()
                finally:
                    connection.close()

    def test_nonobject_actions_and_unexpected_errors_are_redacted(self):
        with patch("controlomics.server.handle_action") as action:
            for data in ([], "private_sentinel", 4):
                status, content, _ = self.request("/api/analyze", data, self.headers())
                self.assertEqual(status, 400)
                self.assertNotIn(b"private_sentinel", content)
            action.assert_not_called()
        with patch("controlomics.server.handle_action", side_effect=RuntimeError("private_sentinel")):
            status, content, _ = self.request("/api/analyze", {}, self.headers())
            self.assertEqual(status, 500)
            self.assertNotIn(b"private_sentinel", content)
        self.assertEqual(self.request("/api/session")[0], 200)

    def test_worker_limit_rejects_excess_connections_and_recovers(self):
        ready = threading.Event()
        lock = threading.Lock()
        count = 0
        original_setup = Handler.setup

        def observed_setup(handler):
            nonlocal count
            original_setup(handler)
            with lock:
                count += 1
                if count == 2:
                    ready.set()

        with patch("controlomics.server.MAX_CONNECTIONS", 2), patch.object(Handler, "setup", observed_setup):
            server = LocalServer(0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            held = []
            try:
                for _ in range(2):
                    client = socket.create_connection(("127.0.0.1", server.server_port), timeout=2)
                    held.append(client)
                    client.sendall(b"GET /api/session HTTP/1.1\r\n")
                self.assertTrue(ready.wait(2), "Two workers did not start")
                connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=2)
                try:
                    connection.request("GET", "/api/session")
                    response = connection.getresponse()
                    self.assertEqual(response.status, 503)
                    self.assertIn(b"Retry", response.read())
                finally:
                    connection.close()
                for client in held:
                    client.close()
                # Acquiring every slot waits for the two workers to finish,
                # avoiding a timing-dependent retry or inspection of internals.
                for _ in range(2):
                    self.assertTrue(server.connection_slots.acquire(timeout=2))
                for _ in range(2):
                    server.connection_slots.release()
                connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=2)
                try:
                    connection.request("GET", "/api/session")
                    response = connection.getresponse()
                    self.assertEqual(response.status, 200)
                    response.read()
                finally:
                    connection.close()
            finally:
                for client in held:
                    client.close()
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)

    def test_idle_header_connection_times_out_and_releases_worker(self):
        with patch("controlomics.server.CONNECTION_TIMEOUT", 0.1):
            server = LocalServer(0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with socket.create_connection(("127.0.0.1", server.server_port), timeout=2) as client:
                    client.sendall(b"GET /api/session HTTP/1.1\r\n")
                    self.assertEqual(client.recv(1024), b"")
                connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=2)
                try:
                    connection.request("GET", "/api/session")
                    response = connection.getresponse()
                    self.assertEqual(response.status, 200)
                    response.read()
                finally:
                    connection.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)


class RequestShutdownTests(unittest.TestCase):
    def test_worker_slot_is_released_if_connection_shutdown_fails(self):
        server = object.__new__(LocalServer)
        server.connection_slots = threading.BoundedSemaphore(1)
        self.assertTrue(server.connection_slots.acquire(blocking=False))
        server.finish_request = Mock()
        server.shutdown_request = Mock(side_effect=RuntimeError('Synthetic close failure'))
        with self.assertRaises(RuntimeError):
            server.process_request_thread(Mock(), ('127.0.0.1', 1))
        self.assertTrue(server.connection_slots.acquire(blocking=False))
        server.connection_slots.release()

    def test_shutdown_discards_at_most_64_kib_and_closes(self):
        server, request = Mock(), Mock()
        unread = bytearray(b'x' * (64 * 1024 + 1))

        def recv(size):
            received = bytes(unread[:size])
            del unread[:size]
            return received

        request.recv.side_effect = recv
        with patch('controlomics.server.time.monotonic', return_value=10):
            LocalServer.shutdown_request(server, request)
        self.assertEqual(len(unread), 1)
        self.assertTrue(all(0 < call.args[0] <= 4096 for call in request.recv.call_args_list))
        self.assertTrue(all(0 < call.args[0] <= 0.05 + 1e-12 for call in request.settimeout.call_args_list))
        request.shutdown.assert_called_once_with(socket.SHUT_WR)
        server.close_request.assert_called_once_with(request)

    def test_shutdown_stops_at_the_existing_50_ms_deadline(self):
        server, request = Mock(), Mock()
        request.recv.return_value = b'x'
        with patch('controlomics.server.time.monotonic', side_effect=(10, 10.02, 10.06)):
            LocalServer.shutdown_request(server, request)
        request.recv.assert_called_once_with(4096)
        self.assertAlmostEqual(request.settimeout.call_args.args[0], 0.03)
        server.close_request.assert_called_once_with(request)

    def test_shutdown_stops_at_eof_without_waiting_for_the_deadline(self):
        server, request = Mock(), Mock()
        request.recv.return_value = b''
        LocalServer.shutdown_request(server, request)
        request.recv.assert_called_once_with(4096)
        server.close_request.assert_called_once_with(request)

    def test_shutdown_closes_after_socket_errors(self):
        for operation in ('shutdown', 'settimeout', 'recv'):
            with self.subTest(operation=operation):
                server, request = Mock(), Mock()
                getattr(request, operation).side_effect = TimeoutError('Synthetic transport failure')
                LocalServer.shutdown_request(server, request)
                server.close_request.assert_called_once_with(request)

    def test_shutdown_closes_after_an_unexpected_error_and_preserves_it(self):
        server, request = Mock(), Mock()
        request.recv.side_effect = RuntimeError('Synthetic unexpected failure')
        with self.assertRaises(RuntimeError):
            LocalServer.shutdown_request(server, request)
        server.close_request.assert_called_once_with(request)
