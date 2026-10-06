"""Bounded local review archives. Hash consistency is not authenticated provenance."""

from __future__ import annotations

import io
import ipaddress
import json
import stat
import zipfile
import zlib
from datetime import datetime, timezone
from typing import Annotated, Literal
from urllib.parse import unquote, urlsplit

from pydantic import AwareDatetime, Field, model_validator

from controlomics import __version__
from controlomics.evaluation import AnnotationRevision, EvaluationBundle, bundle_hash
from controlomics.privacy import PreparedRequest, SafeField, canonical_json, digest, screen_text
from controlomics.project import decode_json, parse_project_json
from controlomics.reports import render_report
from controlomics.schemas import Identifier, Record, Sha256, Text

MAX_ARCHIVE = 1024 * 1024
MAX_EXPANDED = 8 * 1024 * 1024
NAMES = {"project.json", "network_audit.json", "report.html", "evaluation.json", "annotation_revisions.json"}


class PublicAuditField(Record):
    name: Text
    value: Text
    classification: Literal["SAFE"]

    @model_validator(mode="after")
    def screened(self):
        SafeField(self.name, self.value, self.classification)
        return self


class NetworkAuditEvent(Record):
    purpose: Literal["LITERATURE", "MODEL"]
    method: Literal["GET", "POST"]
    url: Text
    fields: Annotated[tuple[PublicAuditField, ...], Field(min_length=1, max_length=7)]
    body: None = None
    request_sha256: Sha256
    body_sha256: Sha256 | None = None
    sent_at: AwareDatetime
    status: Literal["BLOCKED", "FAILED", "COMPLETED"]
    credential_supplied: bool
    payload_transmission: Literal["NOT_STARTED", "ATTEMPTED", "COMPLETED"]
    response_sha256: Sha256 | None = None
    response_bytes: Annotated[int, Field(ge=0, le=2 * 1024 * 1024)] | None = None

    @model_validator(mode="after")
    def safe_ledger(self):
        if len({item.name for item in self.fields}) != len(self.fields):
            raise ValueError("audit fields must be unique")
        parts = urlsplit(self.url)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.fragment or parts.port not in (None, 443) or screen_text((parts.hostname or "") + " " + unquote(parts.path + "?" + parts.query)) == "RESTRICTED":
            raise ValueError("audit URL contains unsupported content")
        try:
            address = ipaddress.ip_address(parts.hostname)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise ValueError("audit destination is not public")
        if self.purpose == "LITERATURE":
            prepared = PreparedRequest(self.purpose, self.method, self.url,
                tuple(SafeField(item.name, item.value, item.classification) for item in self.fields))
            if self.body_sha256 is not None or prepared.approval_hash != self.request_sha256:
                raise ValueError("literature audit does not match its approved request")
        elif self.method != "POST" or parts.query or self.body_sha256 is None:
            raise ValueError("model audit must contain a body hash and no body or query")
        if self.status == "COMPLETED" and (self.payload_transmission != "COMPLETED" or self.response_sha256 is None or self.response_bytes is None):
            raise ValueError("completed audit requires a response receipt")
        if self.status != "COMPLETED" and (self.response_sha256 is not None or self.response_bytes is not None):
            raise ValueError("incomplete audit cannot assert a response receipt")
        return self


class ArtifactHash(Record):
    sha256: Sha256
    bytes: Annotated[int, Field(ge=0, le=4 * 1024 * 1024)]


class ReviewManifest(Record):
    format: Literal["controlomics.review_bundle.v0.1"] = "controlomics.review_bundle.v0.1"
    controlomics_version: Text
    created_at: AwareDatetime
    project_id: Identifier
    artifacts: dict[str, ArtifactHash]
    limitations: tuple[Text, ...]


def validated_ledger(items):
    if not isinstance(items, (list, tuple)) or len(items) > 500:
        raise ValueError("network ledger must contain at most five hundred events")
    return [NetworkAuditEvent.model_validate_json(json.dumps(item)).model_dump(mode="json") for item in items]


