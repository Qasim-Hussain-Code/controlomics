"""Typed records and consistency checks, not independent scientific verification."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

Text = Annotated[str, StringConstraints(min_length=1, max_length=12000, pattern=r"\S")]
Identifier = Annotated[
    str, StringConstraints(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:]*$")
]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
Number = Annotated[float, Field(allow_inf_nan=False)]
Probability = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
PrivacyClass = Literal["SAFE", "SENSITIVE_SCIENTIFIC", "RESTRICTED"]
ControlClass = Literal[
    "POSITIVE", "NEGATIVE", "NULL", "SPECIFICITY", "ROBUSTNESS", "CONFOUNDER", "FALSIFICATION"
]
ScientificLevel = Literal["TECHNICAL", "STATISTICAL", "BIOLOGICAL", "MECHANISTIC"]
ClaimCategory = Literal[
    "DESCRIPTIVE", "ASSOCIATIONAL", "COMPARATIVE", "PREDICTIVE", "STATISTICAL",
    "FUNCTIONAL", "MECHANISTIC", "CAUSAL",
]
EvidenceStatus = Literal[
    "EVIDENCE_BACKED", "METHOD_BASED", "AGENT_PROPOSED", "UNVERIFIED",
    "CONFLICTING_EVIDENCE", "INSUFFICIENT_EVIDENCE",
]
ExecutionStatus = Literal["NOT_RUN", "PLANNED", "RUNNING", "COMPLETED", "FAILED", "BLOCKED"]
PRIVACY_RANK = {"SAFE": 0, "SENSITIVE_SCIENTIFIC": 1, "RESTRICTED": 2}


def _require_bool(value):
    if type(value) is not bool:
        raise ValueError("privacy flags require a boolean")
    return value


LocalOnly = Annotated[Literal[True], BeforeValidator(_require_bool)]
Disabled = Annotated[Literal[False], BeforeValidator(_require_bool)]


class Record(BaseModel):
    model_config = ConfigDict(
        extra="forbid", strict=True, frozen=True, validate_default=True,
        revalidate_instances="always", hide_input_in_errors=True,
    )
    schema_version: Literal["0.1.0"] = "0.1.0"


class BiologicalContext(Record):
    """Unknown dimensions remain absent rather than being inferred as matches."""

    organism: Text | None = None
    strain: Text | None = None
    cell_type: Text | None = None
    tissue: Text | None = None
    disease_state: Text | None = None
    experimental_condition: Text | None = None
    molecular_target: Text | None = None
    assay_type: Text | None = None
    computational_method: Text | None = None
    data_modality: Text | None = None
    biological_scale: Text | None = None
    intervention: Text | None = None
    time_point: Text | None = None
    reference_database: Text | None = None
    software_assumptions: tuple[Text, ...] = ()


class AnalyticalDesign(Record):
    sampling_unit: Text | None = None
    independence_assumptions: tuple[Text, ...] = ()
    contrasts: tuple[Text, ...] = ()
    covariates: tuple[Text, ...] = ()
    data_partition: Text | None = None
    missing_information: tuple[Text, ...] = ()


class AnalysisContext(Record):
    analysis_id: Identifier
    scientific_question: Text
    analysis_description: Text
    methods: Annotated[tuple[Text, ...], Field(min_length=1)]
    biological_context: BiologicalContext
    design: AnalyticalDesign
    observed_result: Text
    coverage_status: Literal["UNVALIDATED", "OUTSIDE_VALIDATED_COVERAGE"] = "UNVALIDATED"
    uncertainties: tuple[Text, ...] = ()


class ScientificClaim(Record):
    claim_id: Identifier
    analysis_id: Identifier
    statement: Text
    category: ClaimCategory
    computational_support: ClaimCategory
    assumptions: tuple[Text, ...] = ()
    origin: Literal["RESEARCHER", "MODEL", "IMPORT"] = "RESEARCHER"
    uncertainties: tuple[Text, ...] = ()

    @property
    def interpretation_warnings(self) -> tuple[str, ...]:
        if self.category == "CAUSAL" and self.computational_support != "CAUSAL":
            return ("The stated computational support does not establish the causal claim.",)
        return ()


class ClaimRelation(Record):
    source_claim_id: Identifier
    target_claim_id: Identifier
    relationship: Literal["ASSOCIATED_WITH", "DEPENDS_ON", "PREDICTS", "PROPOSED_CAUSES"]
    rationale: Text


class VerificationRecord(Record):
    """An attested check; authenticity must be established outside this schema."""

    reviewer_kind: Literal["HUMAN", "PROGRAMMATIC"]
    reviewer: Text
    method: Text
    checked_at: AwareDatetime
    artifact_sha256: Sha256 | None = None
    limitations: tuple[Text, ...] = ()


class EvidenceIdentifier(Record):
    namespace: Literal["DOI", "PMID", "PMCID", "ACCESSION", "OTHER"]
    value: Annotated[str, StringConstraints(min_length=1, max_length=500, pattern=r"^\S+$")]
    authority: Text

    @model_validator(mode="after")
    def identifier_syntax(self) -> Self:
        import re

        patterns = {"DOI": r"10\.\d{4,9}/\S+", "PMID": r"[1-9]\d*", "PMCID": r"PMC[1-9]\d*"}
        if self.namespace in patterns and not re.fullmatch(patterns[self.namespace], self.value):
            raise ValueError("identifier syntax is invalid")
        return self

    @property
    def normalized_key(self) -> tuple[str, str, str]:
        authority = "" if self.namespace in ("DOI", "PMID", "PMCID") else self.authority.casefold()
        value = self.value.casefold() if self.namespace == "DOI" else self.value
        return self.namespace, authority, value


class EvidenceItem(Record):
    evidence_id: Identifier
    source: Text
    identifiers: Annotated[tuple[EvidenceIdentifier, ...], Field(min_length=1)]
    title: Text | None = None
    authors: tuple[Text, ...] = ()
    year: Annotated[int, Field(ge=1600, le=9999)] | None = None
    retrieved_at: AwareDatetime | None = None
    publication_type: Text | None = None
    evidence_type: Text
    biological_context: BiologicalContext
    experimental_context: Text | None = None
    licensing_restrictions: Text | None = None
    existence_status: Literal["UNVERIFIED", "VERIFIED", "NOT_FOUND"] = "UNVERIFIED"
    existence_check: VerificationRecord | None = None
    content_sha256: Sha256 | None = None
    limitations: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def existence_receipt(self) -> Self:
        keys = [identifier.normalized_key for identifier in self.identifiers]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate evidence identifier")
        if self.existence_status != "UNVERIFIED":
            if self.existence_check is None or self.retrieved_at is None:
                raise ValueError("a checked identity requires a retrieval time and check record")
            if self.existence_check.checked_at < self.retrieved_at:
                raise ValueError("identity check cannot precede retrieval")
        return self


class EvidenceLink(Record):
    evidence_id: Identifier
    statement: Text
    relationship: Literal["SUPPORTS", "CONTRADICTS", "UNCERTAIN"]
    locator: Text
    rationale: Text
    entailment_check: VerificationRecord | None = None

    @model_validator(mode="after")
    def assessed_statement(self) -> Self:
        if self.relationship != "UNCERTAIN" and self.entailment_check is None:
            raise ValueError("statement support or contradiction requires an entailment check")
        return self


ContextDimension = Literal[
    "organism", "strain", "cell_type", "tissue", "disease_state",
    "experimental_condition", "molecular_target", "assay_type", "computational_method",
    "data_modality", "biological_scale", "intervention", "time_point",
    "reference_database", "software_assumptions",
]


class ContextComparison(Record):
    dimension: ContextDimension
    analysis_value: Text | None = None
    evidence_value: Text | None = None
    status: Literal["MATCH", "MISMATCH", "UNKNOWN", "NOT_APPLICABLE"]
    rationale: Text

    @model_validator(mode="after")
    def comparison_values(self) -> Self:
        if self.status in ("MATCH", "MISMATCH"):
            if self.analysis_value is None or self.evidence_value is None:
                raise ValueError("an assessed comparison requires both context values")
        return self


class ContextCompatibility(Record):
    status: Literal["MATCH", "PARTIAL", "MISMATCH", "UNKNOWN"] = "UNKNOWN"
    comparisons: tuple[ContextComparison, ...] = ()
    rationale: Text = "Context compatibility has not been assessed."
    limitations: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def consistent_summary(self) -> Self:
        dimensions = [item.dimension for item in self.comparisons]
        if len(dimensions) != len(set(dimensions)):
            raise ValueError("context dimensions must be unique")
        states = {item.status for item in self.comparisons} - {"NOT_APPLICABLE"}
        expected = (
            "MISMATCH" if "MISMATCH" in states else
            "PARTIAL" if states == {"MATCH", "UNKNOWN"} else
            "MATCH" if states == {"MATCH"} else "UNKNOWN"
        )
        if self.status != expected:
            raise ValueError("context summary disagrees with its comparisons")
        if self.status == "PARTIAL" and not self.limitations:
            raise ValueError("partial compatibility requires explicit limitations")
        return self


class InputRequirement(Record):
    input_id: Identifier
    description: Text
    format: Text
    privacy_class: PrivacyClass = "RESTRICTED"


class PrivacyRequirements(Record):
    classification: PrivacyClass = "RESTRICTED"
    raw_data_must_remain_local: LocalOnly = True
    external_transmission_allowed: Disabled = False
    rationale: Text


class ControlCandidate(Record):
    control_id: Identifier
    control_name: Text
    control_class: ControlClass
    scientific_level: ScientificLevel
    analysis_context: Identifier
    claim_tested: Identifier
    scientific_rationale: Text
    expected_behavior: Text
    failure_interpretation: Text
    evidence_required: bool
    supporting_evidence: tuple[EvidenceLink, ...] = ()
    evidence_status: Literal["AGENT_PROPOSED", "UNVERIFIED", "INSUFFICIENT_EVIDENCE"] = "AGENT_PROPOSED"
    context_compatibility: ContextCompatibility = Field(default_factory=ContextCompatibility)
    execution_status: ExecutionStatus = "NOT_RUN"
    required_inputs: tuple[InputRequirement, ...] = ()
    privacy_requirements: PrivacyRequirements
    priority: Literal["ESSENTIAL", "RECOMMENDED", "EXPLORATORY"]
    priority_rationale: Text
    method_basis: Text | None = None
    uncertainties: tuple[Text, ...] = ()
    limitations: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def input_policy(self) -> Self:
        input_ids = [item.input_id for item in self.required_inputs]
        if len(input_ids) != len(set(input_ids)):
            raise ValueError("control input identifiers must be unique")
        classification = PRIVACY_RANK[self.privacy_requirements.classification]
        if any(PRIVACY_RANK[item.privacy_class] > classification for item in self.required_inputs):
            raise ValueError("control privacy classification understates a required input")
        return self


class VerifiedControl(ControlCandidate):
    """A reviewed control record, including reviews that find insufficient evidence."""

    evidence_status: EvidenceStatus
    verification: VerificationRecord

    @model_validator(mode="after")
    def evidence_gate(self) -> Self:
        supporting = [link for link in self.supporting_evidence if link.relationship == "SUPPORTS"]
        contradicting = [link for link in self.supporting_evidence if link.relationship == "CONTRADICTS"]
        if self.evidence_status == "EVIDENCE_BACKED":
            if not any(link.statement == self.scientific_rationale for link in supporting):
                raise ValueError("evidence-backed rationale requires statement-specific support")
            if not any(link.statement == self.expected_behavior for link in supporting):
                raise ValueError("evidence-backed expected behavior requires statement-specific support")
            if contradicting:
                raise ValueError("contradictory evidence cannot be hidden by an evidence-backed status")
            if self.context_compatibility.status not in ("MATCH", "PARTIAL"):
                raise ValueError("evidence-backed controls require assessed context compatibility")
        if self.evidence_status == "METHOD_BASED" and (self.evidence_required or self.method_basis is None):
            raise ValueError("method-based controls require a method basis and no biological evidence gate")
        if self.evidence_status == "CONFLICTING_EVIDENCE" and not (supporting and contradicting):
            raise ValueError("conflicting evidence requires both support and contradiction")
        return self


class SoftwareVersion(Record):
    name: Text
    version: Text


class InputHash(Record):
    input_id: Identifier
    sha256: Sha256


class DecisionRule(Record):
    rule_id: Identifier
    description: Text
    specified_at: AwareDatetime
    limitations: Annotated[tuple[Text, ...], Field(min_length=1)]


class ExecutionPlan(Record):
    execution_id: Identifier
    control_id: Identifier
    pathway: Literal["LOCAL", "DISPATCHED"]
    execution_status: Literal["PLANNED", "BLOCKED"] = "PLANNED"
    required_inputs: tuple[InputRequirement, ...]
    software_versions: Annotated[tuple[SoftwareVersion, ...], Field(min_length=1)]
    parameters: tuple[Text, ...] = ()
    randomness: Literal["DETERMINISTIC", "SEEDED", "UNCONTROLLED"]
    random_seed: Annotated[int, Field(ge=0)] | None = None
    code_sha256: Sha256 | None = None
    output_schema_version: Literal["0.1.0"] = "0.1.0"
    decision_rule: DecisionRule | None = None
    instructions: Text
    limitations: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def seed_policy(self) -> Self:
        if (self.randomness == "SEEDED") != (self.random_seed is not None):
            raise ValueError("only seeded execution requires a recorded random seed")
        if self.randomness == "UNCONTROLLED" and not self.limitations:
            raise ValueError("uncontrolled randomness requires explicit limitations")
        return self


class NumericMeasure(Record):
    name: Text
    value: Number
    unit: Text | None = None


class ConfidenceInterval(Record):
    lower: Number
    upper: Number
    coverage: Annotated[float, Field(gt=0, lt=1, allow_inf_nan=False)]
    method: Text

    @model_validator(mode="after")
    def interval_order(self) -> Self:
        if self.lower > self.upper:
            raise ValueError("confidence interval bounds are reversed")
        return self


class NullDistributionSummary(Record):
    draws: Annotated[int, Field(gt=0)]
    mean: Number
    standard_deviation: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    null_hypothesis: Text
    exchangeability_assumptions: Annotated[tuple[Text, ...], Field(min_length=1)]


class ControlResult(Record):
    result_id: Identifier
    control_id: Identifier
    execution_id: Identifier
    execution_status: ExecutionStatus
    started_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None
    test_statistic: NumericMeasure | None = None
    effect_estimate: NumericMeasure | None = None
    confidence_interval: ConfidenceInterval | None = None
    p_value: Probability | None = None
    null_distribution_summary: NullDistributionSummary | None = None
    software_versions: tuple[SoftwareVersion, ...] = ()
    random_seed: Annotated[int, Field(ge=0)] | None = None
    input_hashes: tuple[InputHash, ...] = ()
    warnings: tuple[Text, ...] = ()
    errors: tuple[Text, ...] = ()
    interpretive_metadata: tuple[Text, ...] = ()
    outcome: Literal["PASS", "FAIL", "INDETERMINATE"] | None = None
    decision_rule_id: Identifier | None = None
    interpretation: Text | None = None

    @model_validator(mode="after")
    def result_state(self) -> Self:
        if self.started_at and self.completed_at and self.completed_at < self.started_at:
            raise ValueError("completion cannot precede execution")
        if self.execution_status == "FAILED" and not self.errors:
            raise ValueError("failed execution requires an error record")
        if self.execution_status == "COMPLETED":
            if self.errors or self.completed_at is None or not self.software_versions:
                raise ValueError("completed execution requires a time, versions, and no errors")
        if self.outcome is not None and self.execution_status != "COMPLETED":
            raise ValueError("only completed controls can have a scientific outcome")
        if self.outcome in ("PASS", "FAIL"):
            if self.decision_rule_id is None or self.started_at is None or self.interpretation is None:
                raise ValueError("pass or fail requires an execution time, decision rule, and interpretation")
        return self


class AuditOutcome(Record):
    audit_id: Identifier
    claim_id: Identifier
    assessment: Literal[
        "ROBUST", "SUPPORTED", "CONDITIONAL", "FRAGILE", "CONTROL_FAILURE",
        "INSUFFICIENT_EVIDENCE", "UNRESOLVED",
    ]
    rationale: Text
    result_ids: tuple[Identifier, ...] = ()
    evidence_ids: tuple[Identifier, ...] = ()
    reviewer: VerificationRecord
    uncertainties: tuple[Text, ...]
    limitations: Annotated[tuple[Text, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def audit_basis(self) -> Self:
        if self.assessment not in ("UNRESOLVED", "INSUFFICIENT_EVIDENCE"):
            if not self.result_ids and not self.evidence_ids:
                raise ValueError("an assessment requires traceable results or evidence")
        if self.assessment in ("ROBUST", "CONTROL_FAILURE") and not self.result_ids:
            raise ValueError("robustness or control failure requires control results")
        return self


class ModelProvenance(Record):
    provider: Text
    model_identifier: Text
    revision: Text | None = None
    prompt_template_sha256: Sha256


class ProvenanceRecord(Record):
    provenance_id: Identifier
    action: Literal[
        "SCHEMA_VALIDATION", "CLAIM_REVIEW", "EVIDENCE_REVIEW", "CONTEXT_REVIEW",
        "CONTROL_REVIEW", "EXECUTION_RESULT_IMPORT", "AUDIT",
    ]
    recorded_at: AwareDatetime
    controlomics_version: Text
    ontology_version: Literal["0.1.0"] = "0.1.0"
    record_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    software_versions: tuple[SoftwareVersion, ...] = ()
    input_hashes: tuple[InputHash, ...] = ()
    random_seed: Annotated[int, Field(ge=0)] | None = None
    model: ModelProvenance | None = None
    query_sha256: Sha256 | None = None
    warnings: tuple[Text, ...] = ()


class ProjectManifest(Record):
    project_id: Identifier
    created_at: AwareDatetime
    controlomics_version: Text
    ontology_version: Literal["0.1.0"] = "0.1.0"
    format: Literal["controlomics.project"] = "controlomics.project"


class PrivacyPolicy(Record):
    classification: PrivacyClass = "RESTRICTED"
    network_enabled: Disabled = False
    storage: Literal["LOCAL_ONLY"] = "LOCAL_ONLY"
    rationale: Text


class ControlomicsProject(Record):
    manifest: ProjectManifest
    analysis: AnalysisContext
    claims: Annotated[tuple[ScientificClaim, ...], Field(min_length=1)]
    claim_relations: tuple[ClaimRelation, ...] = ()
    evidence: tuple[EvidenceItem, ...] = ()
    candidates: tuple[ControlCandidate, ...] = ()
    controls: tuple[VerifiedControl, ...] = ()
    execution_plans: tuple[ExecutionPlan, ...] = ()
    results: tuple[ControlResult, ...] = ()
    audits: tuple[AuditOutcome, ...] = ()
    provenance: tuple[ProvenanceRecord, ...] = ()
    privacy: PrivacyPolicy

    @model_validator(mode="after")
    def project_integrity(self) -> Self:
        groups = (
            (self.claims, "claim_id"), (self.evidence, "evidence_id"),
            (self.candidates + self.controls, "control_id"),
            (self.execution_plans, "execution_id"), (self.results, "result_id"),
            (self.audits, "audit_id"), (self.provenance, "provenance_id"),
        )
        all_ids = [self.manifest.project_id, self.analysis.analysis_id]
        for records, id_field in groups:
            all_ids.extend(getattr(record, id_field) for record in records)
        if len(all_ids) != len(set(all_ids)):
            raise ValueError("project record identifiers must be unique")
        claims = {item.claim_id: item for item in self.claims}
        evidence = {item.evidence_id: item for item in self.evidence}
        controls = {item.control_id: item for item in self.candidates + self.controls}
        plans = {item.execution_id: item for item in self.execution_plans}
        results = {item.result_id: item for item in self.results}
        if len({item.execution_id for item in self.results}) != len(self.results):
            raise ValueError("an execution can have only one imported result")
        for claim in self.claims:
            if claim.analysis_id != self.analysis.analysis_id:
                raise ValueError("claim refers to an unknown analysis")
        for relation in self.claim_relations:
            if relation.source_claim_id not in claims or relation.target_claim_id not in claims:
                raise ValueError("claim relation refers to an unknown claim")
            if relation.source_claim_id == relation.target_claim_id:
                raise ValueError("claim relations cannot link a claim to itself")
        seen_identifiers: set[tuple[str, str, str]] = set()
        for item in self.evidence:
            keys = {identifier.normalized_key for identifier in item.identifiers}
            if seen_identifiers & keys:
                raise ValueError("duplicate publication identifiers must be consolidated")
            seen_identifiers.update(keys)
        for control in controls.values():
            if control.analysis_context != self.analysis.analysis_id or control.claim_tested not in claims:
                raise ValueError("control refers to an unknown analysis or claim")
            if PRIVACY_RANK[control.privacy_requirements.classification] > PRIVACY_RANK[self.privacy.classification]:
                raise ValueError("project privacy classification understates a control requirement")
            for link in control.supporting_evidence:
                if link.evidence_id not in evidence:
                    raise ValueError("control refers to unknown evidence")
                if link.relationship != "UNCERTAIN" and evidence[link.evidence_id].existence_status != "VERIFIED":
                    raise ValueError("assessed statement support requires a verified publication identity")
                if link.entailment_check is not None:
                    identity_check = evidence[link.evidence_id].existence_check
                    if identity_check is not None and link.entailment_check.checked_at < identity_check.checked_at:
                        raise ValueError("entailment check cannot precede its publication identity check")
                    if isinstance(control, VerifiedControl) and control.verification.checked_at < link.entailment_check.checked_at:
                        raise ValueError("control review cannot precede its entailment checks")
        for plan in self.execution_plans:
            if plan.control_id not in controls:
                raise ValueError("execution plan refers to an unknown control")
            if plan.required_inputs != controls[plan.control_id].required_inputs:
                raise ValueError("execution inputs differ from the control specification")
        for result in self.results:
            if result.execution_id not in plans or result.control_id not in controls:
                raise ValueError("result refers to an unknown execution or control")
            plan = plans[result.execution_id]
            if result.control_id != plan.control_id or result.random_seed != plan.random_seed:
                raise ValueError("result control or seed differs from the execution plan")
            if plan.code_sha256 is not None and [item.version for item in result.software_versions if item.name == "controlomics_fixed_runner"] != [plan.code_sha256]:
                raise ValueError("result runner hash differs from the planned code")
            expected_inputs = {item.input_id for item in plan.required_inputs}
            hashed_inputs = [item.input_id for item in result.input_hashes]
            if len(hashed_inputs) != len(set(hashed_inputs)):
                raise ValueError("duplicate result input hashes")
            if result.execution_status == "COMPLETED" and set(hashed_inputs) != expected_inputs:
                raise ValueError("completed results must hash all and only the required inputs")
            if result.outcome in ("PASS", "FAIL"):
                if plan.decision_rule is None or result.decision_rule_id != plan.decision_rule.rule_id:
                    raise ValueError("result lacks its prespecified decision rule")
                if plan.decision_rule.specified_at > result.started_at:
                    raise ValueError("decision rule was specified after execution began")
        for audit in self.audits:
            if audit.claim_id not in claims:
                raise ValueError("audit refers to an unknown claim")
            if not set(audit.result_ids) <= results.keys() or not set(audit.evidence_ids) <= evidence.keys():
                raise ValueError("audit refers to unknown results or evidence")
            cited_results = [results[item] for item in audit.result_ids]
            if any(controls[item.control_id].claim_tested != audit.claim_id for item in cited_results):
                raise ValueError("audit results test a different claim")
            if audit.assessment == "ROBUST" and any(item.outcome != "PASS" for item in cited_results):
                raise ValueError("robust assessment includes a nonpassing control")
            if audit.assessment == "CONTROL_FAILURE" and not any(item.outcome == "FAIL" for item in cited_results):
                raise ValueError("control failure assessment requires a failed control outcome")
        for event in self.provenance:
            if not set(event.record_ids) <= set(all_ids):
                raise ValueError("provenance refers to an unknown record")
        return self


PUBLIC_SCHEMAS = (
    AnalysisContext, ScientificClaim, EvidenceItem, ControlCandidate, VerifiedControl,
    ExecutionPlan, ControlResult, AuditOutcome, ProvenanceRecord, ControlomicsProject,
)
