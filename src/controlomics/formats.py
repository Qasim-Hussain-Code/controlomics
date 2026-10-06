"""Structural exports for workflow inputs; Python enforces relational gates."""

import json
from pathlib import Path


def export_workflow_schemas(directory: Path):
    from controlomics.evaluation import AnnotationSubmission, AnnotationRevision, EvaluationBundle, EvaluationDataset, PredictionRun
    from controlomics.artifacts import NetworkAuditEvent, ReviewManifest
    from controlomics.execution import ExecutionConfig, PairedSubmission
    from controlomics.models import DraftControl, Proposal
    from controlomics.reasoning import InterpretationDraft, NarrativeInput, ReasoningProfile
    from controlomics.workflow import CandidateSubmission, HumanReview, Intake, NewClaim
    models = (Intake, NewClaim, CandidateSubmission, HumanReview, DraftControl, Proposal,
        ExecutionConfig, NarrativeInput, InterpretationDraft, ReasoningProfile,
        EvaluationDataset, PredictionRun, EvaluationBundle, AnnotationSubmission, AnnotationRevision,
        NetworkAuditEvent, ReviewManifest, PairedSubmission)
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for model in models:
        path = directory / (model.__name__ + ".schema.json")
        path.write_text(json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        paths.append(path)
    return paths
