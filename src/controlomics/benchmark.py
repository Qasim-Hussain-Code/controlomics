"""Development cases and synthetic numerical checks, not expert-grounded validation."""

import math
import platform
import random
from datetime import datetime, timezone

from controlomics import __version__
from controlomics.statistics import permutation_test
from controlomics.workflow import Intake, audit_project, new_project, propose, review_methods
from controlomics.schemas import AnalyticalDesign

CASES = (
    ("transcriptomic_association", "Transcriptomic comparison", "CAUSAL", "ASSOCIATIONAL", "Independent culture", "causal_overreach"),
    ("microscopy_units", "Microscopy classification", "PREDICTIVE", "PREDICTIVE", None, "sampling_unit_missing"),
    ("phylogenetic_evidence", "Phylogenetic comparison", "ASSOCIATIONAL", "ASSOCIATIONAL", "Independent lineage", "biological_evidence_absent"),
    ("structural_evidence", "Structural similarity comparison", "COMPARATIVE", "COMPARATIVE", "Reference structure", "biological_evidence_absent"),
    ("genomic_units", "Hypothetical variant summary", "DESCRIPTIVE", "DESCRIPTIVE", None, "sampling_unit_missing"),
    ("unlisted_method", "A previously unlisted computational biological method", "CAUSAL", "COMPARATIVE", "Independent sample", "causal_overreach"),
)


def wilson(successes, count):
    z = 1.959963984540054
    estimate = successes / count
    denominator = 1 + z * z / count
    center = (estimate + z * z / (2 * count)) / denominator
    radius = z * math.sqrt(estimate * (1 - estimate) / count + z * z / (4 * count * count)) / denominator
    return [max(0, center - radius), min(1, center + radius)]


def run_benchmark(trials=100, seed=827):
    if type(trials) is not int or not 20 <= trials <= 500:
        raise ValueError("development experiment requires 20 to 500 trials")
    cases = []
    for identifier, method, category, support, unit, expected in CASES:
        intake = Intake(question="Hypothetical development question", analysis_description=method,
            methods=(method,), observed_result="Hypothetical reported result; no biological observation.",
            claim="A hypothetical claim for testing a planted design or interpretation omission.",
            claim_category=category, computational_support=support, design=AnalyticalDesign(sampling_unit=unit))
        project = audit_project(review_methods(propose(new_project(intake))))
        findings = set()
        if project.claims[0].interpretation_warnings:
            findings.add("causal_overreach")
        if any("sampling unit" in item for item in project.audits[0].uncertainties):
            findings.add("sampling_unit_missing")
        if any("No biological recommendation" in item for item in project.audits[0].uncertainties):
            findings.add("biological_evidence_absent")
        cases.append({"case_id": identifier, "method": method, "expected_finding": expected,
            "detected": expected in findings, "findings": sorted(findings),
            "control_classes": [item.control_class for item in project.controls], "assessment": project.audits[0].assessment})
    generator = random.Random(seed)
    null_rejections = signal_rejections = 0
    for _ in range(trials):
        null = [generator.gauss(0, 1) for _ in range(8)]
        labels = [0] * 4 + [1] * 4
        null_rejections += permutation_test(null, labels)["p_value"] <= 0.05
        signal = null[:4] + [value + 3 for value in null[4:]]
        signal_rejections += permutation_test(signal, labels)["p_value"] <= 0.05
    return {
        "benchmark": "ControlomicsBench development harness", "run_at": datetime.now(timezone.utc).isoformat(),
        "controlomics_version": __version__, "python_version": platform.python_version(), "seed": seed,
        "scope": "Six manually specified software cases and independent Gaussian synthetic permutation checks. No expert annotations or biological datasets.",
        "cases": cases, "planted_software_findings": {"detected": sum(item["detected"] for item in cases), "total": len(cases)},
        "synthetic_numerical_experiment": {"trials": trials, "units_per_group": 4, "alpha": 0.05,
            "null_rejections": null_rejections, "null_rejection_rate": null_rejections / trials,
            "null_rate_wilson_95_interval": wilson(null_rejections, trials),
            "injected_shift": 3.0, "signal_rejections": signal_rejections, "signal_rejection_rate": signal_rejections / trials,
            "signal_rate_wilson_95_interval": wilson(signal_rejections, trials),
            "method": "Exact two-sided mean-difference permutation test over 70 assignments. Labels are exchangeable in the synthetic null."},
        "limitations": ["The cases test predefined software rules, not scientific control precision or generalization.",
            "The numerical experiment evaluates a narrow independent-unit statistical adapter, not an agent.",
            "Small exact tests have discrete and potentially conservative rejection probabilities.",
            "Expert-grounded benchmark cases, domain-held-out evaluation, model comparisons, and ablations remain pending."]}
