import http.client
import json
import os
import socket
import subprocess
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from controlomics import execution
from controlomics.execution import ExecutionConfig, LocalExecutionError, build_package, execute_local
from controlomics.project import parse_project_json
from controlomics.server import LocalServer, SECURITY_HEADERS
from controlomics.workflow import propose_and_review_new
from tests.fixtures import ROOT, payload


def reference_project():
    value = payload()
    value["candidates"] = []
    return propose_and_review_new(parse_project_json(json.dumps(value)))


def large_input():
    return ("unit,label,value\n" + "".join(f"unit.{i},{i % 2},{i % 7}\n" for i in range(2000))).encode()


class LocalBudgetAuditTests(unittest.TestCase):
    def test_oversized_local_run_is_rejected_before_package_or_process(self):
        project = reference_project()
        config = ExecutionConfig(kind="PERMUTATION", draws=10000, assumptions=("Synthetic units.",))
        with patch.object(execution, "TemporaryDirectory", side_effect=AssertionError("Unexpected staging")), \
                patch.object(execution.subprocess, "run", side_effect=AssertionError("Unexpected process")):
            with self.assertRaises(LocalExecutionError) as raised:
                execute_local(project, project.controls[0].control_id, config, large_input())
        self.assertEqual(raised.exception.code, "LOCAL_RESAMPLING_BUDGET")
        self.assertFalse(project.execution_plans)
        self.assertFalse(project.results)

    def test_dispatch_preserves_larger_configuration_without_raw_input(self):
        project = reference_project()
        config = ExecutionConfig(kind="PERMUTATION", draws=10000, assumptions=("Synthetic units.",))
        with TemporaryDirectory() as temporary:
            target = Path(temporary) / "package"
            updated = build_package(project, project.controls[0].control_id, config, target)
            self.assertEqual(json.loads((target / "config.json").read_bytes())["draws"], 10000)
            self.assertFalse((target / "input.csv").exists())
            self.assertEqual(updated.execution_plans[-1].pathway, "DISPATCHED")

    def test_timeout_has_public_reason_and_removes_staging(self):
        project = reference_project()
        config = ExecutionConfig(kind="REFERENCE", expected_difference=2.0, assumptions=("Synthetic units.",))
        directories = []
        real_temporary = TemporaryDirectory

        def owned_directory(*args, **kwargs):
            directory = real_temporary(*args, **kwargs)
            directories.append(Path(directory.name))
            return directory

        with patch.object(execution, "TemporaryDirectory", side_effect=owned_directory), \
                patch.object(execution.subprocess, "run", side_effect=subprocess.TimeoutExpired(["private_sentinel"], 35)):
            with self.assertRaises(LocalExecutionError) as raised:
                execute_local(project, project.controls[0].control_id, config,
                              (ROOT / "examples/positive_reference.csv").read_bytes())
        self.assertEqual(raised.exception.code, "LOCAL_EXECUTION_TIMEOUT")
        self.assertNotIn("private_sentinel", str(raised.exception))
        self.assertTrue(directories)
        self.assertTrue(all(not path.exists() for path in directories))
        self.assertFalse(project.results)


class ServerAuditTests(unittest.TestCase):
    def setUp(self):
        self.server = LocalServer(0)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.assertFalse(self.thread.is_alive())

    def request(self, method, target="/", value=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        try:
            headers = {"Origin": f"http://127.0.0.1:{self.server.server_port}",
                       "X-Controlomics-Token": self.server.session_token,
                       "Content-Type": "application/json"}
            connection.request(method, target, body=json.dumps(value) if value is not None else None, headers=headers)
            response = connection.getresponse()
            return response.status, response.getheaders(), response.read()
        finally:
            connection.close()

    def assert_security(self, headers):
        for name, value in SECURITY_HEADERS:
            self.assertEqual([v for n, v in headers if n.lower() == name.lower()], [value])

    def test_normal_not_found_and_unsupported_responses_have_security_headers(self):
        for method, target, expected in (("GET", "/", 200), ("GET", "/missing", 404), ("PUT", "/", 501)):
            with self.subTest(method=method, target=target):
                status, headers, _ = self.request(method, target)
                self.assertEqual(status, expected)
                self.assert_security(headers)

    def test_overload_response_also_has_security_headers(self):
        for _ in range(16):
            self.server.connection_slots.acquire()
        try:
            status, headers, _ = self.request("GET")
            self.assertEqual(status, 503)
            self.assert_security(headers)
        finally:
            for _ in range(16):
                self.server.connection_slots.release()
        self.assertEqual(self.request("GET")[0], 200)

    def test_occupied_port_cannot_be_bound_by_a_second_server(self):
        with self.assertRaises(OSError):
            second = LocalServer(self.server.server_port)
            second.server_close()
        if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.assertEqual(self.server.socket.getsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE), 1)

    def test_execution_budget_error_is_specific_and_redacted(self):
        project = reference_project()
        config = ExecutionConfig(kind="PERMUTATION", draws=10000, assumptions=("Synthetic units.",))
        status, headers, body = self.request("POST", "/api/execute", {
            "project": project.model_dump(mode="json"), "control_id": project.controls[0].control_id,
            "config": config.model_dump(mode="json"), "csv": large_input().decode()})
        self.assertEqual(status, 400)
        self.assert_security(headers)
        self.assertEqual(json.loads(body)["code"], "LOCAL_RESAMPLING_BUDGET")
        self.assertNotIn(b"unit.1999", body)
