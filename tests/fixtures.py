"""Synthetic schema fixtures. Receipts and outcomes are not scientific observations."""

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TIME = "2026-10-05T01:00:00+00:00"


def payload(name="transcriptomics.project.json"):
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


def receipt():
    return {
        "reviewer_kind": "PROGRAMMATIC",
        "reviewer": "synthetic_unit_test",
        "method": "Synthetic receipt for schema testing; no external scientific check occurred.",
        "checked_at": TIME,
        "limitations": ["A synthetic schema fixture is not independent evidence."],
    }


def reviewed_project(status="EVIDENCE_BACKED"):
    data = payload()
    control = data["candidates"].pop(0)
    control["verification"] = receipt()
    control["evidence_status"] = status
    control["context_compatibility"] = {
        "status": "MATCH",
        "comparisons": [{
            "dimension": "organism", "analysis_value": "Saccharomyces cerevisiae",
            "evidence_value": "Saccharomyces cerevisiae", "status": "MATCH",
            "rationale": "Synthetic comparison for schema testing.",
        }],
        "rationale": "Synthetic context assessment; not independent scientific review.",
    }
    data["controls"] = [control]
    if status != "METHOD_BASED":
        data["evidence"] = [{
            "evidence_id": "evidence.synthetic", "source": "synthetic_unit_test",
            "identifiers": [{"namespace": "OTHER", "value": "synthetic-fixture", "authority": "unit_test"}],
            "retrieved_at": TIME, "evidence_type": "Synthetic schema fixture",
            "biological_context": {"organism": "Saccharomyces cerevisiae"},
            "existence_status": "VERIFIED", "existence_check": receipt(),
        }]
        control["supporting_evidence"] = [{
            "evidence_id": "evidence.synthetic", "statement": statement, "relationship": "SUPPORTS",
            "locator": "synthetic fixture only", "rationale": "Synthetic entailment fixture.",
            "entailment_check": receipt(),
        } for statement in (control["scientific_rationale"], control["expected_behavior"])]
    return data


def executed_project():
    data = reviewed_project("METHOD_BASED")
    control = data["controls"][0]
    data["execution_plans"] = [{
        "execution_id": "execution.synthetic", "control_id": control["control_id"],
        "pathway": "LOCAL", "required_inputs": copy.deepcopy(control["required_inputs"]),
        "software_versions": [{"name": "synthetic_test", "version": "0"}],
        "randomness": "SEEDED", "random_seed": 7,
        "instructions": "Schema fixture only; no executable code is supplied.",
        "decision_rule": {
            "rule_id": "rule.synthetic", "specified_at": "2026-10-05T00:30:00+00:00",
            "description": "Synthetic rule for testing traceability, not a scientific threshold.",
            "limitations": ["No empirical decision is made by this fixture."],
        },
    }]
    data["results"] = [{
        "result_id": "result.synthetic", "execution_id": "execution.synthetic",
        "control_id": control["control_id"], "execution_status": "COMPLETED",
        "started_at": TIME, "completed_at": "2026-10-05T02:00:00+00:00",
        "software_versions": [{"name": "synthetic_test", "version": "0"}],
        "random_seed": 7,
        "input_hashes": [{"input_id": "synthetic_input", "sha256": "0" * 64}],
        "outcome": "PASS", "decision_rule_id": "rule.synthetic",
        "interpretation": "Synthetic passing outcome for schema tests only.",
    }]
    return data
