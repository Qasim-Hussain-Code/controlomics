"""Consent-gated WSGI adapter for temporary first-party hosted processing."""

from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import subprocess
import threading
import time
from collections import deque
from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path
from urllib.parse import urlsplit

from controlomics.execution import LocalExecutionError
from controlomics.hosting_privacy import HOSTED_PROCESSING_POLICY_REVISION
from controlomics.project import decode_json, parse_project_json
from controlomics.server import ASSETS, MAX_BODY, SECURITY_HEADERS, handle_action

POLICY_REVISION = HOSTED_PROCESSING_POLICY_REVISION
COOKIE_NAME = "__Host-ControlomicsSession"
SESSION_SECONDS = 3600
MAX_SESSIONS = 1024
REQUESTS_PER_MINUTE = 240
SESSION_REQUESTS_PER_MINUTE = 60
SESSION_EXECUTIONS_PER_MINUTE = 2
MAX_RESPONSE = 16 * 1024 * 1024
ACTION_PATHS = frozenset({
    "/api/inspect-input", "/api/annotation-template", "/api/annotate", "/api/specify-paired",
    "/api/review-bundle", "/api/open-bundle", "/api/evaluate", "/api/parse-json", "/api/interpret",
    "/api/analyze", "/api/add-claim", "/api/specify-control", "/api/method-review", "/api/review-template",
    "/api/report", "/api/literature/preview", "/api/literature/retrieve", "/api/model/preview", "/api/model/run",
    "/api/review", "/api/import-results", "/api/package", "/api/execute",
})


def canonical_origin(value):
    if not isinstance(value, str) or not value.isascii():
        raise ValueError("A canonical HTTPS public origin is required.")
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    if (parsed.scheme != "https" or parsed.username is not None or parsed.password is not None
            or parsed.port is not None or parsed.path or parsed.query or parsed.fragment
            or not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?", host)
            or any(not part or len(part) > 63 or part.startswith("-") or part.endswith("-") for part in host.split("."))
            or value != "https://" + host):
        raise ValueError("A canonical HTTPS public origin is required.")
    return value