def validated_revisions(items, evaluation):
    if not isinstance(items, (list, tuple)) or len(items) > 500:
        raise ValueError("annotation revisions exceed their limit")
    revisions = [AnnotationRevision.model_validate_json(json.dumps(item)) for item in items]
    if revisions and (evaluation is None or revisions[-1].updated_sha256 != bundle_hash(evaluation)):
        raise ValueError("annotation revisions do not end at the supplied evaluation snapshot")
    if any(left.updated_sha256 != right.previous_sha256 or left.recorded_at > right.recorded_at for left, right in zip(revisions, revisions[1:])):
        raise ValueError("annotation revision chain is inconsistent")
    return [item.model_dump(mode="json") for item in revisions]


def create_review_bundle(project, network_audit=(), evaluation=None, annotation_revisions=()):
    project = parse_project_json(canonical_json(project.model_dump(mode="json")))
    ledger = validated_ledger(network_audit)
    if evaluation is not None:
        evaluation = EvaluationBundle.model_validate_json(canonical_json(evaluation.model_dump(mode="json")))
    revisions = validated_revisions(annotation_revisions, evaluation)
    documents = {"project.json": canonical_json(project.model_dump(mode="json")),
        "network_audit.json": canonical_json(ledger), "report.html": render_report(project, ledger).encode()}
    if evaluation is not None:
        documents["evaluation.json"] = canonical_json(evaluation.model_dump(mode="json"))
        documents["annotation_revisions.json"] = canonical_json(revisions)
    manifest = ReviewManifest(controlomics_version=__version__, created_at=datetime.now(timezone.utc),
        project_id=project.manifest.project_id, artifacts={name: ArtifactHash(sha256=digest(content), bytes=len(content)) for name, content in documents.items()},
        limitations=("Hashes detect changes relative to this manifest; neither manifest nor reviewer identities are authenticated.",
            "The supplied network ledger may be incomplete. Model bodies are omitted, so their request hashes cannot be reconstructed here.",
            "Raw input files, full source texts, and authorization credentials are not bundled. Project descriptions and public query text may still be private research material.",
            "Prior annotation and evidence snapshot content must be retained separately when needed; revision hashes alone cannot recover it."))
    documents["manifest.json"] = canonical_json(manifest.model_dump(mode="json"))
    if sum(map(len, documents.values())) > MAX_EXPANDED:
        raise ValueError("review bundle exceeds the expanded size budget")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(documents.items()):
            archive.writestr(name, content)
    result = buffer.getvalue()
    if len(result) > MAX_ARCHIVE:
        raise ValueError("review bundle exceeds the one MiB archive limit")
    return result


def open_review_bundle(raw):
    if len(raw) > MAX_ARCHIVE:
        raise ValueError("review bundle exceeds the archive limit")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            names = [item.filename for item in members]
            if len(names) != len(set(names)) or not set(names) <= NAMES | {"manifest.json"} or not {"manifest.json", "project.json", "network_audit.json", "report.html"} <= set(names):
                raise ValueError("review bundle has missing, duplicate, or unsupported members")
            if sum(item.file_size for item in members) > MAX_EXPANDED or any(item.file_size > 4 * 1024 * 1024 or item.flag_bits & 1 or stat.S_ISLNK(item.external_attr >> 16) or item.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) for item in members):
                raise ValueError("review bundle member exceeds safe archive bounds")
            documents = {item.filename: archive.read(item) for item in members}
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, zlib.error) as error:
        raise ValueError("invalid review archive") from error
    manifest = ReviewManifest.model_validate_json(canonical_json(decode_json(documents["manifest.json"])))
    if set(manifest.artifacts) != set(documents) - {"manifest.json"}:
        raise ValueError("review manifest members differ")
    for name, expected in manifest.artifacts.items():
        if len(documents[name]) != expected.bytes or digest(documents[name]) != expected.sha256:
            raise ValueError("review bundle content differs from its manifest")
    project = parse_project_json(documents["project.json"])
    if project.manifest.project_id != manifest.project_id:
        raise ValueError("review bundle project binding differs")
    ledger = validated_ledger(decode_json(documents["network_audit.json"]))
    evaluation = EvaluationBundle.model_validate_json(canonical_json(decode_json(documents["evaluation.json"]))) if "evaluation.json" in documents else None
    if ("annotation_revisions.json" in documents) != (evaluation is not None):
        raise ValueError("evaluation and revision sidecar must be supplied together")
    revisions = validated_revisions(decode_json(documents["annotation_revisions.json"]) if evaluation else (), evaluation)
    # HTML from an imported archive is never opened or executed. A fresh report is generated on export.
    return project, ledger, evaluation, revisions, manifest
