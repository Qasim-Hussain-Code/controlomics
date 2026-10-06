import http.client
import json
import threading
import unittest
from unittest.mock import patch

from controlomics.server import LocalServer, handle_action
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
