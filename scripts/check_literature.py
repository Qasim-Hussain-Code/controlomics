"""Optional live checks of public method identifiers; no research projects are sent."""

import argparse
import json
from pathlib import Path

from controlomics.evidence import Crossref, EuropePMC, consolidate, resolved_match
from controlomics.privacy import SafeTransport
from controlomics.schemas import EvidenceIdentifier


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-public-checks", action="store_true")
    args = parser.parse_args()
    if not args.run_public_checks:
        parser.error("the public identifier check must be explicitly enabled")
    transport = SafeTransport(frozenset({EuropePMC.host, Crossref.host}))
    providers = (EuropePMC(transport), Crossref(transport))
    records, checks = [], []
    # Public method DOIs, checked against provider responses before being used.
    for doi in ("10.1186/s13059-014-0550-8", "10.1186/1471-2105-7-91"):
        identifier = EvidenceIdentifier(namespace="DOI", value=doi, authority="doi.org")
        for provider in providers:
            prepared = provider.prepare_resolve(identifier)
            try:
                record = resolved_match(provider.search(prepared, prepared.approval_hash), identifier)
                records.append(record)
                checks.append({"provider": provider.__class__.__name__, "doi": doi, "status": "IDENTITY_VERIFIED", "title": record.title})
            except ValueError:
                checks.append({"provider": provider.__class__.__name__, "doi": doi, "status": "FAILED"})
    document = {"scope": "Public publication identity only; entailment and biological applicability were not reviewed.",
        "checks": checks, "evidence": [item.model_dump(mode="json") for item in consolidate(tuple(records))],
        "network_audit": transport.audit}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(checks, indent=2))
    return 0 if all(item["status"] == "IDENTITY_VERIFIED" for item in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
