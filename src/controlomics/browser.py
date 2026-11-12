"""Browser workspace runtime: the shared scientific dispatch inside Pyodide.

The interface, this module, and the scientific core run in the visitor's browser.
Actions receive the same transient project snapshots as the local server and
return records or downloads to the page. No first-party server receives research
input. The page calls `session()` once and `dispatch()` for each action.
"""

from __future__ import annotations

import base64
import io
import json
import runpy
import secrets
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from controlomics import execution
from controlomics.execution import LocalExecutionError
from controlomics.privacy import MAX_RESPONSE_BYTES, SafeTransport, TransportError, digest
from controlomics.project import decode_json
from controlomics.server import MAX_BODY, handle_action

DEPLOYMENT_MODE = "BROWSER"
REDACTED_FAILURE = "Operation failed. Private input, credentials, and local paths are omitted."
UNEXPECTED_FAILURE = "Local operation failed unexpectedly. Private details are omitted; retry manually."
RUNNER_NAME = "run_control.py"


PHASES = ("NOT_STARTED", "ATTEMPTED", "COMPLETED")
_outcomes: dict = {}


class FetchRequired(Exception):
    """An approved request that the page must transmit before the action can finish.

    Deliberately not a ValueError, so provider error handling cannot absorb it.
    """

    def __init__(self, request):
        super().__init__("browser transmission required")
        self.request = request


class BrowserTransport(SafeTransport):
    """Approval, allowlist, and ledger checks with transmission by the page.

    Python checks the exact approved request first, as the local transport does.
    Without a recorded outcome it asks the page to send that request and records
    nothing. The page then repeats the action with the outcome, keyed by the
    request hash, and the ledger records the phase the page actually reached.
    """

    def send(self, prepared, approval_hash, api_key=None):
        _, event = self.open_event(prepared, approval_hash, api_key)
        if api_key and (not isinstance(api_key, str) or any(character in api_key for character in "\r\n")):
            # As in the local transport, a malformed credential fails before any transmission.
            event["status"] = "FAILED"
            raise TransportError("external request failed; response content and credentials are omitted")
        outcome = _outcomes.get(prepared.approval_hash)
        if outcome is None:
            self.audit.remove(event)
            raise FetchRequired({"purpose": prepared.purpose, "method": prepared.method, "url": prepared.url,
                                 "body": prepared.body.decode("utf-8") if prepared.body is not None else None,
                                 "request_sha256": prepared.approval_hash, "credential": bool(api_key)})
        valid = (isinstance(outcome, dict) and outcome.get("phase") in PHASES and type(outcome.get("ok")) is bool
                 and (not outcome["ok"] or outcome["phase"] == "COMPLETED" and isinstance(outcome.get("body_base64"), str)))
        if not valid:
            event["status"] = "FAILED"
            event["payload_transmission"] = "ATTEMPTED"
            raise TransportError("external request outcome is invalid; response content is omitted")
        event["payload_transmission"] = outcome["phase"]
        try:
            if not outcome["ok"]:
                raise TransportError("external redirects and unsuccessful responses are rejected")
            raw = base64.b64decode(outcome["body_base64"], validate=True)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise TransportError("external response exceeds its size limit")
            result = decode_json(raw)
            event.update(status="COMPLETED", response_sha256=digest(raw), response_bytes=len(raw))
            return result
        except (ValueError, RecursionError):
            event["status"] = "FAILED"
            raise TransportError("external request failed; response content and credentials are omitted") from None


class InProcessRunner:
    """Stand-in for `subprocess` while the fixed runner executes in the browser.

    Pyodide cannot start processes. The fixed, hash-checked runner script runs as
    `__main__` in this interpreter with the arguments `execute_local` supplies.
    Modules it imports from its own package folder are removed afterwards. The
    page enforces the local time limit by ending the worker that hosts Python.
    """

    TimeoutExpired = subprocess.TimeoutExpired
    CompletedProcess = subprocess.CompletedProcess

    @staticmethod
    def run(args, capture_output=False, text=False, timeout=None, check=False):
        if len(args) < 2 or args[0] != sys.executable or Path(args[1]).name != RUNNER_NAME or check:
            raise ValueError("only the fixed runner can run in the browser workspace")
        script = Path(args[1])
        folder = script.parent.resolve()
        saved_argv, saved_path, before = sys.argv, list(sys.path), set(sys.modules)
        out, err = io.StringIO(), io.StringIO()
        code = 0
        try:
            sys.argv = [str(script), *args[2:]]
            sys.path.insert(0, str(folder))
            with redirect_stdout(out), redirect_stderr(err):
                runpy.run_path(str(script), run_name="__main__")
        except SystemExit as stop:
            code = stop.code if isinstance(stop.code, int) else (0 if stop.code is None else 1)
        except Exception:
            code = 1
        finally:
            sys.argv = saved_argv
            sys.path[:] = saved_path
            # Remove only the runner's own package modules. Shared standard-library
            # modules stay, so classes such as datetime keep a single identity.
            for name in set(sys.modules) - before:
                origin = getattr(sys.modules[name], "__file__", None)
                if origin and Path(origin).resolve().parent == folder:
                    del sys.modules[name]
        return subprocess.CompletedProcess(args, code, out.getvalue() if text else out.getvalue().encode(),
                                           err.getvalue() if text else err.getvalue().encode())


def install():
    """Route fixed-runner execution through the in-process runner."""
    execution.subprocess = InProcessRunner


def session() -> str:
    return json.dumps({"token": secrets.token_urlsafe(32), "deployment": {"mode": DEPLOYMENT_MODE}})


def _reply(status, body):
    return json.dumps({"status": status, "json": body}, allow_nan=False)


def dispatch(path: str, payload: str, outcomes: str = "{}") -> str:
    """Run one interface action and return a JSON envelope for the page.

    Errors use the local server's fixed redacted messages and status codes,
    including serialization failures, which the server also reports as 400.
    An approved external request returns {"fetch": request} for the page to
    send; the page repeats the action with `outcomes` keyed by request hash.
    """
    global _outcomes
    try:
        _outcomes = json.loads(outcomes)
        if not isinstance(_outcomes, dict):
            raise ValueError("outcomes must be an object")
    except (ValueError, RecursionError):
        _outcomes = {}
        return _reply(400, {"error": REDACTED_FAILURE})
    try:
        raw = payload.encode("utf-8")
        if not 0 < len(raw) <= MAX_BODY:
            raise ValueError("invalid request size")
        data = decode_json(raw)
        if not isinstance(data, dict):
            raise ValueError("local actions require a JSON object")
        result = handle_action(path, data, BrowserTransport)
        if isinstance(result, tuple):
            content, content_type, filename = result
            return json.dumps({"status": 200, "body_base64": base64.b64encode(content).decode("ascii"),
                               "content_type": content_type, "filename": filename})
        return _reply(200, result)
    except FetchRequired as required:
        return json.dumps({"status": 0, "fetch": required.request})
    except LocalExecutionError as error:
        return _reply(400, {"error": str(error), "code": error.code})
    except (ValueError, OSError, TypeError, KeyError, IndexError, RecursionError, UnicodeError, subprocess.TimeoutExpired):
        return _reply(400, {"error": REDACTED_FAILURE})
    except Exception:
        return _reply(500, {"error": UNEXPECTED_FAILURE})
    finally:
        _outcomes = {}
