"""Exact-request approval, conservative screening, and bounded outbound transport."""

from __future__ import annotations

import hashlib
import http.client
import ipaddress
import json
import re
import socket
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import parse_qs, unquote, urlsplit

from controlomics.schemas import PrivacyClass

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
ALLOWED_FIELDS = {"public_query", "public_identifier", "question", "analysis_summary", "claim", "method", "organism"}
CREDENTIAL_PATTERNS = {
    "private_key": r"-----BEGIN .*PRIVATE KEY-----",
    "aws_access_key": r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
    "github_token": r"(?<![A-Za-z0-9])(?:ghp_[A-Za-z0-9_-]{12,}|gh[ousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})",
    "provider_key": r"(?<![A-Za-z0-9])(?:sk-[A-Za-z0-9_-]{12,}|hf_[A-Za-z0-9_-]{12,}|AIza[A-Za-z0-9_-]{35})",
    "bearer_token": r"(?i:\bBearer)\s+[A-Za-z0-9._~+/=-]{16,}",
    "named_credential": r"(?i:\b(?:password|api[_ -]?key|token))\s*[:=]\s*\S+",
}


def canonical_json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def screen_text(text: str) -> PrivacyClass:
    patterns = (
        *CREDENTIAL_PATTERNS.values(), r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        r"[A-Za-z]:[\\/]", r"(?:/home/|/Users/|\\\\)[^\s]+",
        r"(?i:\b(?:patient|subject|clinical|medical[ _-]?record)[ _-]?(?:id|identifier|number))\s*[:=]",
        r"(?i:\bMRN)\s*[:#=]?\s*\d{5,}\b",
        # Alphabetic boundaries also detect underscore-prefixed sequence-like runs.
        r"(?<![A-Za-z])[ACGTUNacgtun]{80,}(?![A-Za-z])",
        r"(?<![A-Za-z])[ACDEFGHIKLMNPQRSTVWY]{60,}(?![A-Za-z])",
        # U or X must not split a protein token. Require a protein-specific
        # letter so RNA runs retain their separate nucleotide threshold.
        r"(?<![A-Za-z])(?=[A-Z]*[DEFHIKLMPQRSVWY])[ACDEFGHIKLMNPQRSTVWYUX]{60,}(?![A-Za-z])",
    )
    if any(re.search(pattern, text) for pattern in patterns):
        return "RESTRICTED"
    # Count bases across separated blocks without joining arbitrary scientific prose.
    blocks = r"(?<![A-Za-z])[ACGTUNacgtun]{4,}(?:\s+[ACGTUNacgtun]{4,})+(?![A-Za-z])"
    if any(len(re.sub(r"\s", "", match.group())) >= 80 for match in re.finditer(blocks, text)):
        return "RESTRICTED"
    return "SENSITIVE_SCIENTIFIC"


def is_public_unicast_address(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return ip.is_global and not ip.is_multicast and not ip.is_reserved


@dataclass(frozen=True)
class SafeField:
    name: str
    value: str
    classification: PrivacyClass

    def __post_init__(self):
        if self.name not in ALLOWED_FIELDS or self.classification != "SAFE":
            raise ValueError("outbound fields must be allowlisted and explicitly classified SAFE")
        if not isinstance(self.value, str) or not self.value.strip() or len(self.value) > 12000:
            raise ValueError("outbound field is invalid")
        if screen_text(self.value) == "RESTRICTED":
            raise ValueError("outbound field failed privacy screening")


@dataclass(frozen=True)
class PreparedRequest:
    purpose: str
    method: str
    url: str
    fields: tuple[SafeField, ...]
    body: bytes | None = None

    def __post_init__(self):
        if self.purpose not in ("LITERATURE", "MODEL") or self.method not in ("GET", "POST"):
            raise ValueError("unsupported outbound operation")
        if not self.fields or len({item.name for item in self.fields}) != len(self.fields):
            raise ValueError("outbound fields must be explicit and unique")
        parts = urlsplit(self.url)
        if parts.scheme != "https" or parts.username or parts.password or parts.fragment or parts.port not in (None, 443):
            raise ValueError("outbound endpoints must use HTTPS without credentials or fragments")
        if self.purpose == "LITERATURE":
            fields = {item.name: item.value for item in self.fields}
            query = parse_qs(parts.query, strict_parsing=True)
            valid = False
            if parts.hostname == "www.ebi.ac.uk" and parts.path == "/europepmc/webservices/rest/search":
                valid = set(query) == {"query", "format", "resultType", "pageSize"} and query["query"] == [fields.get("public_query")] and query["format"] == ["json"] and query["resultType"] == ["core"]
                valid = valid and len(query["pageSize"]) == 1 and query["pageSize"][0].isdigit() and 1 <= int(query["pageSize"][0]) <= 20
            elif parts.hostname == "api.crossref.org":
                if parts.path == "/works":
                    valid = set(query) == {"query.bibliographic", "rows"} and query["query.bibliographic"] == [fields.get("public_query")]
                    valid = valid and len(query["rows"]) == 1 and query["rows"][0].isdigit() and 1 <= int(query["rows"][0]) <= 20
                else:
                    valid = not query and parts.path.startswith("/works/") and unquote(parts.path[len("/works/"):]) == fields.get("public_identifier")
            if not valid or self.method != "GET" or self.body is not None or len(fields) != 1:
                raise ValueError("literature URL must correspond exactly to its approved public field")
        else:
            from controlomics.models import model_policy
            from controlomics.project import decode_json
            body = decode_json(self.body or b"")
            if parts.query or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./:-]{0,200}", str(body.get("model", ""))) or screen_text(str(body.get("model", ""))) == "RESTRICTED":
                raise ValueError("model endpoint or identifier is invalid")
            if self.method != "POST" or set(body) != {"model", "messages", "temperature", "max_tokens", "stream"}:
                raise ValueError("model payload contains unsupported content")
            if type(body["temperature"]) not in (int, float) or body["temperature"] != 0 or type(body["max_tokens"]) is not int or body["max_tokens"] != 3000 or body["stream"] is not False:
                raise ValueError("model generation settings must match the fixed public request")
            messages = body["messages"]
            if len(messages) != 2 or messages[0] != {"role": "system", "content": model_policy()}:
                raise ValueError("model policy cannot be replaced by user content")
            if set(messages[1]) != {"role", "content"} or messages[1].get("role") != "user" or decode_json(messages[1].get("content", "")) != {item.name: item.value for item in self.fields}:
                raise ValueError("model user data differ from the approved fields")

    def preview(self):
        return {
            "purpose": self.purpose, "method": self.method, "url": self.url,
            "fields": [{"name": item.name, "value": item.value, "classification": item.classification} for item in self.fields],
            "body": self.body.decode("utf-8") if self.body is not None else None,
        }

    @property
    def approval_hash(self):
        return digest(canonical_json(self.preview()))


