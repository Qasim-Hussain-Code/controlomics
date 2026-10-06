"""Local workflows and separately approved external requests, with redacted errors."""

import argparse
import json
import os
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

from controlomics import __version__
from controlomics.evidence import Crossref, EuropePMC, resolved_match
from controlomics.execution import ExecutionConfig, build_package, execute_local, import_result
from controlomics.models import MessagesProvider
from controlomics.privacy import SafeField, SafeTransport
from controlomics.project import decode_json, export_json_schemas, load_project, save_project
from controlomics.reports import write_report
from controlomics.schemas import ControlResult, EvidenceIdentifier
from controlomics.workflow import HumanReview, Intake, apply_review, audit_project, import_evidence, new_project, propose, review_methods


def read_typed(path, model):
    with path.open("rb") as stream:
        content = stream.read(2 * 1024 * 1024 + 1)
    decode_json(content)
    return model.model_validate_json(content)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="controlomics")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Validate a local project")
    validate.add_argument("project", type=Path)
    schemas = commands.add_parser("export-schemas", help="Export versioned JSON Schemas")
    schemas.add_argument("directory", type=Path)
    create = commands.add_parser("new", help="Create a project from explicit scientific intake")
    create.add_argument("intake", type=Path)
    create.add_argument("--output", type=Path, required=True)
    analyze = commands.add_parser("analyze", help="Propose technical references, review, and audit")
    analyze.add_argument("project", type=Path)
    analyze.add_argument("--output", type=Path, required=True)
    report = commands.add_parser("report", help="Write a self-contained local scientific report")
    report.add_argument("project", type=Path)
    report.add_argument("--output", type=Path, required=True)
    report.add_argument("--network-audit", type=Path)
    review = commands.add_parser("review", help="Apply researcher-supplied source and context review")
    review.add_argument("project", type=Path)
    review.add_argument("review", type=Path)
    review.add_argument("--output", type=Path, required=True)
    retrieve = commands.add_parser("retrieve", help="Preview or approve a public literature request")
    retrieve.add_argument("project", type=Path)
    retrieve.add_argument("--provider", choices=("europepmc", "crossref"), default="europepmc")
    query = retrieve.add_mutually_exclusive_group(required=True)
    query.add_argument("--query")
    query.add_argument("--doi")
    query.add_argument("--pmid")
    retrieve.add_argument("--limit", type=int, default=5)
    retrieve.add_argument("--approve-hash")
    retrieve.add_argument("--output", type=Path, required=True)
    retrieve.add_argument("--audit-output", type=Path, required=True)
    model = commands.add_parser("model-propose", help="Preview minimized context before hosted reasoning")
    model.add_argument("project", type=Path)
    model.add_argument("--context", type=Path, required=True)
    model.add_argument("--endpoint", required=True)
    model.add_argument("--model", required=True)
    model.add_argument("--approve-hash")
    model.add_argument("--output", type=Path, required=True)
    model.add_argument("--audit-output", type=Path, required=True)
    for name in ("package", "execute"):
        command = commands.add_parser(name, help="Build or run a reviewed fixed numeric control")
        command.add_argument("project", type=Path)
        command.add_argument("--control-id", required=True)
        command.add_argument("--config", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
        if name == "package":
            command.add_argument("--directory", type=Path, required=True)
        else:
            command.add_argument("--input", type=Path, required=True)
    result = commands.add_parser("import-results", help="Import an execution-bound control result")
    result.add_argument("project", type=Path)
    result.add_argument("result", type=Path)
    result.add_argument("--output", type=Path, required=True)
    benchmark = commands.add_parser("benchmark", help="Run the labeled development benchmark")
    benchmark.add_argument("--output", type=Path, required=True)
    benchmark.add_argument("--trials", type=int, default=100)
    benchmark.add_argument("--seed", type=int, default=827)
    serve = commands.add_parser("serve", help="Start the local memory-only research interface")
    serve.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    try:
        if args.command == "serve":
            from controlomics.server import serve_local
            serve_local(args.port)
            return 0
        if args.command == "export-schemas":
            print(f"Exported {len(export_json_schemas(args.directory))} structural schemas. Use Python for relational checks.")
            return 0
        if args.command == "benchmark":
            from controlomics.benchmark import run_benchmark
            write_json(args.output, run_benchmark(args.trials, args.seed))
            print("Wrote development benchmark observations; scientific generalization remains unvalidated.")
            return 0
        if args.command == "new":
            save_project(new_project(read_typed(args.intake, Intake)), args.output)
            print("Created a local project from the supplied claim and category.")
            return 0
        project = load_project(args.project)
        if args.command == "validate":
            print("Project structure and references are valid. Scientific validity has not been established.")
            if any(claim.interpretation_warnings for claim in project.claims):
                print("Claim interpretation warning: computational support does not establish the stated causation.")
            return 0
        if args.command == "report":
            audit = decode_json(args.network_audit.read_bytes()) if args.network_audit else ()
            write_report(audit_project(project), args.output, audit)
            print("Wrote a local scientific report. Review its contents before sharing.")
            return 0
        if args.command == "analyze":
            updated = audit_project(review_methods(propose(project)))
        elif args.command == "review":
            updated = audit_project(apply_review(project, read_typed(args.review, HumanReview)))
        elif args.command in ("retrieve", "model-propose"):
            if args.command == "retrieve":
                cls = EuropePMC if args.provider == "europepmc" else Crossref
                transport = SafeTransport(frozenset({cls.host}))
                provider = cls(transport)
                identifier = None
                if args.query:
                    prepared = provider.prepare_search(args.query, args.limit)
                else:
                    identifier = EvidenceIdentifier(namespace="DOI" if args.doi else "PMID", value=args.doi or args.pmid,
                        authority="doi.org" if args.doi else "PubMed")
                    prepared = provider.prepare_resolve(identifier)
            else:
                context = decode_json(args.context.read_bytes())
                if not isinstance(context, dict):
                    raise ValueError("model context must be a named public-field object")
                fields = tuple(SafeField(name, value, "SAFE") for name, value in context.items())
                transport = SafeTransport(frozenset({urlsplit(args.endpoint).hostname}))
                provider = MessagesProvider(args.endpoint, args.model, transport, os.environ.get("CONTROLOMICS_MODEL_KEY"))
                prepared = provider.prepare(fields)
            if args.approve_hash != prepared.approval_hash:
                print(json.dumps({"request": prepared.preview(), "approve_hash": prepared.approval_hash}, indent=2))
                print("No request sent. Review the exact payload, then repeat with --approve-hash.")
                return 2
            try:
                if args.command == "retrieve":
                    records = provider.search(prepared, args.approve_hash)
                    if identifier:
                        records = (resolved_match(records, identifier),)
                    updated = import_evidence(project, records) if records else project
                else:
                    updated = propose(project, provider=provider, proposal=provider.complete(prepared, args.approve_hash))
            finally:
                write_json(args.audit_output, transport.audit)
            updated = audit_project(updated)
        elif args.command in ("package", "execute"):
            config = read_typed(args.config, ExecutionConfig)
            if args.command == "package":
                updated = build_package(project, args.control_id, config, args.directory)
            else:
                with args.input.open("rb") as stream:
                    raw = stream.read(2 * 1024 * 1024 + 1)
                updated = audit_project(execute_local(project, args.control_id, config, raw))
        else:
            updated = audit_project(import_result(project, read_typed(args.result, ControlResult)))
        save_project(updated, args.output)
        print("Wrote an updated local project. Evidence states and limitations remain explicit.")
    except (ValueError, OSError, RecursionError, KeyError, IndexError, TypeError, subprocess.TimeoutExpired):
        print("Operation failed. Input content, credentials, and local paths are omitted.")
        return 1
    except KeyboardInterrupt:
        return 0
    return 0
