"""Offline end-to-end demonstration with explicitly synthetic numeric references."""

import argparse
from pathlib import Path

from controlomics.execution import ExecutionConfig, execute_local
from controlomics.project import load_project, save_project
from controlomics.reports import write_report
from controlomics.workflow import Intake, audit_project, new_project, propose, review_methods


def demonstration(example, root):
    template = load_project(root / "examples" / (example + ".project.json"))
    analysis, claim = template.analysis, template.claims[0]
    intake = Intake(question=analysis.scientific_question, analysis_description=analysis.analysis_description,
        methods=analysis.methods, observed_result=analysis.observed_result, claim=claim.statement,
        claim_category=claim.category, computational_support=claim.computational_support,
        biological_context=analysis.biological_context, design=analysis.design, assumptions=claim.assumptions)
    project = review_methods(propose(new_project(intake)))
    for control in project.controls:
        positive = control.control_class == "POSITIVE"
        config = ExecutionConfig(kind="REFERENCE", expected_difference=2.0 if positive else 0.0,
            assumptions=("The supplied CSV is a hand-constructed synthetic independent-unit numeric reference.",
                "It tests a group mean-difference calculation, not the primary analysis or biological claim.",
                "The expected effect was specified independently before running the reference calculation."))
        raw = (root / "examples" / ("positive_reference.csv" if positive else "negative_reference.csv")).read_bytes()
        project = execute_local(project, control.control_id, config, raw)
    return audit_project(project)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("local_projects/demo"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.output.mkdir(parents=True, exist_ok=True)
    for example in ("transcriptomics", "microscopy_ml"):
        project = demonstration(example, root)
        save_project(project, args.output / (example + ".project.json"))
        write_report(project, args.output / (example + ".report.html"))
        if example == "transcriptomics":
            write_report(project, args.output / "report.html")
        outcomes = ", ".join(result.outcome for result in project.results)
        print(example + ": synthetic technical references " + outcomes + "; biological claim remains unvalidated.")
    print("Saved two projects and scientific reports. No external requests were made.")


if __name__ == "__main__":
    main()
