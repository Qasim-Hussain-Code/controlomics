"""Generate transparently labeled development cases and unassessed sheets."""

from pathlib import Path

from controlomics.evaluation import (EvaluationCase, EvaluationDataset, ReferenceControl,
    annotation_template, run_dataset, evaluate)
from controlomics.schemas import AnalyticalDesign, EvidenceIdentifier
from controlomics.workflow import Intake
from controlomics.cli import write_json


def main():
    cases = []
    specifications = (
        ("prediction_partition", "Feature classification with tuning and selection", "PREDICTIVE", "PREDICTIVE", "Independent sample", None,
         ("partition_missing", "selection_leakage_review"), "10.1186/1471-2105-7-91"),
        ("nested_comparison", "Group comparison with repeated measurements within donor", "COMPARATIVE", "COMPARATIVE", "Donor", None,
         ("dependent_units_review", "exchangeability_review"), "10.1038/s41467-021-21038-1"),
        ("enrichment_background", "Gene set enrichment and overlap", "ASSOCIATIONAL", "ASSOCIATIONAL", "Independent sample", None,
         ("background_review", "exchangeability_review"), "10.1073/pnas.0506580102"),
        ("new_modality_rank", "Previously unlisted measurement ranking with a similarity score", "COMPARATIVE", "COMPARATIVE", "Independent reference", None,
         ("reference_selection_review",), None),
        ("causal_interpretation", "An observational association", "CAUSAL", "ASSOCIATIONAL", "Independent sample", None,
         ("causal_overreach",), None),
        ("unspecified_operation", "Unrecognized operation", "DESCRIPTIVE", "DESCRIPTIVE", None, None,
         ("operation_uncertain", "sampling_unit_missing"), None),
    )
    for identifier, method, category, support, unit, partition, findings, doi in specifications:
        intake = Intake(question="Hypothetical development question", analysis_description=method, methods=(method,),
            observed_result="Hypothetical reported result; no biological observation.", claim="A hypothetical " + category.lower() + " statement.",
            claim_category=category, computational_support=support, design=AnalyticalDesign(sampling_unit=unit, data_partition=partition))
        sources = (EvidenceIdentifier(namespace="DOI", value=doi, authority="doi.org"),) if doi else ()
        cases.append(EvaluationCase(case_id=identifier, description="Manually specified software development scenario: " + method,
            partition="DEVELOPMENT", source_group=identifier, intake=intake, source_identifiers=sources, expected_findings=findings,
            references=(ReferenceControl(reference_id="positive", description="Prespecified known-signal methodological reference", control_class="POSITIVE", essential=True),
                        ReferenceControl(reference_id="negative", description="Prespecified signal-absent methodological reference", control_class="NEGATIVE", essential=True))))
    dataset = EvaluationDataset(dataset_id="development_design.v0.1", annotation_origin="DEVELOPMENT_FIXTURE", cases=tuple(cases),
        limitations=("Development expectations concern review-question codes, not independently expert-validated control truth.",
            "Public method papers motivate scenarios; they are not entailment receipts or annotations of the generated controls.",
            "All cases are development cases. No held-out scientific evaluation is claimed."))
    write_json(Path("examples/benchmark.dataset.json"), dataset.model_dump(mode="json"))
    reports = {}
    for reasoner in ("reference", "design"):
        run = run_dataset(dataset, reasoner)
        sheet = annotation_template(dataset, run)
        write_json(Path("examples") / ("benchmark." + reasoner + ".predictions.json"), run.model_dump(mode="json"))
        write_json(Path("examples") / ("benchmark." + reasoner + ".unassessed.json"), sheet.model_dump(mode="json"))
        reports[reasoner] = evaluate(sheet)
    write_json(Path("docs/validation/design_development_evaluation.json"), reports)
    print("Generated development cases, offline predictions, and unassessed judgment sheets. No expert ratings were invented.")


if __name__ == "__main__":
    main()
