"""Loopback-only, stateless HTTP interface. Research records stay in browser memory."""

from __future__ import annotations

import hmac
import base64
import io
import json
import secrets
import subprocess
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from controlomics.evidence import Crossref, EuropePMC
from controlomics.execution import ExecutionConfig, build_package, execute_local, import_result
from controlomics.models import MessagesProvider, MethodBaseline
from controlomics.reasoning import NarrativeInput, describe_design, interpret_narrative
from controlomics.privacy import SafeField, SafeTransport
from controlomics.project import decode_json, parse_project_json, save_project
from controlomics.reports import render_report
from controlomics.schemas import ControlResult
from controlomics.workflow import (CandidateSubmission, HumanReview, Intake, NewClaim, add_claim, apply_review,
    audit_project, import_evidence, new_project, propose, review_methods, review_template, specify_candidate)

ASSETS = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/style.css": ("style.css", "text/css")}
MAX_BODY = 2 * 1024 * 1024


def project_from(data):
    return parse_project_json(json.dumps(data["project"]))


def workspace(project):
    return {"project": project.model_dump(mode="json"), "design_profiles": [
        {"claim_id": claim.claim_id, **describe_design(project.analysis, claim).model_dump(mode="json")}
        for claim in project.claims]}


def selected_claim(project, identifier):
    if identifier is None and len(project.claims) == 1:
        return project.claims[0].claim_id
    if identifier not in {claim.claim_id for claim in project.claims}:
        raise ValueError("select one known claim before hosted reasoning")
    return identifier