def _encode(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


class HostedApplication:
    """One-worker, bounded, metadata-only session state; projects are never cached."""

    def __init__(self, public_origin, session_secret, *, trust_proxy=False):
        self.origin = canonical_origin(public_origin)
        self.host = urlsplit(self.origin).netloc
        if isinstance(session_secret, str):
            session_secret = session_secret.encode("utf-8")
        if not isinstance(session_secret, bytes) or len(session_secret) < 32:
            raise ValueError("A hosted session secret of at least 32 bytes is required.")
        if type(trust_proxy) is not bool:
            raise ValueError("The proxy setting must be explicit.")
        # A new worker requires session renewal even with the same deployment
        # secret. No request or consent is silently replayed after a cold start.
        self._key = hmac.digest(session_secret, b"worker:" + secrets.token_bytes(32), "sha256")
        self.trust_proxy = trust_proxy
        self._lock = threading.Lock()
        self._actions = threading.BoundedSemaphore(2)
        self._sessions = {}
        self._requests = deque()

    def _cookie(self, session):
        payload = _encode(json.dumps(session, sort_keys=True, separators=(",", ":")).encode("ascii"))
        return payload + "." + _encode(hmac.digest(self._key, b"cookie:" + payload.encode("ascii"), "sha256"))

    def _token(self, cookie):
        return _encode(hmac.digest(self._key, b"request:" + cookie.encode("ascii"), "sha256"))

    def _session(self, environ, now):
        header = environ.get("HTTP_COOKIE", "")
        if not isinstance(header, str) or len(header) > 4096 or "," in header:
            return None, None
        found = []
        for part in header.split(";"):
            name, separator, value = part.strip().partition("=")
            if name == COOKIE_NAME and separator:
                found.append(value)
        if len(found) != 1 or not re.fullmatch(r"[A-Za-z0-9_-]{1,700}\.[A-Za-z0-9_-]{43}", found[0]):
            return None, None
        cookie = found[0]
        payload, supplied = cookie.split(".")
        expected = _encode(hmac.digest(self._key, b"cookie:" + payload.encode("ascii"), "sha256"))
        if not hmac.compare_digest(supplied, expected):
            return None, None
        try:
            session = decode_json(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
            if (set(session) != {"sid", "iat", "exp", "policy", "grant"}
                    or not isinstance(session["sid"], str) or not re.fullmatch(r"[A-Za-z0-9_-]{32}", session["sid"])
                    or type(session["iat"]) is not int or type(session["exp"]) is not int
                    or not session["iat"] <= now < session["exp"] <= session["iat"] + SESSION_SECONDS
                    or session["policy"] not in ("", POLICY_REVISION)
                    or (session["policy"] == "" and session["grant"] is not None)
                    or (session["policy"] == POLICY_REVISION and
                        (type(session["grant"]) is not int or not session["iat"] <= session["grant"] <= now))):
                return None, None
        except (ValueError, TypeError, KeyError):
            return None, None
        return session, cookie

    def _binding(self, session):
        return hashlib.sha256(session["sid"].encode("ascii")).hexdigest()

    def _new_session(self, now):
        with self._lock:
            self._sessions = {key: value for key, value in self._sessions.items() if value["expiry"] > now}
            if len(self._sessions) >= MAX_SESSIONS:
                return None
            session = {"sid": secrets.token_urlsafe(24), "iat": now, "exp": now + SESSION_SECONDS, "policy": "", "grant": None}
            self._sessions[self._binding(session)] = {"expiry": session["exp"], "requests": deque(), "executions": deque(), "active": False}
            return session

    def _metadata(self, session, cookie):
        consented = session["policy"] == POLICY_REVISION
        return {"token": self._token(cookie), "mode": "HOSTED_TEMPORARY", "policy_revision": POLICY_REVISION,
                "consent_required": not consented, "hosting_consent": consented}

    def _request_allowed(self, now):
        with self._lock:
            while self._requests and self._requests[0] <= now - 60:
                self._requests.popleft()
            if len(self._requests) >= REQUESTS_PER_MINUTE:
                return False
            self._requests.append(now)
            return True

    def _admit(self, session, now, *, execution=False):
        with self._lock:
            state = self._sessions.get(self._binding(session))
            if state is None:
                return "SESSION_RENEWAL_REQUIRED"
            for name in ("requests", "executions"):
                while state[name] and state[name][0] <= now - 60:
                    state[name].popleft()
            if state["active"]:
                return "SESSION_BUSY"
            if len(state["requests"]) >= SESSION_REQUESTS_PER_MINUTE or (execution and len(state["executions"]) >= SESSION_EXECUTIONS_PER_MINUTE):
                return "SESSION_RATE_LIMIT"
            state["requests"].append(now)
            if execution:
                state["executions"].append(now)
            state["active"] = True
            return None

    def _release(self, session):
        with self._lock:
            state = self._sessions.get(self._binding(session))
            if state is not None:
                state["active"] = False

    def _private_proxy_peer(self, environ):
        try:
            peer = ipaddress.ip_address(environ.get("REMOTE_ADDR", ""))
            return (peer.is_private or peer.is_loopback) and not peer.is_unspecified and not peer.is_multicast
        except ValueError:
            return False

    def _secure_request(self, environ):
        # PUBLIC_ORIGIN is authoritative. Client forwarded-host/for values
        # never select an origin, a session or a rate-limit identity.
        if environ.get("HTTP_HOST") != self.host:
            return False
        # Shared links may carry click identifiers or campaign parameters.
        # Only fixed public assets ignore them; they never select content,
        # create sessions, authorize processing, or reach scientific actions.
        if (environ.get("QUERY_STRING", "")
                and not (environ.get("REQUEST_METHOD") in ("GET", "HEAD")
                         and environ.get("PATH_INFO") in ASSETS)):
            return False
        if "HTTP_X_FORWARDED_PROTO" in environ and environ["HTTP_X_FORWARDED_PROTO"] != "https":
            return False
        if not self.trust_proxy:
            return environ.get("wsgi.url_scheme") == "https"
        if environ.get("wsgi.url_scheme") not in ("http", "https") or environ.get("HTTP_X_FORWARDED_PROTO") != "https":
            return False
        return self._private_proxy_peer(environ)

    def _respond(self, start_response, status, body, content_type="application/json", *, cookie=None, filename=None, head=False):
        if isinstance(body, dict):
            body = json.dumps(body, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode("utf-8")
        if not isinstance(body, bytes) or len(body) > MAX_RESPONSE:
            status, body, content_type = 500, b'{"error":"Hosted response could not be prepared."}', "application/json"
        headers = [("Content-Type", content_type), ("Content-Length", str(len(body))), *SECURITY_HEADERS,
                   ("Strict-Transport-Security", "max-age=31536000"), ("Cross-Origin-Resource-Policy", "same-origin")]
        if cookie is not None:
            headers.append(("Set-Cookie", f"{COOKIE_NAME}={cookie}; Path=/; Max-Age={SESSION_SECONDS}; Secure; HttpOnly; SameSite=Strict"))
        if filename is not None:
            if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", filename):
                raise ValueError("Invalid response disposition.")
            headers.append(("Content-Disposition", f'attachment; filename="{filename}"'))
        start_response(f"{status} {HTTPStatus(status).phrase}", headers)
        return [b"" if head else body]

    def _error(self, start_response, status, code, message):
        return self._respond(start_response, status, {"error": message, "code": code})

    def __call__(self, environ, start_response):
        try:
            return self._handle(environ, start_response)
        except Exception:
            return self._error(start_response, 500, "HOSTED_OPERATION_FAILED", "Hosted operation failed. Private details are omitted; retry manually.")

    def _handle(self, environ, start_response):
        now = int(time.time())
        path, method = environ.get("PATH_INFO"), environ.get("REQUEST_METHOD")
        # Render documents the canonical Host for internal health probes, but
        # does not promise a forwarded HTTPS header on those direct probes.
        # This exception exposes fixed readiness only, never session state,
        # cookies, research inputs, or an action body.
        if (self.trust_proxy and path == "/healthz" and method in ("GET", "HEAD")
                and environ.get("HTTP_HOST") == self.host and not environ.get("QUERY_STRING", "")
                and self._private_proxy_peer(environ)):
            return self._respond(start_response, 200, {"status": "ok", "mode": "HOSTED_TEMPORARY"}, head=method == "HEAD")
        if not self._secure_request(environ):
            return self._error(start_response, 403, "HOSTED_ORIGIN_REJECTED", "Hosted origin verification failed.")
        if not self._request_allowed(now):
            return self._error(start_response, 429, "HOSTED_RATE_LIMIT", "Hosted request limit reached. Retry manually later.")
        if method in ("GET", "HEAD"):
            if path == "/healthz":
                return self._respond(start_response, 200, {"status": "ok", "mode": "HOSTED_TEMPORARY"}, head=method == "HEAD")
            if path in ASSETS:
                name, content_type = ASSETS[path]
                return self._respond(start_response, 200, (Path(__file__).parent / "web" / name).read_bytes(), content_type, head=method == "HEAD")
            if path == "/api/session" and method == "GET":
                if environ.get("HTTP_SEC_FETCH_SITE") not in (None, "same-origin", "none"):
                    return self._error(start_response, 403, "HOSTED_ORIGIN_REJECTED", "Hosted origin verification failed.")
                session, cookie = self._session(environ, now)
                with self._lock:
                    if session is not None and self._binding(session) not in self._sessions:
                        session = None
                if session is None:
                    session = self._new_session(now)
                    if session is None:
                        return self._error(start_response, 503, "HOSTED_SESSION_CAPACITY", "Hosted session capacity reached. Retry manually later.")
                    cookie = self._cookie(session)
                    return self._respond(start_response, 200, self._metadata(session, cookie), cookie=cookie)
                return self._respond(start_response, 200, self._metadata(session, cookie))
            return self._error(start_response, 404, "HOSTED_NOT_FOUND", "Resource not found.")
        if method != "POST":
            return self._error(start_response, 405, "HOSTED_METHOD_REJECTED", "Request method is unsupported.")
        if path not in ACTION_PATHS and path != "/api/hosting-consent":
            return self._error(start_response, 404, "HOSTED_NOT_FOUND", "Resource not found.")
        session, cookie = self._session(environ, now)
        supplied = environ.get("HTTP_X_CONTROLOMICS_TOKEN", "")
        if (environ.get("HTTP_ORIGIN") != self.origin or environ.get("HTTP_SEC_FETCH_SITE") not in (None, "same-origin")
                or session is None or not isinstance(supplied, str) or not supplied.isascii()
                or not hmac.compare_digest(supplied, self._token(cookie))):
            return self._error(start_response, 403, "SESSION_RENEWAL_REQUIRED", "Hosted session verification failed. Renew the session, then retry manually.")
        if path != "/api/hosting-consent" and session["policy"] != POLICY_REVISION:
            return self._error(start_response, 428, "HOSTING_CONSENT_REQUIRED", "Explicit temporary hosted-processing consent is required.")
        declared = environ.get("CONTENT_LENGTH", "")
        maximum = 512 if path == "/api/hosting-consent" else MAX_BODY
        if ("HTTP_TRANSFER_ENCODING" in environ or "HTTP_CONTENT_LENGTH" in environ
                or not isinstance(declared, str) or not declared.isascii() or not declared.isdecimal() or len(declared) > 10
                or not 0 < int(declared) <= maximum
                or environ.get("CONTENT_TYPE", "").split(";", 1)[0].strip() != "application/json"):
            return self._error(start_response, 400, "HOSTED_BODY_REJECTED", "Invalid hosted request framing or size.")
        if not self._actions.acquire(blocking=False):
            return self._error(start_response, 503, "HOSTED_BUSY", "Hosted processing is busy. Retry manually.")
        admitted = False
        try:
            refusal = self._admit(session, now, execution=path == "/api/execute")
            if refusal is not None:
                status = 403 if refusal == "SESSION_RENEWAL_REQUIRED" else 429
                return self._error(start_response, status, refusal, "Hosted session limit or state requires a manual retry or renewal.")
            admitted = True
            raw = environ["wsgi.input"].read(int(declared))
            if not isinstance(raw, bytes) or len(raw) != int(declared):
                raise ValueError("Incomplete request body.")
            data = decode_json(raw)
            if not isinstance(data, dict):
                raise ValueError("Hosted actions require a JSON object.")
            if path == "/api/hosting-consent":
                if set(data) != {"allowed", "policy_revision"} or data["allowed"] is not True or data["policy_revision"] != POLICY_REVISION:
                    return self._error(start_response, 400, "HOSTING_CONSENT_REJECTED", "Consent must explicitly match the current hosting policy.")
                if session["policy"] != POLICY_REVISION:
                    session = {**session, "policy": POLICY_REVISION, "grant": now}
                    cookie = self._cookie(session)
                    return self._respond(start_response, 200, self._metadata(session, cookie), cookie=cookie)
                return self._respond(start_response, 200, self._metadata(session, cookie))
            from controlomics.hosting_privacy import hosted_processing_receipt, record_hosted_input_summary, record_hosted_processing
            context = {"processor_origin": self.origin, "session_binding_sha256": self._binding(session),
                       "granted_at": datetime.fromtimestamp(session["grant"], timezone.utc)}
            if "project" in data:
                project = record_hosted_processing(parse_project_json(json.dumps(data["project"])), **context)
                data = {**data, "project": project.model_dump(mode="json")}
            result = handle_action(path, data)
            if isinstance(result, tuple):
                return self._respond(start_response, 200, result[0], result[1], filename=result[2])
            if "project" in result:
                project = record_hosted_processing(parse_project_json(json.dumps(result["project"])), **context)
                result = {**result, "project": project.model_dump(mode="json")}
            receipt = hosted_processing_receipt(**context)
            if "input_summary" in result:
                from controlomics.inputs import NumericInputSummary
                summary = record_hosted_input_summary(NumericInputSummary.model_validate_json(json.dumps(result["input_summary"])), receipt)
                result = {**result, "input_summary": summary.model_dump(mode="json")}
            result = {**result, "hosting_processing": receipt.model_dump(mode="json")}
            return self._respond(start_response, 200, result)
        except LocalExecutionError as error:
            return self._error(start_response, 400, error.code, str(error))
        except (ValueError, OSError, TypeError, KeyError, IndexError, RecursionError, subprocess.TimeoutExpired):
            return self._error(start_response, 400, "HOSTED_OPERATION_REJECTED", "Operation failed. Private input, credentials, and local paths are omitted.")
        finally:
            if admitted:
                self._release(session)
            self._actions.release()


def create_app(public_origin=None, session_secret=None, *, trust_proxy=None):
    if public_origin is None:
        public_origin = os.environ.get("PUBLIC_ORIGIN") or os.environ.get("RENDER_EXTERNAL_URL")
    if session_secret is None:
        session_secret = os.environ.get("CONTROLOMICS_SESSION_SECRET")
    if trust_proxy is None:
        setting = os.environ.get("CONTROLOMICS_TRUST_PROXY", "")
        if setting not in ("", "render"):
            raise ValueError("Unsupported hosted proxy setting.")
        trust_proxy = setting == "render"
    return HostedApplication(public_origin, session_secret, trust_proxy=trust_proxy)


_application = None
_application_lock = threading.Lock()


def application(environ, start_response):
    global _application
    if _application is None:
        with _application_lock:
            if _application is None:
                try:
                    _application = create_app()
                except (ValueError, TypeError):
                    body = b'{"error":"Hosted configuration is unavailable."}'
                    start_response("503 Service Unavailable", [("Content-Type", "application/json"), ("Content-Length", str(len(body))), *SECURITY_HEADERS])
                    return [body]
    return _application(environ, start_response)
