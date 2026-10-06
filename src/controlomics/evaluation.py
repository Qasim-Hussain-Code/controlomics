"""Evaluation arithmetic for supplied reference annotations, not benchmark truth."""

from __future__ import annotations

import math
import json
from hashlib import sha256
from collections import Counter
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, model_validator

from controlomics import __version__
from controlomics.benchmark import wilson
from controlomics.schemas import (ControlClass, EvidenceIdentifier, Identifier, Probability,
    Record, ScientificLevel, Text, Sha256, LocalOnly)
from controlomics.workflow import Intake

Origin = Literal["UNASSESSED", "DEVELOPMENT_FIXTURE", "EXPERT_ATTESTATION"]
Partition = Literal["DEVELOPMENT", "VALIDATION", "TEST"]


class ReferenceControl(Record):
    reference_id: Identifier
    description: Text
    control_class: ControlClass
    essential: bool


class EvaluationCase(Record):
    case_id: Identifier
    description: Text
    partition: Partition
    source_group: Identifier
    intake: Intake | None = None
    source_identifiers: tuple[EvidenceIdentifier, ...] = ()
    references: tuple[ReferenceControl, ...] = ()
    expected_findings: tuple[Identifier, ...] | None = None

    @model_validator(mode="after")
    def unique_reference_ids(self):
        ids = [item.reference_id for item in self.references]
        if len(ids) != len(set(ids)) or self.expected_findings is not None and len(self.expected_findings) != len(set(self.expected_findings)):
            raise ValueError("case references and findings must be unique")
        return self


