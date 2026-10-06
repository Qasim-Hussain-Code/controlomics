"""Official literature adapters. Identity verification does not establish entailment."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol
from urllib.parse import quote, urlencode

from controlomics.privacy import PreparedRequest, SafeField, SafeTransport, canonical_json, digest
from controlomics.schemas import BiologicalContext, EvidenceIdentifier, EvidenceItem, VerificationRecord


class EvidenceProvider(Protocol):
    def prepare_search(self, query: str, limit: int = 5) -> PreparedRequest: ...
    def prepare_resolve(self, identifier: EvidenceIdentifier) -> PreparedRequest: ...
    def search(self, prepared: PreparedRequest, approval_hash: str) -> tuple[EvidenceItem, ...]: ...


def _limit(limit):
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("literature searches require between one and twenty records")


def _identifier(namespace, value):
    authority = {"PMID": "PubMed", "PMCID": "PMC", "DOI": "doi.org"}[namespace]
    return EvidenceIdentifier(namespace=namespace, value=value, authority=authority)


def _checked_metadata(parser, response):
    try:
        return parser(response)
    except (AttributeError, TypeError, KeyError, IndexError, ValueError):
        raise ValueError("External publication metadata had an unsupported structure; content is omitted.") from None


def _item(source, identifiers, title, authors, year, kind, raw, licensing=None):
    now = datetime.now(timezone.utc)
    key = next((item.normalized_key for item in identifiers if item.namespace == "DOI"), identifiers[0].normalized_key)
    artifact = digest(canonical_json(raw))
    return EvidenceItem(
        evidence_id="evidence." + digest(canonical_json(key))[:24], source=source,
        identifiers=tuple(identifiers), title=title or None, authors=tuple(authors), year=year,
        retrieved_at=now, publication_type=kind, evidence_type="Publication metadata",
        biological_context=BiologicalContext(), licensing_restrictions=licensing or "Source text rights must be checked separately; abstract and full text are not exported.",
        existence_status="VERIFIED", content_sha256=artifact,
        existence_check=VerificationRecord(
            reviewer_kind="PROGRAMMATIC", reviewer="controlomics.evidence." + source,
            method="Parsed identifiers and publication metadata from the official provider response. No statement entailment was assessed.",
            checked_at=now, artifact_sha256=artifact,
            limitations=("Provider metadata can be incomplete or incorrect.",),
        ), limitations=("Identity verification does not establish support for a scientific statement.",),
    )


class EuropePMC:
    host = "www.ebi.ac.uk"
    endpoint = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    def __init__(self, transport: SafeTransport):
        self.transport = transport

    def prepare_search(self, query, limit=5):
        _limit(limit)
        field = SafeField("public_query", query, "SAFE")
        url = self.endpoint + "?" + urlencode({"query": query, "format": "json", "resultType": "core", "pageSize": limit})
        return PreparedRequest("LITERATURE", "GET", url, (field,))

    def prepare_resolve(self, identifier):
        if identifier.namespace == "PMID":
            query = f"EXT_ID:{identifier.value} AND SRC:MED"
        elif identifier.namespace == "PMCID":
            query = f"PMCID:{identifier.value}"
        elif identifier.namespace == "DOI":
            query = 'DOI:"' + identifier.value.replace('"', '') + '"'
        else:
            raise ValueError("Europe PMC resolves DOI, PMID, or PMCID")
        return self.prepare_search(query, 5)

    def search(self, prepared, approval_hash):
        response = self.transport.send(prepared, approval_hash)
        return _checked_metadata(self._parse, response)

    def _parse(self, response):
        records = response.get("resultList", {}).get("result", [])
        result = []
        for record in records:
            identifiers = []
            for namespace, value in (("PMID", record.get("id") if record.get("source") == "MED" else None),
                                     ("PMCID", record.get("pmcid")), ("DOI", record.get("doi"))):
                if value:
                    identifiers.append(_identifier(namespace, str(value)))
            if not identifiers:
                continue
            authors = [item.get("fullName") for item in record.get("authorList", {}).get("author", []) if item.get("fullName")]
            year = int(record["pubYear"]) if str(record.get("pubYear", "")).isdigit() else None
            types = record.get("pubTypeList", {}).get("pubType", [])
            result.append(_item("EuropePMC", identifiers, record.get("title"), authors, year,
                                "; ".join(types) or None, record))
        return tuple(result)


class Crossref:
    host = "api.crossref.org"
    endpoint = "https://api.crossref.org/works"

    def __init__(self, transport: SafeTransport):
        self.transport = transport

    def prepare_search(self, query, limit=5):
        _limit(limit)
        field = SafeField("public_query", query, "SAFE")
        return PreparedRequest("LITERATURE", "GET", self.endpoint + "?" + urlencode({"query.bibliographic": query, "rows": limit}), (field,))

    def prepare_resolve(self, identifier):
        if identifier.namespace != "DOI":
            raise ValueError("Crossref resolves DOI identifiers")
        field = SafeField("public_identifier", identifier.value, "SAFE")
        return PreparedRequest("LITERATURE", "GET", self.endpoint + "/" + quote(identifier.value, safe=""), (field,))

    def search(self, prepared, approval_hash):
        response = self.transport.send(prepared, approval_hash)
        return _checked_metadata(self._parse, response)

    def _parse(self, response):
        message = response.get("message", {})
        records = message.get("items", []) if "items" in message else [message]
        result = []
        for record in records:
            if not record.get("DOI"):
                continue
            identifiers = [_identifier("DOI", record["DOI"])]
            authors = [" ".join(filter(None, (item.get("given"), item.get("family")))) for item in record.get("author", [])]
            authors = [item for item in authors if item]
            dates = record.get("published", record.get("issued", {})).get("date-parts", [])
            year = dates[0][0] if dates and dates[0] else None
            title = record.get("title", [])
            licenses = [item["URL"] for item in record.get("license", []) if item.get("URL")]
            result.append(_item("Crossref", identifiers, title[0] if title else None, authors, year,
                                record.get("type"), record, "; ".join(licenses) or None))
        return tuple(result)


def resolved_match(records, requested: EvidenceIdentifier):
    matches = [record for record in records if requested.normalized_key in {item.normalized_key for item in record.identifiers}]
    if len(matches) != 1:
        raise ValueError("identifier lookup was missing or ambiguous")
    return matches[0]


def consolidate(records: tuple[EvidenceItem, ...]) -> tuple[EvidenceItem, ...]:
    """Consolidate connected identifier aliases without counting them independently."""
    groups = []
    for record in records:
        keys = {item.normalized_key for item in record.identifiers}
        matching = [group for group in groups if group[0] & keys]
        group_records = [record]
        for group in matching:
            keys.update(group[0])
            group_records.extend(group[1])
            groups.remove(group)
        groups.append((keys, group_records))
    merged = []
    for keys, group in groups:
        newest = max(group, key=lambda record: record.retrieved_at or datetime.min.replace(tzinfo=timezone.utc))
        identifiers = {identifier.normalized_key: identifier for record in group for identifier in record.identifiers}
        warnings = tuple(dict.fromkeys(warning for record in group for warning in record.limitations))
        if len({record.title.casefold() for record in group if record.title}) > 1:
            warnings += ("Provider titles disagree; inspect publication metadata before scientific use.",)
        merged.append(newest.model_copy(update={
            "identifiers": tuple(identifiers.values()),
            "source": "; ".join(sorted({record.source for record in group})), "limitations": warnings,
        }))
    return tuple(merged)
