import http.client
import json
import socket
import threading
import unittest
from unittest.mock import patch

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