class EvaluationDataset(Record):
    format: Literal["controlomics.evaluation_dataset.v0.1"] = "controlomics.evaluation_dataset.v0.1"
    dataset_id: Identifier
    annotation_origin: Origin
    annotator: Text | None = None
    cases: Annotated[tuple[EvaluationCase, ...], Field(min_length=1, max_length=200)]
    limitations: Annotated[tuple[Text, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def partitions_and_origin(self):
        ids = [case.case_id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("benchmark case IDs must be unique")
        if self.annotation_origin == "EXPERT_ATTESTATION" and self.annotator is None:
            raise ValueError("expert annotations require an explicitly supplied annotator")
        groups, identifiers = {}, {}
        for case in self.cases:
            for value, registry in ((case.source_group, groups), *[(item.normalized_key, identifiers) for item in case.source_identifiers]):
                if value in registry and registry[value] != case.partition:
                    raise ValueError("a declared source group or publication crosses evaluation partitions")
                registry[value] = case.partition
        return self


class PredictedControl(Record):
    control_id: Identifier
    control_class: ControlClass
    scientific_level: ScientificLevel
    description: Text
    probability_appropriate: Probability | None = None


class CasePrediction(Record):
    case_id: Identifier
    controls: tuple[PredictedControl, ...]
    abstained: bool
    findings: tuple[Identifier, ...] = ()
    execution_states: tuple[Literal["COMPLETED", "FAILED", "BLOCKED", "NOT_RUN"], ...] = ()

    @model_validator(mode="after")
    def prediction_state(self):
        ids = [control.control_id for control in self.controls]
        if len(ids) != len(set(ids)) or len(self.findings) != len(set(self.findings)):
            raise ValueError("predictions and findings must be unique within a case")
        if self.abstained and self.controls:
            raise ValueError("a fully abstained case cannot contain recommendations")
        return self


class PredictionRun(Record):
    run_id: Identifier
    provider: Text
    cases: Annotated[tuple[CasePrediction, ...], Field(min_length=1)]
    limitations: Annotated[tuple[Text, ...], Field(min_length=1)]


class RecommendationJudgment(Record):
    case_id: Identifier
    control_id: Identifier
    appropriate: bool | None
    unsupported: bool | None
    matched_reference_ids: tuple[Identifier, ...] = ()
    rationale: Text

    @model_validator(mode="after")
    def reference_matches(self):
        if self.matched_reference_ids and self.appropriate is not True:
            raise ValueError("reference coverage requires an appropriate recommendation judgment")
        if len(self.matched_reference_ids) != len(set(self.matched_reference_ids)):
            raise ValueError("matched references must be unique")
        return self


class EvidenceDecision(Record):
    unit_id: Identifier
    case_id: Identifier
    layer: Literal["CITATION_IDENTITY", "STATEMENT_ENTAILMENT", "CONTEXT_COMPATIBILITY"]
    predicted_decision: bool
    reference_decision: bool | None
    rationale: Text


class EvaluationBundle(Record):
    format: Literal["controlomics.evaluation.v0.1"] = "controlomics.evaluation.v0.1"
    dataset: EvaluationDataset
    predictions: PredictionRun
    judgment_origin: Origin
    annotator: Text | None = None
    judgments: tuple[RecommendationJudgment, ...] = ()
    evidence_decisions: tuple[EvidenceDecision, ...] = ()

    @model_validator(mode="after")
    def references_and_judgments(self):
        cases = {case.case_id: case for case in self.dataset.cases}
        predictions = {case.case_id: case for case in self.predictions.cases}
        if len(predictions) != len(self.predictions.cases) or set(predictions) != set(cases):
            raise ValueError("predictions must cover each dataset case exactly once, including abstentions")
        controls = {(case.case_id, item.control_id) for case in predictions.values() for item in case.controls}
        judgments = set()
        for judgment in self.judgments:
            key = judgment.case_id, judgment.control_id
            if key not in controls or key in judgments:
                raise ValueError("judgments must reference unique predicted recommendations")
            judgments.add(key)
            references = {item.reference_id for item in cases[judgment.case_id].references}
            if not set(judgment.matched_reference_ids) <= references:
                raise ValueError("matched reference does not belong to the judged case")
            if self.judgment_origin == "UNASSESSED" and (judgment.appropriate is not None or judgment.unsupported is not None or judgment.matched_reference_ids):
                raise ValueError("unassessed sheets cannot contain asserted judgments")
        units = [(item.layer, item.unit_id) for item in self.evidence_decisions]
        if len(units) != len(set(units)) or any(item.case_id not in cases for item in self.evidence_decisions):
            raise ValueError("evidence decisions require unique units and known cases")
        if self.judgment_origin == "UNASSESSED" and any(item.reference_decision is not None for item in self.evidence_decisions):
            raise ValueError("unassessed sheets cannot assert evidence reference decisions")
        if self.judgment_origin == "EXPERT_ATTESTATION" and self.annotator is None:
            raise ValueError("expert judgments require an explicitly supplied annotator")
        return self


class AnnotationSubmission(Record):
    bundle_sha256: Sha256
    judgment_origin: Literal["DEVELOPMENT_FIXTURE", "EXPERT_ATTESTATION"]
    annotator: Text
    human_attested: bool
    judgments: tuple[RecommendationJudgment, ...]
    evidence_decisions: tuple[EvidenceDecision, ...]

    @model_validator(mode="after")
    def actual_reviewer(self):
        if not self.human_attested:
            raise ValueError("recording judgments requires an explicit human attestation")
        return self


class AnnotationRevision(Record):
    previous_sha256: Sha256
    updated_sha256: Sha256
    recorded_at: AwareDatetime
    judgment_origin: Literal["DEVELOPMENT_FIXTURE", "EXPERT_ATTESTATION"]
    annotator: Text
    human_attested: LocalOnly


def bundle_hash(bundle):
    from controlomics.privacy import canonical_json, digest
    return digest(canonical_json(bundle.model_dump(mode="json")))


def apply_annotations(bundle: EvaluationBundle, submission: AnnotationSubmission):
    if submission.bundle_sha256 != bundle_hash(bundle):
        raise ValueError("annotations target a different evaluation snapshot")
    before = {(item.layer, item.unit_id): (item.case_id, item.predicted_decision) for item in bundle.evidence_decisions}
    after = {(item.layer, item.unit_id): (item.case_id, item.predicted_decision) for item in submission.evidence_decisions}
    if before != after:
        raise ValueError("annotation cannot alter predicted evidence decisions")
    # Revalidation retains all case/reference/partition gates. Predictions and references are immutable here.
    value = bundle.model_dump(mode="json")
    value.update(judgment_origin=submission.judgment_origin, annotator=submission.annotator,
        judgments=[item.model_dump(mode="json") for item in submission.judgments],
        evidence_decisions=[item.model_dump(mode="json") for item in submission.evidence_decisions])
    updated = EvaluationBundle.model_validate_json(json.dumps(value))
    revision = AnnotationRevision(previous_sha256=bundle_hash(bundle), updated_sha256=bundle_hash(updated),
        recorded_at=datetime.now(timezone.utc), judgment_origin=submission.judgment_origin,
        annotator=submission.annotator, human_attested=True)
    return updated, revision


def ratio(numerator, denominator, definition):
    return {"numerator": numerator, "denominator": denominator,
        "value": numerator / denominator if denominator else None,
        "wilson_95_interval": wilson(numerator, denominator) if denominator else None,
        "definition": definition}


def evaluate(bundle: EvaluationBundle, partition: Partition | None = None):
    cases = {case.case_id: case for case in bundle.dataset.cases if partition is None or case.partition == partition}
    if not cases:
        raise ValueError("the selected partition has no cases")
    predictions = {case.case_id: case for case in bundle.predictions.cases if case.case_id in cases}
    judgments = {(item.case_id, item.control_id): item for item in bundle.judgments if item.case_id in cases}
    eligible = bundle.judgment_origin != "UNASSESSED"
    judged = [item for item in judgments.values() if item.appropriate is not None] if eligible else []
    unsupported = [item for item in judgments.values() if item.unsupported is not None] if eligible else []
    complete_cases = {identifier for identifier, prediction in predictions.items() if eligible and
        all((identifier, control.control_id) in judgments and judgments[identifier, control.control_id].appropriate is not None for control in prediction.controls)}
    coverage_known = complete_cases if bundle.dataset.annotation_origin != "UNASSESSED" else set()
    covered = {(item.case_id, identifier) for item in judged if item.appropriate and item.case_id in coverage_known for identifier in item.matched_reference_ids}
    references = {(case.case_id, item.reference_id) for case in cases.values() if case.case_id in coverage_known for item in case.references}
    essential = {(case.case_id, item.reference_id) for case in cases.values() if case.case_id in coverage_known for item in case.references if item.essential}
    tp = expected = reported = 0
    finding_cases = 0
    for identifier, case in cases.items():
        if case.expected_findings is not None and bundle.dataset.annotation_origin != "UNASSESSED":
            predicted = set(predictions[identifier].findings)
            reference = set(case.expected_findings)
            tp += len(predicted & reference); expected += len(reference); reported += len(predicted)
            finding_cases += 1
    states = [state for prediction in predictions.values() for state in prediction.execution_states]
    metrics = {
        "recommendation_precision": ratio(sum(item.appropriate for item in judged), len(judged), "Appropriate / recommendations with a definite appropriateness judgment; uncertain and missing judgments excluded."),
        "reference_control_recall": ratio(len(covered & references), len(references), "Distinct covered / reference controls, restricted to completely judged cases with supplied reference annotations; abstained cases remain in recall."),
        "critical_control_recall": ratio(len(covered & essential), len(essential), "Distinct covered essential / essential references in the same completely judged cases."),
        "unsupported_recommendation_rate": ratio(sum(item.unsupported for item in unsupported), len(unsupported), "Unsupported / recommendations with a definite unsupported judgment; unknowns excluded."),
        "flaw_detection_recall": ratio(tp, expected, "Matched / expected finding codes in cases with supplied finding annotations."),
        "flaw_detection_precision": ratio(tp, reported, "Matched / reported finding codes in those annotated cases."),
        "execution_success": ratio(states.count("COMPLETED"), states.count("COMPLETED") + states.count("FAILED"), "Completed / completed-or-failed attempts; BLOCKED and NOT_RUN excluded and counted separately."),
        "abstention_rate": ratio(sum(prediction.abstained for prediction in predictions.values()), len(cases), "Cases with no recommendations and explicit full abstention / selected cases."),
    }
    for layer in ("CITATION_IDENTITY", "STATEMENT_ENTAILMENT", "CONTEXT_COMPATIBILITY"):
        decisions = [item for item in bundle.evidence_decisions if item.case_id in cases and item.layer == layer and item.reference_decision is not None] if eligible else []
        metrics[layer.lower() + "_accuracy"] = ratio(sum(item.predicted_decision == item.reference_decision for item in decisions), len(decisions),
            "Correct predicted binary decisions / supplied definite reference decisions for this evidence layer.")
    probabilities = []
    for identifier, prediction in predictions.items():
        for control in prediction.controls:
            judgment = judgments.get((identifier, control.control_id))
            if eligible and judgment and judgment.appropriate is not None and control.probability_appropriate is not None:
                probabilities.append((control.probability_appropriate - int(judgment.appropriate)) ** 2)
    metrics["binary_quadratic_score"] = {"value": math.fsum(probabilities) / len(probabilities) if probabilities else None,
        "denominator": len(probabilities), "definition": "Mean squared error of supplied probability of appropriateness versus definite judgments, on the binary 0-to-1 convention. Lower is better; this alone is not calibration."}
    return {"format": "controlomics.evaluation_report.v0.1", "run_at": datetime.now(timezone.utc).isoformat(),
        "controlomics_version": __version__, "dataset_id": bundle.dataset.dataset_id, "run_id": bundle.predictions.run_id,
        "provider": bundle.predictions.provider, "partition": partition or "ALL",
        "reference_origin": bundle.dataset.annotation_origin, "judgment_origin": bundle.judgment_origin,
        "annotators": {"references": bundle.dataset.annotator, "judgments": bundle.annotator}, "metrics": metrics,
        "coverage": {"cases": len(cases), "recommendations": sum(len(item.controls) for item in predictions.values()),
            "appropriateness_assessed": len(judged), "unsupported_assessed": len(unsupported),
            "uncertain_or_missing_appropriateness": sum(len(item.controls) for item in predictions.values()) - len(judged),
            "completely_judged_cases": len(complete_cases), "reference_recall_cases": len(coverage_known),
            "finding_annotated_cases": finding_cases, "blocked_executions": states.count("BLOCKED"), "not_run": states.count("NOT_RUN")},
        "limitations": list(bundle.dataset.limitations + bundle.predictions.limitations) + [
            "Annotations and reviewer names are supplied attestations, not authenticated independent ground truth.",
            "Development fixture metrics do not establish scientific control quality or agent generalization.",
            "Wilson intervals are descriptive binomial summaries; correlated cases, controls, or sources require a separate inferential design.",
            "No absent, uncertain, or unassessed annotation was silently treated as a correct recommendation."]}


def annotation_template(dataset: EvaluationDataset, predictions: PredictionRun):
    return EvaluationBundle(dataset=dataset, predictions=predictions, judgment_origin="UNASSESSED",
        judgments=tuple(RecommendationJudgment(case_id=case.case_id, control_id=control.control_id,
            appropriate=None, unsupported=None, rationale="Unassessed. Supply a source-based judgment and its limitations.")
            for case in predictions.cases for control in case.controls))


def run_dataset(dataset: EvaluationDataset, reasoner="design"):
    from controlomics.models import DesignReasoner, MethodBaseline
    from controlomics.reasoning import describe_design
    from controlomics.workflow import new_project
    if reasoner not in ("design", "reference"):
        raise ValueError("the offline dataset runner supports design and reference baselines")
    provider = DesignReasoner() if reasoner == "design" else MethodBaseline()
    results = []
    for case in dataset.cases:
        if case.intake is None:
            raise ValueError("each runnable case needs explicit scientific intake")
        project = new_project(case.intake)
        proposal = provider.propose(project.analysis, project.claims[0])
        findings = [finding.code for finding in describe_design(project.analysis, project.claims[0]).findings]
        if reasoner == "reference":
            findings = [code for code in findings if code in ("sampling_unit_missing", "causal_overreach")]
        results.append(CasePrediction(case_id=case.case_id, abstained=not proposal.controls, findings=tuple(findings),
            controls=tuple(PredictedControl(control_id="prediction." + sha256(case.case_id.encode()).hexdigest()[:16] + "." + str(index),
                control_class=control.control_class, scientific_level=control.scientific_level, description=control.name)
                for index, control in enumerate(proposal.controls, 1))))
    return PredictionRun(run_id="run." + reasoner, provider=provider.identifier, cases=tuple(results),
        limitations=("Offline software development baseline; no hosted model or biological validation.",
            "Findings are provisional review questions. Reference-label agreement is not diagnosis accuracy.",
            "The reference ablation retains only explicit causal-support mismatch and missing-unit checks."))


def compare_annotations(first: EvaluationBundle, second: EvaluationBundle):
    if first.dataset != second.dataset or first.predictions != second.predictions:
        raise ValueError("paired annotation comparison requires the same dataset and predictions")
    if "UNASSESSED" in (first.judgment_origin, second.judgment_origin):
        raise ValueError("unassessed annotation sheets have no agreement measurement")
    left = {(item.case_id, item.control_id): item.appropriate for item in first.judgments}
    right = {(item.case_id, item.control_id): item.appropriate for item in second.judgments}
    paired = sorted(left.keys() & right.keys())
    count = len(paired)
    counts_left, counts_right = Counter(left[key] for key in paired), Counter(right[key] for key in paired)
    agreement = sum(left[key] == right[key] for key in paired) / count if count else None
    expected = sum(counts_left[label] * counts_right[label] for label in (True, False, None)) / count ** 2 if count else None
    kappa = (agreement - expected) / (1 - expected) if count and expected < 1 else None
    return {"paired_recommendations": count, "unpaired_recommendations": len(left.keys() | right.keys()) - count,
        "observed_agreement": agreement, "expected_marginal_agreement": expected, "cohen_kappa": kappa,
        "annotation_origins": [first.judgment_origin, second.judgment_origin], "annotators": [first.annotator, second.annotator],
        "limitations": ["UNCERTAIN is a nominal category; missing judgments are excluded rather than counted as agreement.",
            "Agreement is not correctness or authenticated independent expert review. Degenerate marginals produce no kappa."]}
