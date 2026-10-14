"""Qualify pinned Gunicorn on Linux using owned loopback sockets and synthetic inputs."""

from __future__ import annotations

import argparse
import errno
import hashlib
import http.client
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from controlomics.hosted_worker import READ_DEADLINE_SECONDS, READ_INACTIVITY_SECONDS  # noqa: E402
from controlomics.server import SECURITY_HEADERS  # noqa: E402

ORIGIN = "https://controlomics.example"
MARKER = "synthetic_private_transport_marker"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "linux":
        raise SystemExit("This transport qualification requires Linux and the pinned optional cloud dependencies.")
    import gunicorn

    output = args.output.resolve()
    if output.exists():
        raise SystemExit("Choose an absent qualification output file.")
    output.parent.mkdir(parents=True, exist_ok=True)
    log_path = output.with_suffix(".server.log")
    if log_path.exists():
        raise SystemExit("Choose an absent qualification log file.")
    record = {"scope": "Owned loopback HTTP with trusted TLS-proxy headers; not live Render/TLS verification",
              "python": sys.version.split()[0], "gunicorn": gunicorn.__version__,
              "read_inactivity_seconds": READ_INACTIVITY_SECONDS, "read_deadline_seconds": READ_DEADLINE_SECONDS,
              "checks": [], "source_hashes": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in
                  ("src/controlomics/hosted.py", "src/controlomics/hosted_worker.py", "gunicorn.conf.py", "scripts/check_hosted_transport.py")}}
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(32)
    port = listener.getsockname()[1]
    process = None
    failure = None
    with TemporaryDirectory(prefix="hosted_transport_", dir=output.parent) as temporary, log_path.open("x", encoding="utf-8") as logs:
        scratch = Path(temporary)
        (scratch / "owned_hosted_fixture.py").write_text(
            "from controlomics.hosted import create_app\n"
            "from controlomics.hosted_worker import BoundedSocket\n"
            "app = create_app()\n"
            "def application(environ, start_response):\n"
            "    if not isinstance(environ.get('gunicorn.socket'), BoundedSocket):\n"
            "        raise RuntimeError('Unbounded hosted transport fixture')\n"
            "    return app(environ, start_response)\n", encoding="utf-8")
        env = {**os.environ, "PUBLIC_ORIGIN": ORIGIN, "CONTROLOMICS_SESSION_SECRET": "Synthetic transport qualification secret, never a deployment key.",
               "CONTROLOMICS_TRUST_PROXY": "render", "TMPDIR": str(scratch),
               "PYTHONPATH": os.pathsep.join((str(scratch), str(ROOT / "src")))}
        try:
            process = subprocess.Popen([sys.executable, "-m", "gunicorn", "--config", str(ROOT / "gunicorn.conf.py"),
                "--bind", f"fd://{listener.fileno()}", "owned_hosted_fixture:application"], cwd=ROOT, env=env,
                pass_fds=(listener.fileno(),), stdout=logs, stderr=logs, start_new_session=True)

            def request(path, data=None, *, cookie=None, token=None, extra=None):
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
                headers = {"Host": "controlomics.example", "X-Forwarded-Proto": "https"}
                if data is not None:
                    headers.update({"Origin": ORIGIN, "Content-Type": "application/json", "X-Controlomics-Token": token or ""})
                if cookie:
                    headers["Cookie"] = cookie
                for name, value in (extra or {}).items():
                    if value is None:
                        headers.pop(name, None)
                    else:
                        headers[name] = value
                try:
                    connection.request("POST" if data is not None else "GET", path, json.dumps(data).encode() if data is not None else None, headers)
                    response = connection.getresponse()
                    status, body, result_headers = response.status, response.read(), dict(response.getheaders())
                    for name, value in SECURITY_HEADERS:
                        if result_headers.get(name) != value:
                            raise AssertionError("Missing hosted security header")
                    value = json.loads(body) if result_headers.get("Content-Type") == "application/json" else body
                    return status, value, result_headers
                finally:
                    connection.close()

            startup = time.monotonic() + 20
            while True:
                if process.poll() is not None:
                    raise AssertionError("Owned Gunicorn did not remain running")
                try:
                    if request("/healthz")[0] == 200:
                        break
                except (OSError, http.client.HTTPException):
                    pass
                if time.monotonic() >= startup:
                    raise AssertionError("Owned Gunicorn did not become ready")
                time.sleep(0.1)
            record["checks"].append({"name": "worker_and_wsgi_socket_guard", "status": "PASS"})
            for asset in ("/", "/app.js", "/style.css"):
                status, original, original_headers = request(asset)
                assert status == 200 and "Set-Cookie" not in original_headers
                status, shared, shared_headers = request(asset + "?fbclid=synthetic_click_id&utm_source=facebook", extra={
                    "Origin": "https://www.facebook.com", "Sec-Fetch-Site": "cross-site"})
                assert status == 200 and shared == original and "Set-Cookie" not in shared_headers
                assert shared_headers["Content-Type"] == original_headers["Content-Type"]
                assert shared_headers["Content-Length"] == original_headers["Content-Length"]
            for guarded in ("/api/session", "/healthz", "/not-an-asset"):
                status, _, guarded_headers = request(guarded + "?fbclid=synthetic_click_id")
                assert status == 403 and "Set-Cookie" not in guarded_headers
            record["checks"].append({"name": "shared_link_queries_only_serve_unchanged_public_assets", "status": "PASS"})
            health_status, health, health_headers = request("/healthz", extra={"X-Forwarded-Proto": None})
            assert health_status == 200 and health == {"status": "ok", "mode": "HOSTED_TEMPORARY"}
            assert "Set-Cookie" not in health_headers
            assert request("/api/session", extra={"X-Forwarded-Proto": None})[0] == 403
            record["checks"].append({"name": "internal_readiness_without_https_header_never_opens_sessions", "status": "PASS"})
            status, session, headers = request("/api/session")
            assert status == 200 and session["consent_required"]
            cookie = headers["Set-Cookie"].split(";", 1)[0]
            assert request("/api/interpret", {"private": MARKER}, cookie=cookie, token=session["token"])[0] == 428
            status, session, headers = request("/api/hosting-consent", {"allowed": True, "policy_revision": session["policy_revision"]}, cookie=cookie, token=session["token"])
            assert status == 200 and not session["consent_required"]
            cookie, token = headers["Set-Cookie"].split(";", 1)[0], session["token"]
            record["checks"].append({"name": "cookie_consent_and_no_science_before_consent", "status": "PASS"})
            # Use the repository's maintained synthetic project, not external data.
            project = json.loads((ROOT / "examples/transcriptomics.project.json").read_bytes())
            project["candidates"] = []
            status, analyzed, _ = request("/api/analyze", {"project": project}, cookie=cookie, token=token)
            assert status == 200
            project = analyzed["project"]
            assert project["privacy"]["hosted_processing_receipts"]
            status, executed, _ = request("/api/execute", {"project": project, "control_id": project["controls"][0]["control_id"],
                "config": {"kind": "REFERENCE", "expected_difference": 2.0, "assumptions": ["Synthetic independent units."]},
                "csv": (ROOT / "examples/positive_reference.csv").read_text()}, cookie=cookie, token=token)
            assert status == 200 and executed["project"]["results"][-1]["outcome"] == "PASS"
            status, report, _ = request("/api/report", {"project": executed["project"]}, cookie=cookie, token=token)
            assert status == 200 and ORIGIN.encode() in report
            record["checks"].append({"name": "actual_full_analysis_reference_execution_and_report", "status": "PASS"})

            def probe(name, *, body=False, drip=False):
                started = time.monotonic()
                with socket.create_connection(("127.0.0.1", port), timeout=READ_DEADLINE_SECONDS + 5) as client:
                    if body:
                        raw = (f"POST /api/parse-json HTTP/1.1\r\nHost: controlomics.example\r\nX-Forwarded-Proto: https\r\nOrigin: {ORIGIN}\r\nCookie: {cookie}\r\nX-Controlomics-Token: {token}\r\nContent-Type: application/json\r\nContent-Length: 1000\r\n\r\n".encode() + b"{")
                    else:
                        raw = b"GET /healthz HTTP/1.1\r\nHost: controlomics.example\r\nX-Private-Fixture: " + MARKER.encode()
                    client.sendall(raw)
                    received = bytearray()
                    next_send = started + 0.5
                    client.settimeout(0.1 if drip else READ_INACTIVITY_SECONDS + 5)
                    while True:
                        if drip and time.monotonic() >= next_send:
                            try:
                                client.sendall(b"x")
                            except OSError:
                                break
                            next_send += 0.5
                        try:
                            chunk = client.recv(65536)
                            if not chunk:
                                break
                            received.extend(chunk)
                            if body and b"\r\n\r\n" in received:
                                header, _, response_body = bytes(received).partition(b"\r\n\r\n")
                                length = next(int(line.split(b":", 1)[1]) for line in header.split(b"\r\n") if line.lower().startswith(b"content-length:"))
                                if len(response_body) >= length:
                                    break
                        except socket.timeout:
                            if not drip or time.monotonic() > started + READ_DEADLINE_SECONDS + 5:
                                raise AssertionError("Transport did not finish within its bounded observation window")
                        except ConnectionResetError:
                            break
                    elapsed = time.monotonic() - started
                    expected = READ_DEADLINE_SECONDS if drip else READ_INACTIVITY_SECONDS
                    assert expected - 0.5 <= elapsed <= expected + 5, (name, elapsed)
                    assert MARKER.encode() not in received
                    if body:
                        assert bytes(received).startswith(b"HTTP/1.1 400 "), bytes(received)[:80]
                    return {"name": name, "status": "PASS", "elapsed_seconds": round(elapsed, 3), "expected_limit_seconds": expected}

            for drip in (False, True):
                outcomes, errors = [], []

                def run_probe(name, body):
                    try:
                        outcomes.append(probe(name, body=body, drip=drip))
                    except Exception as error:
                        errors.append(type(error).__name__)

                threads = [threading.Thread(target=run_probe, args=(f"{'total_deadline' if drip else 'inactivity'}_{'body' if body else 'headers'}", body)) for body in (False, True)]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(timeout=READ_DEADLINE_SECONDS + 6)
                assert all(not thread.is_alive() for thread in threads) and not errors, errors
                record["checks"].extend(outcomes)
                assert request("/api/parse-json", {"content": "{}"}, cookie=cookie, token=token)[0] == 200
                record["checks"].append({"name": "action_slot_recovered_after_" + ("total_deadline" if drip else "inactivity"), "status": "PASS"})

            with socket.create_connection(("127.0.0.1", port), timeout=5) as client:
                client.sendall(b"GET /healthz HTTP/1.1\r\nHost: controlomics.example\r\n" + MARKER.encode() + b" invalid-header: value\r\n\r\n")
                response = client.recv(65536)
                assert response.startswith(b"HTTP/1.1 400 ") and MARKER.encode() not in response
            record["checks"].append({"name": "malformed_header_error_redacted", "status": "PASS"})
        except Exception as error:
            failure = error
            record["failure_type"] = type(error).__name__
            record["status"] = "FAIL"
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=12)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
            record["owned_server_exited"] = process is not None and process.poll() is not None
            listener.close()
    with socket.socket() as check:
        record["owned_endpoint_connection_refused"] = check.connect_ex(("127.0.0.1", port)) == errno.ECONNREFUSED
    record["owned_temporary_directory_removed"] = not scratch.exists()
    log = log_path.read_bytes()
    record["log_excludes_synthetic_private_marker"] = MARKER.encode() not in log
    record["server_log_sha256"] = hashlib.sha256(log).hexdigest()
    if failure is None and all(record[name] for name in ("owned_server_exited", "owned_endpoint_connection_refused", "owned_temporary_directory_removed", "log_excludes_synthetic_private_marker")):
        record["status"] = "PASS"
    else:
        record["status"] = "FAIL"
    with output.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": record["status"], "checks": len(record["checks"]), "owned_server_exited": record["owned_server_exited"]}))
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
