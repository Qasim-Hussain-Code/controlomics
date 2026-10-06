"""Inspectable local design cues. Heuristics do not establish scientific facts."""

from __future__ import annotations

import re
from typing import Literal

from controlomics.schemas import ClaimCategory, Record, Text

Facet = Literal["PREDICTION", "GROUP_COMPARISON", "ASSOCIATION", "RANKING", "SET_OVERLAP",
    "SIMILARITY", "DEPENDENT_UNITS", "TIME_DEPENDENCE", "BATCH_STRUCTURE", "CAUSAL_INTERPRETATION"]


class DesignCue(Record):
    facet: Facet
    basis: Text


class DesignFinding(Record):
    code: Text
    message: Text
    interpretation: Literal["MISSING_INFORMATION", "REVIEW_REQUIRED", "STATED_MISMATCH"]


class ReasoningProfile(Record):
    rules_version: Literal["design_rules.v0.1"] = "design_rules.v0.1"
    cues: tuple[DesignCue, ...]
    findings: tuple[DesignFinding, ...]
    limitations: tuple[Text, ...] = (
        "Lexical cues and supplied categories are provisional; they do not establish the actual design.",
        "Rules cover analytical operations, not an exhaustive biological domain list or validated general reasoning.",)


PATTERNS = {
    "PREDICTION": r"\b(classifi\w*|predict\w*|training|cross[- ]validation|held[- ]out)\b",
    "GROUP_COMPARISON": r"\b(compar\w*|contrast\w*|differential|between[- ]group|fold[- ]change)\b",
    "ASSOCIATION": r"\b(association\w*|correlat\w*|regression)\b",
    "RANKING": r"\b(rank\w*|scor\w*|prioriti[sz]\w*|screening)\b",
    "SET_OVERLAP": r"\b(enrichment|over[- ]representation|overlap|gene[- ]sets?)\b",
    "SIMILARITY": r"\b(similarity|alignment|homology|distance|nearest[- ]neighbou?r)\b",
    "DEPENDENT_UNITS": r"\b(paired|repeated[- ]measur\w*|nested|same (?:donor|individual|culture)|within[- ](?:donor|individual|culture)|multiple .{0,30} per (?:donor|individual|culture))\b",
    "TIME_DEPENDENCE": r"\b(time[- ]series|longitudinal|temporal|serial correlation)\b",
    "BATCH_STRUCTURE": r"\b(batch\w*|plate\w*|site[- ]effect\w*|confound\w*)\b",
}


def describe_design(analysis, claim):
    text = "\n".join((analysis.analysis_description, *analysis.methods, claim.statement,
        *claim.assumptions, analysis.design.data_partition or "", *analysis.design.independence_assumptions,
        *analysis.design.covariates))
    cues = [DesignCue(facet=facet, basis="Text contains the provisional design cue: " + match.group())
        for facet, pattern in PATTERNS.items() if (match := re.search(pattern, text, re.IGNORECASE))]
    facets = {item.facet for item in cues}
    for category, facet in (("PREDICTIVE", "PREDICTION"), ("COMPARATIVE", "GROUP_COMPARISON"),
                            ("ASSOCIATIONAL", "ASSOCIATION")):
        if claim.category == category and facet not in facets:
            cues.append(DesignCue(facet=facet, basis="Researcher-supplied claim category: " + category))
            facets.add(facet)
    if claim.category in ("CAUSAL", "MECHANISTIC"):
        cues.append(DesignCue(facet="CAUSAL_INTERPRETATION", basis="Researcher-supplied causal or mechanistic interpretation."))
        facets.add("CAUSAL_INTERPRETATION")
    findings = []
    def finding(code, message, interpretation="REVIEW_REQUIRED"):
        findings.append(DesignFinding(code=code, message=message, interpretation=interpretation))
    if not analysis.design.sampling_unit:
        finding("sampling_unit_missing", "The independent sampling unit is unspecified; identify the unit of replication before interpreting uncertainty.", "MISSING_INFORMATION")
    if "PREDICTION" in facets:
        finding("selection_leakage_review", "Review whether feature selection, tuning, normalization, and repeated observations were kept inside training partitions.")
        if not analysis.design.data_partition:
            finding("partition_missing", "The prediction assessment has no supplied training/test partition description.", "MISSING_INFORMATION")
    if "DEPENDENT_UNITS" in facets:
        finding("dependent_units_review", "Paired or nested observations may be present. Row count and unique IDs do not establish independent replication.")
    if "TIME_DEPENDENCE" in facets:
        finding("temporal_dependence_review", "Review time ordering, autocorrelation, and whether evaluation or resampling preserves temporal structure.")
    if facets & {"GROUP_COMPARISON", "ASSOCIATION", "SET_OVERLAP"}:
        finding("exchangeability_review", "Justify the unit and restrictions of any null resampling; unrestricted label permutation is not automatically appropriate.")
    if "SET_OVERLAP" in facets:
        finding("background_review", "Specify the tested universe, annotation versions, set-size effects, and multiplicity handling for overlap or enrichment.")
    if "BATCH_STRUCTURE" in facets:
        finding("confounding_review", "Assess whether batch or nuisance structure is balanced or confounded with the contrast; correction alone does not establish identifiability.")
    if "RANKING" in facets or "SIMILARITY" in facets:
        finding("reference_selection_review", "Separate reference selection from evaluation and account for similarity, composition, size, or score-distribution matching.")
    if claim.interpretation_warnings:
        finding("causal_overreach", "The stated computational support does not establish the claimed causal interpretation.", "STATED_MISMATCH")
    if not cues:
        finding("operation_uncertain", "No analytical operation was recognized. Generic references are provisional; describe the operation and assumptions explicitly.", "MISSING_INFORMATION")
    return ReasoningProfile(cues=tuple(cues), findings=tuple(findings))


