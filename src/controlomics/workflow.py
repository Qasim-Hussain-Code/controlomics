"""Local claim intake, conservative recommendations, reviews, and audit snapshots."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import Field

from controlomics import __version__
from controlomics.evidence import consolidate
from controlomics.models import DesignReasoner, DraftControl, ModelProvider
from controlomics.reasoning import describe_design
from controlomics.privacy import canonical_json, digest
from controlomics.project import parse_project_json
from controlomics.schemas import (
    AnalysisContext, AnalyticalDesign, AuditOutcome, BiologicalContext, ClaimCategory,
    ContextCompatibility, ContextComparison, ControlCandidate, ControlomicsProject,
    EvidenceLink, PrivacyPolicy, PrivacyRequirements, ProjectManifest, ProvenanceRecord,
    Identifier, ModelProvenance, Record, ScientificClaim, Sha256, Text, VerificationRecord, VerifiedControl,
)


def now():
    return datetime.now(timezone.utc)


def replace_project(project, **updates):
    return parse_project_json(project.model_copy(update=updates).model_dump_json())


def event(action, ids, **kwargs):
    return ProvenanceRecord(provenance_id="provenance." + uuid.uuid4().hex,
                            action=action, recorded_at=now(), controlomics_version=__version__,
                            record_ids=tuple(ids), **kwargs)


class Intake(Record):
    question: Text
    analysis_description: Text
    methods: Annotated[tuple[Text, ...], Field(min_length=1)]
    observed_result: Text
    claim: Text
    claim_category: ClaimCategory
    computational_support: ClaimCategory
    biological_context: BiologicalContext = Field(default_factory=BiologicalContext)
    design: AnalyticalDesign = Field(default_factory=AnalyticalDesign)
    assumptions: tuple[Text, ...] = ()


def new_project(intake: Intake):
    suffix = uuid.uuid4().hex[:16]
    analysis_id, claim_id = "analysis." + suffix, "claim." + suffix
    return ControlomicsProject(
        manifest=ProjectManifest(project_id="project." + suffix, created_at=now(), controlomics_version=__version__),
        analysis=AnalysisContext(analysis_id=analysis_id, scientific_question=intake.question,
            analysis_description=intake.analysis_description, methods=intake.methods,
            biological_context=intake.biological_context, design=intake.design, observed_result=intake.observed_result),
        claims=(ScientificClaim(claim_id=claim_id, analysis_id=analysis_id, statement=intake.claim,
            category=intake.claim_category, computational_support=intake.computational_support,
            assumptions=intake.assumptions, origin="RESEARCHER"),),
        privacy=PrivacyPolicy(rationale="Researcher descriptions remain local; outbound fields require separate explicit review."),
        provenance=(),
    )


def propose(project, provider: ModelProvider | None = None, proposal=None, claim_id=None):
    provider = provider or DesignReasoner()
    if proposal is not None and claim_id is None and len(project.claims) > 1:
        raise ValueError("a hosted proposal must target one explicitly selected claim")
    selected = [claim for claim in project.claims if claim_id is None or claim.claim_id == claim_id]
    if not selected:
        raise ValueError("unknown proposal claim")
    candidates = list(project.candidates)
    added = []
    for claim in selected:
        if proposal is None and any(item.claim_tested == claim.claim_id for item in project.candidates + project.controls):
            continue
        result = proposal if proposal is not None else provider.propose(project.analysis, claim)
        for draft in result.controls:
            candidate = ControlCandidate(
                control_id="control." + uuid.uuid4().hex, control_name=draft.name,
                control_class=draft.control_class, scientific_level=draft.scientific_level,
                analysis_context=project.analysis.analysis_id, claim_tested=claim.claim_id,
                scientific_rationale=draft.rationale, expected_behavior=draft.expected_behavior,
                failure_interpretation=draft.failure_interpretation, evidence_required=draft.evidence_required,
                privacy_requirements=PrivacyRequirements(classification=project.privacy.classification,
                    rationale="Descriptions and input data remain local."),
                priority=draft.priority, priority_rationale=draft.priority_rationale,
                method_basis=draft.method_basis, uncertainties=draft.uncertainties + result.abstentions,
                limitations=draft.limitations,
            )
            candidates.append(candidate)
            added.append(candidate.control_id)
    if not added and proposal is None:
        return project
    ids = tuple(added) or tuple(item.claim_id for item in selected)
    model = None
    if proposal is not None and hasattr(provider, "endpoint"):
        from urllib.parse import urlsplit
        from controlomics.models import model_policy
        model = ModelProvenance(provider=urlsplit(provider.endpoint).hostname, model_identifier=provider.identifier,
                                prompt_template_sha256=digest(model_policy().encode()))
    return replace_project(project, candidates=tuple(candidates), provenance=project.provenance + (
        event("CLAIM_REVIEW", ids, model=model, warnings=("Proposal provider: " + provider.identifier, "Candidate generation does not establish evidence support.")),
    ))


def review_methods(project, control_ids=None):
    selected = set(control_ids) if control_ids is not None else None
    if selected is not None and not selected <= {item.control_id for item in project.candidates}:
        raise ValueError("method review must target known candidates")
    remaining, reviewed = [], list(project.controls)
    for candidate in project.candidates:
        if (selected is not None and candidate.control_id not in selected) or candidate.evidence_required or candidate.method_basis is None or candidate.scientific_level not in ("TECHNICAL", "STATISTICAL"):
            remaining.append(candidate)
            continue
        data = candidate.model_dump()
        data.update(evidence_status="METHOD_BASED", verification=VerificationRecord(
            reviewer_kind="PROGRAMMATIC", reviewer="controlomics.method_gate",
            method="Checked that this technical or statistical specification states a method basis and does not require biological evidence. Applicability and performance remain unvalidated.",
            checked_at=now(), limitations=("This is specification review, not empirical validation.",)))
        reviewed.append(VerifiedControl(**data))
    newly_reviewed = reviewed[len(project.controls):]
    events = (event("CONTROL_REVIEW", [item.control_id for item in newly_reviewed]),) if newly_reviewed else ()
    return replace_project(project, candidates=tuple(remaining), controls=tuple(reviewed), provenance=project.provenance + events)


def import_evidence(project, records):
    originals = project.evidence + tuple(records)
    merged = consolidate(originals)
    # An existing identity snapshot anchors prior entailment receipts. A later
    # retrieval must not move that prerequisite after the earlier human review.
    stable = []
    for item in merged:
        keys = {identifier.normalized_key for identifier in item.identifiers}
        matches = [old for old in project.evidence if old.existence_status == "VERIFIED" and
            keys & {identifier.normalized_key for identifier in old.identifiers}]
        existing = min(matches, key=lambda old: old.existence_check.checked_at) if matches else None
        stable.append(existing.model_copy(update={"identifiers": item.identifiers, "source": item.source,
            "limitations": tuple(dict.fromkeys(existing.limitations + item.limitations +
                ("The retained identity snapshot anchors earlier reviews; repeat retrieval does not authenticate them.",)))}) if existing else item)
    merged = tuple(stable)
    aliases = {}
    for old in originals:
        keys = {identifier.normalized_key for identifier in old.identifiers}
        match = next(item for item in merged if keys & {identifier.normalized_key for identifier in item.identifiers})
        aliases[old.evidence_id] = match.evidence_id
    def rewrite(control):
        return control.model_copy(update={"supporting_evidence": tuple(
            link.model_copy(update={"evidence_id": aliases[link.evidence_id]}) for link in control.supporting_evidence)})
    return replace_project(project, evidence=merged,
        candidates=tuple(rewrite(item) for item in project.candidates),
        controls=tuple(rewrite(item) for item in project.controls),
        audits=tuple(item.model_copy(update={"evidence_ids": tuple(dict.fromkeys(aliases[value] for value in item.evidence_ids))}) for item in project.audits),
        provenance=tuple(item.model_copy(update={"record_ids": tuple(dict.fromkeys(aliases.get(value, value) for value in item.record_ids))}) for item in project.provenance) +
                   (event("EVIDENCE_REVIEW", [item.evidence_id for item in merged]),),
    )


def compare_context(analysis: BiologicalContext, evidence: BiologicalContext, dimensions=None):
    dimensions = dimensions or tuple(name for name in BiologicalContext.model_fields if name != "schema_version")
    comparisons = []
    for name in dimensions:
        if name not in BiologicalContext.model_fields or name == "schema_version":
            raise ValueError("unknown context dimension")
        left, right = getattr(analysis, name), getattr(evidence, name)
        if isinstance(left, tuple):
            left, right = "; ".join(left) or None, "; ".join(right) or None
        status = "UNKNOWN"
        if left and right:
            status = "MATCH" if " ".join(left.casefold().split()) == " ".join(right.casefold().split()) else "MISMATCH"
        elif left is None and right is None:
            continue
        comparisons.append(ContextComparison(dimension=name, analysis_value=left, evidence_value=right,
            status=status, rationale="Exact normalized text comparison; semantic aliases and relevance require researcher review."))
    states = {item.status for item in comparisons}
    status = "MISMATCH" if "MISMATCH" in states else "PARTIAL" if states == {"MATCH", "UNKNOWN"} else "MATCH" if states == {"MATCH"} else "UNKNOWN"
    return ContextCompatibility(status=status, comparisons=tuple(comparisons),
        rationale="Compared all supplied dimensions; missing values were not treated as matches.",
        limitations=("Some supplied context dimensions could not be compared.",) if status in ("PARTIAL", "UNKNOWN") else ())


class StatementReview(Record):
    evidence_id: Text
    statement: Text
    relationship: Literal["SUPPORTS", "CONTRADICTS", "UNCERTAIN"]
    source_text: Text
    excerpt: Annotated[str, Field(min_length=1, max_length=300)]
    locator: Text
    rationale: Text
    source_context: BiologicalContext


class HumanReview(Record):
    control_id: Text
    reviewer: Text
    statements: Annotated[tuple[StatementReview, ...], Field(min_length=1)]
    limitations: Annotated[tuple[Text, ...], Field(min_length=1)]
    supersedes_review_sha256: Sha256 | None = None


class NewClaim(Record):
    statement: Text
    category: ClaimCategory
    computational_support: ClaimCategory
    assumptions: tuple[Text, ...] = ()


def add_claim(project, submission: NewClaim):
    claim = ScientificClaim(claim_id="claim." + uuid.uuid4().hex, analysis_id=project.analysis.analysis_id,
        statement=submission.statement, category=submission.category, computational_support=submission.computational_support,
        assumptions=submission.assumptions, origin="RESEARCHER")
    return replace_project(project, claims=project.claims + (claim,), provenance=project.provenance + (
        event("CLAIM_REVIEW", [claim.claim_id], warnings=("Added an explicit researcher statement; scientific support remains unreviewed.",)),))


class CandidateSubmission(Record):
    claim_id: Identifier
    control: DraftControl
    control_id: Identifier | None = None


def specify_candidate(project, submission: CandidateSubmission):
    if submission.claim_id not in {claim.claim_id for claim in project.claims}:
        raise ValueError("control must target a known claim")
    previous = next((item for item in project.candidates if item.control_id == submission.control_id), None)
    if submission.control_id and previous is None:
        raise ValueError("only unreviewed candidates can be edited; retain a separate snapshot for revised reviewed specifications")
    if previous and any(item.control_id == previous.control_id for item in project.execution_plans):
        raise ValueError("an execution-bound specification cannot be edited")
    draft = submission.control
    control = ControlCandidate(control_id=previous.control_id if previous else "control." + uuid.uuid4().hex,
        control_name=draft.name, control_class=draft.control_class, scientific_level=draft.scientific_level,
        analysis_context=project.analysis.analysis_id, claim_tested=submission.claim_id,
        scientific_rationale=draft.rationale, expected_behavior=draft.expected_behavior,
        failure_interpretation=draft.failure_interpretation, evidence_required=draft.evidence_required,
        method_basis=draft.method_basis, priority=draft.priority, priority_rationale=draft.priority_rationale,
        uncertainties=draft.uncertainties, limitations=draft.limitations, evidence_status="UNVERIFIED",
        privacy_requirements=PrivacyRequirements(classification=project.privacy.classification,
            rationale="Researcher-authored control specification remains local."))
    warnings = ("Unreviewed researcher-authored specification; no evidence state was promoted.",)
    if previous:
        warnings += ("Superseded candidate snapshot sha256: " + digest(canonical_json(previous.model_dump(mode="json"))),)
    return replace_project(project, candidates=tuple(item for item in project.candidates if item.control_id != control.control_id) + (control,),
        provenance=project.provenance + (event("CONTROL_REVIEW", [control.control_id], warnings=warnings),))


def review_template(project, control_id):
    control = next((item for item in project.candidates + project.controls if item.control_id == control_id), None)
    if control is None:
        raise ValueError("unknown review control")
    return {"control_id": control_id, "statements": [control.scientific_rationale, control.expected_behavior],
        "supersedes_review_sha256": digest(canonical_json(control.model_dump(mode="json"))) if isinstance(control, VerifiedControl) else None,
        "context_fields": [name for name in BiologicalContext.model_fields if name != "schema_version"]}


def apply_review(project, review: HumanReview):
    candidate = next((item for item in project.candidates + project.controls if item.control_id == review.control_id), None)
    if candidate is None:
        raise ValueError("human review must reference a known control")
    if isinstance(candidate, VerifiedControl):
        expected = digest(canonical_json(candidate.model_dump(mode="json")))
        if review.supersedes_review_sha256 != expected:
            raise ValueError("re-review requires explicit approval of the current reviewed snapshot")
    elif review.supersedes_review_sha256 is not None:
        raise ValueError("an unreviewed candidate has no review to supersede")
    identities = {item.evidence_id: item for item in project.evidence}
    links, contexts = [], []
    for item in review.statements:
        evidence = identities.get(item.evidence_id)
        if evidence is None or evidence.existence_status != "VERIFIED":
            raise ValueError("human review requires independently retrieved publication identity")
        if item.excerpt not in item.source_text:
            raise ValueError("review excerpt does not occur in the supplied source text")
        if item.statement not in (candidate.scientific_rationale, candidate.expected_behavior):
            raise ValueError("review must address the exact rationale or expected behavior")
        receipt = VerificationRecord(reviewer_kind="HUMAN", reviewer=review.reviewer,
            method="Human entailment attestation from locally supplied source text; software checked excerpt presence only.",
            checked_at=now(), artifact_sha256=digest(item.source_text.encode()), limitations=review.limitations)
        links.append(EvidenceLink(evidence_id=item.evidence_id, statement=item.statement, relationship=item.relationship,
            locator=item.locator, rationale=item.rationale, entailment_check=receipt))
        contexts.append(compare_context(project.analysis.biological_context, item.source_context))
    statuses = {item.status for item in contexts}
    compatibility = next((item for item in contexts if item.status == "MISMATCH"), contexts[0])
    if len(statuses) > 1 and "MISMATCH" not in statuses:
        compatibility = next((item for item in contexts if item.status in ("UNKNOWN", "PARTIAL")), compatibility)
    supported = {item.statement for item in links if item.relationship == "SUPPORTS"}
    contradicted = any(item.relationship == "CONTRADICTS" for item in links)
    complete = {candidate.scientific_rationale, candidate.expected_behavior} <= supported
    if supported and contradicted:
        status = "CONFLICTING_EVIDENCE"
    elif complete and not contradicted and compatibility.status == "MATCH":
        status = "EVIDENCE_BACKED"
    else:
        status = "INSUFFICIENT_EVIDENCE"
    data = candidate.model_dump()
    data.update(supporting_evidence=tuple(links), context_compatibility=compatibility, evidence_status=status,
        verification=VerificationRecord(reviewer_kind="HUMAN", reviewer=review.reviewer,
            method="Researcher-submitted statement review and deterministic evidence/context gate.", checked_at=now(), limitations=review.limitations),
        limitations=candidate.limitations + review.limitations)
    control = VerifiedControl(**data)
    return replace_project(project, candidates=tuple(item for item in project.candidates if item.control_id != candidate.control_id),
        controls=tuple(item for item in project.controls if item.control_id != candidate.control_id) + (control,),
        provenance=project.provenance + (event("CONTROL_REVIEW", [control.control_id],
            warnings=("Superseded reviewed snapshot sha256: " + review.supersedes_review_sha256,) if review.supersedes_review_sha256 else ()),))


def audit_project(project):
    audits = []
    for claim in project.claims:
        controls = [item for item in project.candidates + project.controls if item.claim_tested == claim.claim_id]
        result_ids = tuple(item.result_id for item in project.results if any(control.control_id == item.control_id for control in controls))
        failures = [item for item in project.results if item.result_id in result_ids and item.outcome == "FAIL"]
        uncertainties = list(claim.interpretation_warnings)
        if not {"POSITIVE", "NEGATIVE"} <= {item.control_class for item in controls}:
            uncertainties.append("At least one primary control class is missing.")
        if not project.analysis.design.sampling_unit:
            uncertainties.append("The independent sampling unit is unspecified; dependence and pseudoreplication require review.")
        if not any(item.evidence_status == "EVIDENCE_BACKED" and item.scientific_level in ("BIOLOGICAL", "MECHANISTIC") for item in controls):
            uncertainties.append("No biological recommendation has completed the evidence gate.")
        for control in controls:
            if control.context_compatibility.status in ("MISMATCH", "UNKNOWN", "PARTIAL"):
                uncertainties.append("Context applicability remains limited for control " + control.control_id + ".")
        profile = describe_design(project.analysis, claim)
        uncertainties.extend(finding.message for finding in profile.findings)
        assessment = "CONTROL_FAILURE" if failures else "INSUFFICIENT_EVIDENCE"
        audits.append(AuditOutcome(audit_id="audit." + uuid.uuid4().hex, claim_id=claim.claim_id,
            assessment=assessment, rationale="The recorded controls and evidence do not establish the full biological claim. " +
                ("A specified technical control failed and requires investigation." if failures else "Further scientific review and applicable controls are required."),
            result_ids=result_ids, evidence_ids=tuple(item.evidence_id for item in project.evidence),
            reviewer=VerificationRecord(reviewer_kind="PROGRAMMATIC", reviewer="controlomics.conservative_audit",
                method="Rule-based checks for absent control classes, causal overstatement, missing sampling units, context uncertainty, and recorded failures.", checked_at=now()),
            uncertainties=tuple(dict.fromkeys(uncertainties)),
            limitations=("This audit is a conservative software assessment, not expert adjudication or a demonstration of generalization.",)))
    return replace_project(project, audits=tuple(audits), provenance=tuple(
        item for item in project.provenance if item.action != "AUDIT") + (event("AUDIT", [item.audit_id for item in audits],
            warnings=("Design diagnostics: design_rules.v0.1; heuristic findings require researcher interpretation.",)),))