def handle_action(path, data):
    if path == "/api/inspect-input":
        from controlomics.inputs import inspect_numeric_input
        return {"input_summary": inspect_numeric_input(data["csv"].encode("utf-8"), data["adapter"]).model_dump(mode="json")}
    if path in ("/api/annotation-template", "/api/annotate"):
        from controlomics.evaluation import AnnotationSubmission, EvaluationBundle, apply_annotations, bundle_hash
        bundle = EvaluationBundle.model_validate_json(json.dumps(data["bundle"]))
        if path.endswith("template"):
            return {"bundle": bundle.model_dump(mode="json"), "bundle_sha256": bundle_hash(bundle)}
        updated, revision = apply_annotations(bundle, AnnotationSubmission.model_validate_json(json.dumps(data["submission"])))
        return {"bundle": updated.model_dump(mode="json"), "bundle_sha256": bundle_hash(updated), "revision": revision.model_dump(mode="json")}
    if path == "/api/specify-paired":
        from controlomics.execution import specify_paired_control
        return workspace(audit_project(specify_paired_control(project_from(data), data["claim_id"], data["rationale"], data["assumptions"])))
    if path == "/api/review-bundle":
        from controlomics.artifacts import create_review_bundle
        from controlomics.evaluation import EvaluationBundle
        evaluation = EvaluationBundle.model_validate_json(json.dumps(data["evaluation_bundle"])) if data.get("evaluation_bundle") is not None else None
        return create_review_bundle(project_from(data), data.get("network_audit", ()), evaluation, data.get("annotation_revisions", ())), "application/zip", "controlomics.review.zip"
    if path == "/api/open-bundle":
        from controlomics.artifacts import open_review_bundle
        project, ledger, evaluation, revisions, manifest = open_review_bundle(base64.b64decode(data["archive_base64"], validate=True))
        return {**workspace(project), "network_audit_restored": ledger, "evaluation_bundle": evaluation.model_dump(mode="json") if evaluation else None,
            "annotation_revisions": revisions, "bundle_limitations": manifest.limitations}
    if path == "/api/evaluate":
        from controlomics.evaluation import EvaluationBundle, evaluate
        bundle = EvaluationBundle.model_validate_json(json.dumps(data["bundle"]))
        return {"evaluation": evaluate(bundle, data.get("partition"))}
    if path == "/api/parse-json":
        return {"value": decode_json(data["content"])}
    if path == "/api/interpret":
        return {"draft": interpret_narrative(NarrativeInput.model_validate_json(json.dumps(data))).model_dump(mode="json")}
    if path == "/api/analyze":
        if "project" in data:
            project = project_from(data)
        else:
            intake = Intake.model_validate_json(json.dumps(data["intake"]))
            project = new_project(intake)
        provider = MethodBaseline() if data.get("reasoner") == "reference" else None
        return workspace(audit_project(review_methods(propose(project, provider))))
    if path == "/api/add-claim":
        submission = NewClaim.model_validate_json(json.dumps(data["claim"]))
        return workspace(audit_project(review_methods(propose(add_claim(project_from(data), submission)))))
    if path == "/api/specify-control":
        submission = CandidateSubmission.model_validate_json(json.dumps(data["specification"]))
        return workspace(audit_project(specify_candidate(project_from(data), submission)))
    if path == "/api/method-review":
        return workspace(audit_project(review_methods(project_from(data))))
    if path == "/api/review-template":
        return {"template": review_template(project_from(data), data["control_id"])}
    if path == "/api/report":
        return render_report(audit_project(project_from(data)), data.get("network_audit", ())).encode(), "text/html", "controlomics.report.html"
    if path in ("/api/literature/preview", "/api/literature/retrieve"):
        if type(data.get("public_confirmed")) is not bool or not data["public_confirmed"]:
            raise ValueError("a public-only query must be explicitly confirmed")
        cls = {"europepmc": EuropePMC, "crossref": Crossref}[data["provider"]]
        transport = SafeTransport(frozenset({cls.host}))
        provider = cls(transport)
        prepared = provider.prepare_search(data["query"], data.get("limit", 5))
        if path.endswith("preview"):
            return {"request": prepared.preview(), "approve_hash": prepared.approval_hash}
        project = project_from(data)
        try:
            records = provider.search(prepared, data.get("approve_hash"))
            project = import_evidence(project, records) if records else project
            return {**workspace(audit_project(project)), "network_audit": transport.audit}
        except ValueError:
            return {"error": "External retrieval failed; research input and provider response content are omitted.", "network_audit": transport.audit}
    if path in ("/api/model/preview", "/api/model/run"):
        if type(data.get("public_confirmed")) is not bool or not data["public_confirmed"]:
            raise ValueError("minimized model fields must be explicitly confirmed public")
        if not isinstance(data["fields"], dict):
            raise ValueError("model context must be a named public-field object")
        fields = tuple(SafeField(name, value, "SAFE") for name, value in data["fields"].items())
        host = urlsplit(data["endpoint"]).hostname
        transport = SafeTransport(frozenset({host}))
        provider = MessagesProvider(data["endpoint"], data["model"], transport, data.get("api_key"))
        prepared = provider.prepare(fields)
        if path.endswith("preview"):
            return {"request": prepared.preview(), "approve_hash": prepared.approval_hash}
        project = project_from(data)
        claim_id = selected_claim(project, data.get("claim_id"))
        try:
            proposal = provider.complete(prepared, data.get("approve_hash"))
            project = propose(project, provider=provider, proposal=proposal, claim_id=claim_id)
            return {**workspace(audit_project(project)), "network_audit": transport.audit}
        except (ValueError, KeyError, TypeError, IndexError):
            return {"error": "Hosted reasoning failed or returned invalid structured content. Credentials and response text are omitted.", "network_audit": transport.audit}
    if path == "/api/review":
        review = HumanReview.model_validate_json(json.dumps(data["review"]))
        return workspace(audit_project(apply_review(project_from(data), review)))
    if path == "/api/import-results":
        result = ControlResult.model_validate_json(json.dumps(data["result"]))
        return workspace(audit_project(import_result(project_from(data), result)))
    if path in ("/api/package", "/api/execute"):
        project = project_from(data)
        config = ExecutionConfig.model_validate_json(json.dumps(data["config"]))
        if path == "/api/execute":
            return workspace(audit_project(execute_local(project, data["control_id"], config, data["csv"].encode())))
        with TemporaryDirectory(prefix="controlomics_package_") as temporary:
            folder = Path(temporary) / "package"
            updated = build_package(project, data["control_id"], config, folder)
            save_project(updated, folder / "project.json")
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for file in sorted(folder.iterdir()):
                    archive.write(file, arcname=file.name)
            return {"project": updated.model_dump(mode="json"), "package_base64": base64.b64encode(buffer.getvalue()).decode(),
                    "filename": "controlomics.execution.zip"}
    raise ValueError("unknown application action")


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, port=8765):
        if type(port) is not int or not 0 <= port <= 65535:
            raise ValueError("invalid local port")
        self.session_token = secrets.token_urlsafe(32)
        super().__init__(("127.0.0.1", port), Handler)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def allowed_host(self):
        port = self.server.server_port
        return self.headers.get("Host") in (f"127.0.0.1:{port}", f"localhost:{port}")

    def reply(self, status, body, content_type="application/json", filename=None):
        if isinstance(body, dict):
            body = json.dumps(body, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type + ("; charset=utf-8" if content_type.startswith("text/") else ""))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if filename:
            self.send_header("Content-Disposition", 'attachment; filename="' + filename + '"')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.allowed_host():
            self.reply(403, {"error": "Local host verification failed."})
            return
        if self.path == "/api/session":
            self.reply(200, {"token": self.server.session_token})
        elif self.path in ASSETS:
            name, content_type = ASSETS[self.path]
            content = (Path(__file__).parent / "web" / name).read_bytes()
            self.reply(200, content, content_type)
        else:
            self.reply(404, {"error": "Resource not found."})

    def do_POST(self):
        self.connection.settimeout(10)
        origins = (f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}")
        try:
            token = self.headers.get("X-Controlomics-Token", "").encode("ascii")
        except UnicodeError:
            token = b""
        if not self.allowed_host() or self.headers.get("Origin") not in origins or not hmac.compare_digest(token, self.server.session_token.encode("ascii")):
            self.reply(403, {"error": "Local request authorization failed."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if 0 < length <= MAX_BODY else b""
        except (ValueError, OSError):
            self.reply(400, {"error": "Invalid local request body."})
            return
        try:
            if not 0 < length <= MAX_BODY or len(raw) != length or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                raise ValueError("invalid request size or content type")
            data = decode_json(raw)
            result = handle_action(self.path, data)
            if isinstance(result, tuple):
                self.reply(200, result[0], result[1], result[2])
            else:
                self.reply(200, result)
        except (ValueError, OSError, TypeError, KeyError, IndexError, RecursionError, subprocess.TimeoutExpired):
            self.reply(400, {"error": "Operation failed. Private input, credentials, and local paths are omitted."})


def serve_local(port=8765):
    with LocalServer(port) as server:
        print(f"Controlomics research alpha: http://127.0.0.1:{server.server_port}")
        print("Projects remain in browser memory. Export your work before closing the page. Press Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