class NarrativeInput(Record):
    description: Text


class InterpretationDraft(Record):
    fields: dict[str, str]
    suggested_categories: tuple[ClaimCategory, ...]
    missing_fields: tuple[Text, ...]
    limitations: tuple[Text, ...]


LABELS = {"question": "question", "research question": "question", "analysis": "analysis_description",
    "analysis description": "analysis_description", "methods": "methods", "method": "methods",
    "result": "observed_result", "reported result": "observed_result", "claim": "claim", "conclusion": "claim",
    "organism": "organism", "sampling unit": "sampling_unit", "partition": "data_partition",
    "assumptions": "assumptions", "claim category": "claim_category", "computational support": "computational_support"}


def interpret_narrative(request: NarrativeInput):
    fields, notes, current = {}, [], None
    for line in request.description.splitlines():
        match = re.match(r"^\s*([A-Za-z ]{2,32}):\s*(.*)$", line)
        if match and match[1].strip().casefold() in LABELS:
            key = LABELS[match[1].strip().casefold()]
            if key in fields:
                notes.append("Repeated label was not merged: " + key)
                current = None
            else:
                fields[key], current = match[2].strip(), key
        elif current and line.strip():
            fields[current] += "\n" + line.strip()
    if not fields:
        fields["analysis_description"] = request.description
        for key, pattern in (("claim", r"(?:We conclude that|We claim that|Our conclusion is that)\s+[^.!?]+[.!?]?"),
                             ("observed_result", r"(?:We observed|The reported result was)\s+[^.!?]+[.!?]?"),
                             ("methods", r"(?:We used|The method was)\s+[^.!?]+[.!?]?"),
                             ("question", r"(?:^|(?<=[.!?])\s+)(?:Does|Can|Is|Are|How)\s+[^.!?]+\?")):
            if match := re.search(pattern, request.description, re.IGNORECASE):
                fields[key] = match.group().strip()
        notes.append("Prose extraction retains explicit source phrases and can miss or misidentify their role.")
    categories = []
    statement = fields.get("claim", "")
    for category, pattern in (("CAUSAL", r"\b(causes?|causal)\b"), ("PREDICTIVE", r"\b(predict\w*|classif\w*)\b"),
        ("ASSOCIATIONAL", r"\b(associat\w*|correlat\w*)\b"), ("COMPARATIVE", r"\b(differ\w*|compar\w*|higher|lower)\b")):
        if re.search(pattern, statement, re.IGNORECASE):
            categories.append(category)
    missing = tuple(key for key in ("question", "analysis_description", "methods", "observed_result", "claim", "claim_category", "computational_support") if not fields.get(key))
    return InterpretationDraft(fields=fields, suggested_categories=tuple(categories), missing_fields=missing,
        limitations=tuple(notes) + ("Review every extracted field. Categories are suggestions; computational support is never inferred from a causal claim.",
            "This local parser is a transparent convenience, not a validated language-understanding model."))
