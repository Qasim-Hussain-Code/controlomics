"""Write manually specified hypothetical schema examples, without inference or retrieval."""

import json
from pathlib import Path

from controlomics.project import parse_project_json


def candidate(analysis_id, claim_id, name, control_class, rationale, expected, failure, method):
    return {
        "control_id": f"{analysis_id}.{control_class.lower()}",
        "control_name": name,
        "control_class": control_class,
        "scientific_level": "STATISTICAL",
        "analysis_context": analysis_id,
        "claim_tested": claim_id,
        "scientific_rationale": rationale,
        "expected_behavior": expected,
        "failure_interpretation": failure,
        "evidence_required": False,
        "supporting_evidence": [],
        "evidence_status": "UNVERIFIED",
        "required_inputs": [{
            "input_id": "synthetic_input",
            "description": "A small synthetic dataset created locally for a separately specified test.",
            "format": "Locally specified tabular input",
            "privacy_class": "SAFE",
        }],
        "privacy_requirements": {
            "classification": "SAFE",
            "rationale": "The example describes a hypothetical local test and contains no research data.",
        },
        "priority": "EXPLORATORY",
        "priority_rationale": "Method calibration is useful during development; biological appropriateness remains unreviewed.",
        "method_basis": method,
        "uncertainties": ["No executable test or empirical outcome is supplied."],
        "limitations": ["Synthetic method calibration cannot establish the biological claim."],
    }


def make_project(project_id, analysis, claim, positive, negative):
    return {
        "manifest": {
            "project_id": project_id,
            "created_at": "2026-10-05T00:00:00+00:00",
            "controlomics_version": "0.1.0.dev0",
        },
        "analysis": analysis,
        "claims": [claim],
        "candidates": [positive, negative],
        "privacy": {"classification": "SAFE", "rationale": "Manually specified hypothetical example; no raw data."},
    }


def examples():
    analysis_id, claim_id = "analysis.transcriptomics", "claim.transcriptomics"
    transcriptomics = make_project(
        "project.transcriptomics",
        {
            "analysis_id": analysis_id,
            "scientific_question": "Does a hypothetical treatment change transcript abundance in cultured yeast?",
            "analysis_description": "A hypothetical between-culture differential abundance comparison.",
            "methods": ["A researcher-specified count-based differential abundance method"],
            "biological_context": {"organism": "Saccharomyces cerevisiae", "data_modality": "bulk transcript counts"},
            "design": {
                "sampling_unit": "Independent culture",
                "independence_assumptions": ["Cultures, rather than individual counts, are the independent units."],
                "contrasts": ["Hypothetical treatment versus reference"],
                "missing_information": ["Replication, normalization, batch structure, and model specification are not supplied."],
            },
            "observed_result": "Hypothetical reported abundance differences; no measurements are included.",
            "uncertainties": ["The analysis and claim have not been scientifically reviewed."],
        },
        {
            "claim_id": claim_id, "analysis_id": analysis_id,
            "statement": "Transcript abundance differs between the hypothetical conditions.",
            "category": "COMPARATIVE", "computational_support": "COMPARATIVE",
            "assumptions": ["The sampling units and stated contrasts represent the intended comparison."],
        },
        candidate(
            analysis_id, claim_id, "Known synthetic abundance change", "POSITIVE",
            "A locally simulated signal can challenge the implementation's ability to recover a specified contrast.",
            "The method should recover a prespecified injected signal under its simulation assumptions.",
            "Failure would motivate checking contrast coding, implementation, or simulation assumptions.",
            "A simulation requires specified count behavior, effect size, replication, and acceptance criteria.",
        ),
        candidate(
            analysis_id, claim_id, "Unit-respecting null calibration", "NEGATIVE",
            "A justified null simulation can assess spurious signal under a separately defined no-effect model.",
            "False detections should be assessed against a prespecified null calibration criterion.",
            "Excess detections could reflect a misspecified null, dependence, or analytical failure.",
            "Define the no-effect process and dependence structure; label permutation requires exchangeability of independent units.",
        ),
    )
    analysis_id, claim_id = "analysis.microscopy", "claim.microscopy"
    microscopy = make_project(
        "project.microscopy",
        {
            "analysis_id": analysis_id,
            "scientific_question": "Can image features distinguish two hypothetical cell morphology labels?",
            "analysis_description": "A hypothetical supervised classifier evaluated on held-out cultures.",
            "methods": ["A researcher-specified image-feature classification pipeline"],
            "biological_context": {"data_modality": "microscopy image features", "biological_scale": "cultured cells"},
            "design": {
                "sampling_unit": "Independent culture",
                "data_partition": "All images from one culture must remain in one partition.",
                "missing_information": ["Label provenance, acquisition batches, and feature-selection procedure are unknown."],
            },
            "observed_result": "Hypothetical reported predictive discrimination; no metric or dataset is supplied.",
        },
        {
            "claim_id": claim_id, "analysis_id": analysis_id,
            "statement": "The image-feature pipeline predicts the hypothetical morphology label in new cultures.",
            "category": "PREDICTIVE", "computational_support": "PREDICTIVE",
            "assumptions": ["Held-out cultures are independent of training and preprocessing selection."],
        },
        candidate(
            analysis_id, claim_id, "Prespecified synthetic predictive signal", "POSITIVE",
            "An independently generated separable feature can challenge a pipeline's ability to detect a known synthetic signal.",
            "The full pipeline should recover discrimination for the prespecified signal in independently generated held-out units.",
            "Failure could indicate preprocessing, label handling, evaluation, or simulation problems.",
            "Specify signal strength and held-out generation before testing; avoid learning fixture labels through shared preprocessing.",
        ),
        candidate(
            analysis_id, claim_id, "Unit-respecting label null", "NEGATIVE",
            "A justified label-null experiment can challenge apparent discrimination caused by analytical leakage.",
            "The rerun pipeline should satisfy a prespecified no-information criterion under an appropriate label null.",
            "Unexpected discrimination could indicate leakage, a misspecified null, or dependence.",
            "Specify exchangeability and partitioning; repeat feature selection and tuning inside each null replicate.",
        ),
    )
    return {"transcriptomics.project.json": transcriptomics, "microscopy_ml.project.json": microscopy}


if __name__ == "__main__":
    directory = Path(__file__).resolve().parents[1] / "examples"
    directory.mkdir(exist_ok=True)
    for name, payload in examples().items():
        project = parse_project_json(json.dumps(payload))
        (directory / name).write_text(project.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n")
    print("Wrote two hypothetical schema examples. No inference, retrieval, or execution occurred.")
