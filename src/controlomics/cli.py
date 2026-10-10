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
from controlomics.models import MessagesProvider, MethodBaseline
from controlomics.reasoning import NarrativeInput, describe_design, interpret_narrative
from controlomics.privacy import SafeField, SafeTransport
from controlomics.project import decode_json, export_json_schemas, load_project, save_project
from controlomics.reports import write_report
from controlomics.schemas import ControlResult, EvidenceIdentifier
from controlomics.storage import require_distinct_outputs, write_bytes_atomic, write_text_atomic
from controlomics.workflow import (CandidateSubmission, HumanReview, Intake, NewClaim, add_claim, apply_review,
    audit_project, import_evidence, new_project, propose, review_methods, specify_candidate)


def read_typed(path, model):
    with path.open("rb") as stream:
        content = stream.read(2 * 1024 * 1024 + 1)
    decode_json(content)
    return model.model_validate_json(content)


def read_json(path):
    with path.open("rb") as stream:
        return decode_json(stream.read(2 * 1024 * 1024 + 1))


def write_json(path, value):
    write_text_atomic(path, json.dumps(value, indent=2, allow_nan=False) + "\n")


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
    analyze.add_argument("--reasoner", choices=("design", "reference"), default="design")
    interpret = commands.add_parser("interpret", help="Draft local intake fields for researcher confirmation")
    interpret.add_argument("description", type=Path)
    interpret.add_argument("--output", type=Path, required=True)
    dataset_run = commands.add_parser("run-dataset", help="Run an offline benchmark baseline on explicit cases")
    dataset_run.add_argument("dataset", type=Path)
    dataset_run.add_argument("--reasoner", choices=("design", "reference"), default="design")
    dataset_run.add_argument("--output", type=Path, required=True)
    annotation = commands.add_parser("annotation-template", help="Prepare an unassessed judgment sheet")
    annotation.add_argument("dataset", type=Path)
    annotation.add_argument("predictions", type=Path)
    annotation.add_argument("--output", type=Path, required=True)
    evaluation = commands.add_parser("evaluate", help="Compute metrics from supplied reference annotations")
    evaluation.add_argument("bundle", type=Path)
    evaluation.add_argument("--partition", choices=("DEVELOPMENT", "VALIDATION", "TEST"))
    evaluation.add_argument("--output", type=Path, required=True)
    agreement = commands.add_parser("compare-annotations", help="Compare paired supplied annotation sheets")
    agreement.add_argument("first", type=Path)
    agreement.add_argument("second", type=Path)
    agreement.add_argument("--output", type=Path, required=True)
    design = commands.add_parser("design", help="Export inspectable local design cues and questions")
    design.add_argument("project", type=Path)
    design.add_argument("--output", type=Path, required=True)
    for name in ("add-claim", "specify-control", "specify-paired"):
        command = commands.add_parser(name, help="Add an explicit local scientific specification")
        command.add_argument("project", type=Path)
        command.add_argument("submission", type=Path)
        command.add_argument("--output", type=Path, required=True)
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
    model.add_argument("--claim-id")
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
    inspect_input = commands.add_parser("inspect-input", help="Check a bounded local CSV without executing a control")
    inspect_input.add_argument("input", type=Path)
    inspect_input.add_argument("--adapter", choices=("INDEPENDENT_REFERENCE", "PAIRED_DIFFERENCE"), default="INDEPENDENT_REFERENCE")
    inspect_input.add_argument("--output", type=Path, required=True)
    benchmark = commands.add_parser("benchmark", help="Run the labeled development benchmark")
    benchmark.add_argument("--output", type=Path, required=True)
    benchmark.add_argument("--trials", type=int, default=100)
    benchmark.add_argument("--seed", type=int, default=827)
    serve = commands.add_parser("serve", help="Start the local memory-only research interface")
    serve.add_argument("--port", type=int, default=8765)
    bundle_export = commands.add_parser("bundle-export", help="Save a bounded local review archive")
    bundle_export.add_argument("project", type=Path)
    bundle_export.add_argument("--network-audit", type=Path)
    bundle_export.add_argument("--evaluation", type=Path)
    bundle_export.add_argument("--revisions", type=Path)
    bundle_export.add_argument("--output", type=Path, required=True)
    bundle_import = commands.add_parser("bundle-import", help="Validate a review archive and write known local records")
    bundle_import.add_argument("archive", type=Path)
    bundle_import.add_argument("--directory", type=Path, required=True)
    annotate = commands.add_parser("annotate", help="Apply researcher-supplied judgments to an exact evaluation snapshot")
    annotate.add_argument("bundle", type=Path)
    annotate.add_argument("submission", type=Path)
    annotate.add_argument("--output", type=Path, required=True)
    annotate.add_argument("--revision-output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command in ("retrieve", "model-propose"):
            require_distinct_outputs(args.output, args.audit_output)
            require_distinct_outputs(args.project, args.audit_output)
            if args.command == "model-propose":
                require_distinct_outputs(args.context, args.audit_output)
        elif args.command == "annotate":
            require_distinct_outputs(args.output, args.revision_output)
            require_distinct_outputs(args.bundle, args.revision_output)
            require_distinct_outputs(args.submission, args.revision_output)
        elif args.command == "package":
            for name in ("config.json", "execution_plan.json", "control.json", "result.schema.json", "environment.json", "run_control.py", "stats.py", "verify_results.py", "manifest.json", "README.md"):
                require_distinct_outputs(args.output, args.directory / name)
        if args.command == "inspect-input":
            from controlomics.inputs import MAX_INPUT, inspect_numeric_input
            with args.input.open("rb") as stream:
                raw = stream.read(MAX_INPUT + 1)
            write_json(args.output, inspect_numeric_input(raw, args.adapter).model_dump(mode="json"))
            print("Saved input dimensions and the exact byte hash. No control was executed or scientific validity assigned.")
            return 0
        if args.command == "specify-paired":
            from controlomics.execution import PairedSubmission, specify_paired_control
            submission = read_typed(args.submission, PairedSubmission)
            project = specify_paired_control(load_project(args.project), submission.claim_id, submission.rationale, submission.assumptions)
            save_project(audit_project(project), args.output)
            print("Specified a complete-pair statistical control; applicability remains researcher-supplied.")
            return 0
        if args.command == "annotate":
            from controlomics.evaluation import AnnotationSubmission, EvaluationBundle, apply_annotations
            updated, revision = apply_annotations(read_typed(args.bundle, EvaluationBundle), read_typed(args.submission, AnnotationSubmission))
            write_json(args.output, updated.model_dump(mode="json"))
            write_json(args.revision_output, revision.model_dump(mode="json"))
            print("Saved supplied annotation judgments and their revision hashes. Identities are not authenticated.")
            return 0
        if args.command == "bundle-export":
            from controlomics.artifacts import create_review_bundle
            from controlomics.evaluation import EvaluationBundle
            content = create_review_bundle(load_project(args.project), read_json(args.network_audit) if args.network_audit else (),
                read_typed(args.evaluation, EvaluationBundle) if args.evaluation else None, read_json(args.revisions) if args.revisions else ())
            write_bytes_atomic(args.output, content)
            print("Saved a local review archive. Review project descriptions and public query text before sharing.")
            return 0
        if args.command == "bundle-import":
            from controlomics.artifacts import MAX_ARCHIVE, open_review_bundle
            with args.archive.open("rb") as stream:
                project, ledger, evaluation, revisions, manifest = open_review_bundle(stream.read(MAX_ARCHIVE + 1))
            if args.directory.exists() and any(args.directory.iterdir()):
                raise ValueError("review import directory must be new or empty")
            args.directory.mkdir(parents=True, exist_ok=True)
            save_project(project, args.directory / "project.json")
            write_json(args.directory / "network_audit.json", ledger)
            write_json(args.directory / "manifest.json", manifest.model_dump(mode="json"))
            write_report(project, args.directory / "report.html", ledger)
            if evaluation is not None:
                write_json(args.directory / "evaluation.json", evaluation.model_dump(mode="json"))
                write_json(args.directory / "annotation_revisions.json", revisions)
            print("Validated review records and regenerated the local report. Hashes are not authenticated provenance.")
            return 0
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
        if args.command in ("run-dataset", "annotation-template", "evaluate", "compare-annotations"):
            from controlomics.evaluation import (EvaluationBundle, EvaluationDataset, PredictionRun,
                annotation_template, compare_annotations, evaluate, run_dataset)
            if args.command == "run-dataset":
                value = run_dataset(read_typed(args.dataset, EvaluationDataset), args.reasoner).model_dump(mode="json")
            elif args.command == "annotation-template":
                value = annotation_template(read_typed(args.dataset, EvaluationDataset), read_typed(args.predictions, PredictionRun)).model_dump(mode="json")
            elif args.command == "evaluate":
                value = evaluate(read_typed(args.bundle, EvaluationBundle), args.partition)
            else:
                value = compare_annotations(read_typed(args.first, EvaluationBundle), read_typed(args.second, EvaluationBundle))
            write_json(args.output, value)
            print("Wrote local evaluation records. Supplied annotations are not authenticated independent validation.")
            return 0
        if args.command == "interpret":
            with args.description.open("rb") as stream:
                content = stream.read(12001)
            if len(content) > 12000:
                raise ValueError("description exceeds the local UTF-8 byte budget")
            draft = interpret_narrative(NarrativeInput(description=content.decode("utf-8")))
            write_json(args.output, draft.model_dump(mode="json"))
            print("Wrote provisional local fields. Researcher confirmation is required; no request was sent.")
            return 0
        project = load_project(args.project)
        if args.command == "design":
            write_json(args.output, [{"claim_id": claim.claim_id, **describe_design(project.analysis, claim).model_dump(mode="json")} for claim in project.claims])
            print("Wrote heuristic design cues and review questions; scientific validity remains unestablished.")
            return 0
        if args.command == "validate":
            print("Project structure and references are valid. Scientific validity has not been established.")
            if any(claim.interpretation_warnings for claim in project.claims):
                print("Claim interpretation warning: computational support does not establish the stated causation.")
            return 0
        if args.command == "report":
            audit = read_json(args.network_audit) if args.network_audit else ()
            write_report(audit_project(project), args.output, audit)
            print("Wrote a local scientific report. Review its contents before sharing.")
            return 0
        if args.command == "analyze":
            updated = audit_project(review_methods(propose(project, MethodBaseline() if args.reasoner == "reference" else None)))
        elif args.command == "add-claim":
            updated = audit_project(review_methods(propose(add_claim(project, read_typed(args.submission, NewClaim)))))
        elif args.command == "specify-control":
            updated = audit_project(specify_candidate(project, read_typed(args.submission, CandidateSubmission)))
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
                if (args.claim_id is None and len(project.claims) > 1) or (args.claim_id is not None and args.claim_id not in {claim.claim_id for claim in project.claims}):
                    raise ValueError("select one known claim before hosted reasoning")
                context = read_json(args.context)
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
                    updated = propose(project, provider=provider, proposal=provider.complete(prepared, args.approve_hash), claim_id=args.claim_id)
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