class ApprovalRequired(ValueError):
    pass


class TransportError(ValueError):
    pass


@dataclass
class SafeTransport:
    allowed_hosts: frozenset[str]
    audit: list[dict] = field(default_factory=list)

    def send(self, prepared: PreparedRequest, approval_hash: str | None, api_key: str | None = None):
        if approval_hash != prepared.approval_hash:
            raise ApprovalRequired("review and approve the exact outbound request first")
        host = urlsplit(prepared.url).hostname
        if host not in self.allowed_hosts:
            raise TransportError("destination is outside the configured allowlist")
        event = {**prepared.preview(), "request_sha256": prepared.approval_hash,
                 "sent_at": datetime.now(timezone.utc).isoformat(), "status": "BLOCKED"}
        # Audit contains approved public text and a body hash, never authorization headers.
        event["body"] = None
        event["body_sha256"] = digest(prepared.body) if prepared.body is not None else None
        event["credential_supplied"] = bool(api_key)
        event["payload_transmission"] = "NOT_STARTED"
        self.audit.append(event)
        try:
            addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            if not addresses or any(not is_public_unicast_address(address[4][0]) for address in addresses):
                raise TransportError("nonpublic destinations are disabled")
            headers = {"Accept": "application/json", "User-Agent": "Controlomics/0.2 scientific-metadata-client"}
            if prepared.body is not None:
                headers["Content-Type"] = "application/json"
            if api_key:
                if not isinstance(api_key, str) or any(character in api_key for character in "\r\n"):
                    raise TransportError("invalid credential")
                headers["Authorization"] = "Bearer " + api_key
            # Connect to the checked IP, while retaining the original hostname for TLS.
            address = addresses[0][4][0]
            connection = http.client.HTTPSConnection(host, timeout=20)
            try:
                context = ssl.create_default_context()
                # Keep certificate/hostname defaults and any stricter protocol floor.
                if context.minimum_version < ssl.TLSVersion.TLSv1_2:
                    context.minimum_version = ssl.TLSVersion.TLSv1_2
                connection.sock = context.wrap_socket(
                    socket.create_connection((address, 443), timeout=20), server_hostname=host)
                parts = urlsplit(prepared.url)
                path = parts.path + ("?" + parts.query if parts.query else "")
                event["payload_transmission"] = "ATTEMPTED"
                connection.request(prepared.method, path, body=prepared.body, headers=headers)
                event["payload_transmission"] = "COMPLETED"
                response = connection.getresponse()
                if not 200 <= response.status < 300:
                    raise TransportError("external redirects and unsuccessful responses are rejected")
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            finally:
                connection.close()
            if len(raw) > MAX_RESPONSE_BYTES:
                raise TransportError("external response exceeds its size limit")
            from controlomics.project import decode_json
            result = decode_json(raw)
            event.update(status="COMPLETED", response_sha256=digest(raw), response_bytes=len(raw))
            return result
        except (OSError, ValueError, RecursionError, http.client.HTTPException):
            event["status"] = "FAILED"
            raise TransportError("external request failed; response content and credentials are omitted") from None
        finally:
            # Interruptions propagate to the caller, which may still export this ledger.
            # Once sending starts, an incomplete request cannot remain BLOCKED.
            if event["status"] == "BLOCKED" and event["payload_transmission"] != "NOT_STARTED":
                event["status"] = "FAILED"
