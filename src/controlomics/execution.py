"""Reviewed fixed templates for small local numeric controls with explicit adapters."""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from tempfile import TemporaryDirectory
import uuid
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, model_validator

from controlomics import __version__
from controlomics import statistics, storage
from controlomics.privacy import canonical_json, digest
from controlomics.project import decode_json
from controlomics.storage import require_new_directory, staged_directory
from controlomics.schemas import (
    ControlResult, DecisionRule, ExecutionPlan, InputRequirement, PrivacyPolicy, PrivacyRequirements,
    Identifier, Record, SoftwareVersion, Text,
)
from controlomics.workflow import event, now, replace_project


class ExecutionConfig(Record):
    kind: Literal["REFERENCE", "PERMUTATION", "BOOTSTRAP"]
    adapter: Literal["INDEPENDENT_REFERENCE", "PAIRED_DIFFERENCE"] = "INDEPENDENT_REFERENCE"
    adapter_rationale: Text | None = None
    assumptions: Annotated[tuple[Text, ...], Field(min_length=1)]
    random_seed: Annotated[int, Field(ge=0)] = 0
    draws: Annotated[int, Field(ge=100, le=10000)] = 999
    coverage: Annotated[float, Field(gt=0, lt=1, allow_inf_nan=False)] = 0.95
    expected_difference: Annotated[float, Field(allow_inf_nan=False)] | None = None
    absolute_tolerance: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 1e-9

    @model_validator(mode="after")
    def reference_value(self):
        if self.adapter == "PAIRED_DIFFERENCE" and (self.kind == "REFERENCE" or self.adapter_rationale is None):
            raise ValueError("paired inference requires an applicability rationale and permutation or bootstrap kind")
        if self.kind == "REFERENCE" and self.expected_difference is None:
            raise ValueError("a reference check requires an independently prespecified expected difference")
        if self.kind != "REFERENCE" and self.expected_difference is not None:
            raise ValueError("inferential controls do not use an automatic reference pass rule")
        return self


PAIRED_BASIS = "Complete-pair mean differences; independent pairs; sign-invariant differences for the permutation null; whole-pair resampling for the bootstrap."


class PairedSubmission(Record):
    claim_id: Identifier
    rationale: Text
    assumptions: Annotated[tuple[Text, ...], Field(min_length=1)]


def specify_paired_control(project, claim_id, rationale, assumptions):
    submission = PairedSubmission.model_validate_json(json.dumps({"claim_id": claim_id, "rationale": rationale, "assumptions": assumptions}))
    from controlomics.models import DraftControl
    from controlomics.workflow import CandidateSubmission, specify_candidate, review_methods
    draft = DraftControl(name="Complete-pair difference control", control_class="NULL", scientific_level="STATISTICAL",
        rationale=submission.rationale, expected_behavior="Under the specified sign-invariant null, within-pair sign flips generate the reference distribution of the absolute mean difference. Resampling complete pairs estimates uncertainty in the observed mean difference under the supplied sampling assumptions.",
        failure_interpretation="A small p value challenges the specified sign-invariant null. A bootstrap interval describes estimated uncertainty under its assumptions. Neither establishes causality or biological validity.",
        evidence_required=False, method_basis=PAIRED_BASIS,
        uncertainties=submission.assumptions, limitations=("Pair completeness does not establish independence or sign invariance. A zero mean alone does not justify sign flips.",
            "The percentile bootstrap resamples complete pairs; its population coverage is not established by this calculation.",
            "Nested, temporal, covariate-adjusted, and primary analyses require other adapters."))
    updated = specify_candidate(project, CandidateSubmission(claim_id=submission.claim_id, control=draft))
    return review_methods(updated, control_ids=(updated.candidates[-1].control_id,))


RUNNER = '''"""Local fixed-template control runner. No network or dynamic code execution."""
import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    config = json.loads((base / "config.json").read_text(encoding="utf-8"))
    plan = json.loads((base / "execution_plan.json").read_text(encoding="utf-8"))
    manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["artifact_hashes"].items():
        if hashlib.sha256((base / name).read_bytes()).hexdigest() != expected:
            raise ValueError("execution artifact hash differs from the reviewed package")
    from export_storage import require_distinct_outputs, write_text_atomic
    require_distinct_outputs(args.input, args.output)
    for name in ("config.json", "execution_plan.json", "control.json", "result.schema.json", "environment.json", "run_control.py", "stats.py", "export_storage.py", "verify_results.py", "manifest.json", "README.md", "project.json"):
        require_distinct_outputs(args.output, base / name)
    from stats import read_numeric_bytes, mean_difference, permutation_test, bootstrap_difference, read_paired_bytes, paired_mean, paired_permutation, paired_bootstrap
    started = datetime.now(timezone.utc).isoformat()
    with args.input.open("rb") as stream:
        raw_input = stream.read(2 * 1024 * 1024 + 1)
    paired = config.get("adapter") == "PAIRED_DIFFERENCE"
    if paired:
        differences = read_paired_bytes(raw_input)
        effect = paired_mean(differences)
    else:
        values, labels = read_numeric_bytes(raw_input)
        effect = mean_difference(values, labels)
    output = {
        "schema_version": "0.1.0", "result_id": plan["execution_id"] + ".result",
        "control_id": plan["control_id"], "execution_id": plan["execution_id"],
        "execution_status": "COMPLETED", "started_at": started,
        "software_versions": [{"name": "Python", "version": platform.python_version()},
                              {"name": "controlomics_fixed_runner", "version": manifest["code_sha256"]}],
        "random_seed": plan["random_seed"],
        "input_hashes": [{"input_id": "paired_units" if paired else "numeric_units", "sha256": hashlib.sha256(raw_input).hexdigest()}],
        "effect_estimate": {"name": "mean of within-pair condition 1 minus condition 0" if paired else "mean(label=1)-mean(label=0)", "value": effect},
        "outcome": "INDETERMINATE", "warnings": ["Sampling independence and applicability are researcher-supplied assumptions."],
        "interpretive_metadata": config["assumptions"],
        "interpretation": "The numeric result alone does not establish biological validity or absence of an effect.",
    }
    if config["kind"] == "REFERENCE":
        passed = abs(effect - config["expected_difference"]) <= config["absolute_tolerance"]
        output.update(outcome="PASS" if passed else "FAIL", decision_rule_id=plan["decision_rule"]["rule_id"],
                      interpretation="Prespecified technical reference calculation " + ("matched" if passed else "did not match") + " its expected output. This does not establish the biological claim.")
    elif config["kind"] == "PERMUTATION":
        result = paired_permutation(differences, seed=config["random_seed"], draws=config["draws"]) if paired else permutation_test(values, labels, seed=config["random_seed"], draws=config["draws"])
        output.update(p_value=result["p_value"],
            test_statistic={"name": "absolute mean difference", "value": abs(effect)},
            null_distribution_summary={"draws": result["draws"], "mean": result["null_mean"],
                "standard_deviation": result["null_sd"], "null_hypothesis": "Independent pair differences are invariant under independent sign flips." if paired else "Group labels are exchangeable for the tested mean-difference null.",
                "exchangeability_assumptions": config["assumptions"]})
        output["warnings"].append("Exact enumeration" if result["exact"] else "Monte Carlo p value uses the plus-one correction.")
        output["warnings"].append("Numerical tail comparisons use a relative tolerance of 1e-12 with zero absolute tolerance.")
    else:
        result = paired_bootstrap(differences, seed=config["random_seed"], draws=config["draws"], coverage=config["coverage"]) if paired else bootstrap_difference(values, labels, seed=config["random_seed"], draws=config["draws"], coverage=config["coverage"])
        output["confidence_interval"] = {"lower": result["lower"], "upper": result["upper"],
            "coverage": result["coverage"], "method": "Complete-pair percentile bootstrap with linear quantile interpolation" if paired else "Within-group percentile bootstrap with linear quantile interpolation"}
        output["warnings"].append("Percentile intervals can have poor coverage for small, biased, or dependent samples.")
    output["completed_at"] = datetime.now(timezone.utc).isoformat()
    write_text_atomic(args.output, json.dumps(output, indent=2, allow_nan=False) + "\\n")
    print("Wrote a local numeric control result; raw input values were not printed.")

if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, OverflowError):
        print("Execution failed; input values and local paths are omitted.")
        raise SystemExit(1)
    except KeyboardInterrupt:
        print("Execution interrupted; no successful result is implied.")
        raise SystemExit(130)
'''

VERIFIER = '''"""Verify schema and bindings using the installed Controlomics package."""
import argparse
import hashlib
import json
from pathlib import Path
from controlomics.schemas import ControlResult, ExecutionPlan
from controlomics.project import decode_json

parser = argparse.ArgumentParser()
parser.add_argument("result", type=Path)
args = parser.parse_args()
try:
    base = Path(__file__).resolve().parent
    manifest = decode_json((base / "manifest.json").read_bytes())
    for name, expected in manifest["artifact_hashes"].items():
        if hashlib.sha256((base / name).read_bytes()).hexdigest() != expected:
            raise ValueError("changed execution artifact")
    with args.result.open("rb") as stream:
        content = stream.read(2 * 1024 * 1024 + 1)
    decode_json(content)
    result = ControlResult.model_validate_json(content)
    plan = ExecutionPlan.model_validate_json((base / "execution_plan.json").read_bytes())
    if result.control_id != plan.control_id or result.execution_id != plan.execution_id or result.random_seed != plan.random_seed:
        raise ValueError("result binding differs")
    if {item.input_id for item in result.input_hashes} != {item.input_id for item in plan.required_inputs}:
        raise ValueError("result input bindings differ")
    if [item.version for item in result.software_versions if item.name == "controlomics_fixed_runner"] != [plan.code_sha256]:
        raise ValueError("result runner hash differs")
    if result.outcome in ("PASS", "FAIL") and (plan.decision_rule is None or result.decision_rule_id != plan.decision_rule.rule_id or result.started_at < plan.decision_rule.specified_at):
        raise ValueError("result prespecified rule differs")
    print("Result schema and execution bindings are valid; scientific interpretation needs review.")
except (ValueError, OSError, RecursionError):
    print("Result verification failed; input contents and paths are omitted.")
    raise SystemExit(1)
'''


def build_package(project, control_id: str, config: ExecutionConfig, directory: Path, pathway="DISPATCHED"):
    control = next((item for item in project.controls if item.control_id == control_id), None)
    if control is None or control.evidence_status not in ("METHOD_BASED", "EVIDENCE_BACKED"):
        raise ValueError("execution requires a reviewed, justified control specification")
    paired = config.adapter == "PAIRED_DIFFERENCE"
    if paired and (control.scientific_level != "STATISTICAL" or control.control_class != "NULL" or control.method_basis != PAIRED_BASIS):
        raise ValueError("paired adapter requires the explicit complete-pair control specification")
    if not paired and (control.scientific_level != "TECHNICAL" or control.control_class not in ("POSITIVE", "NEGATIVE")):
        raise ValueError("this numeric adapter only executes technical positive and negative reference specifications; other controls require an applicable adapter")
    require_new_directory(directory)
    if any(plan.control_id == control_id for plan in project.execution_plans):
        raise ValueError("control already has an execution plan; create a separate project snapshot for a new run")
    stats_code = Path(statistics.__file__).read_text(encoding="utf-8").replace("\r\n", "\n")
    storage_code = Path(storage.__file__).read_text(encoding="utf-8").replace("\r\n", "\n")
    code_hash = digest(RUNNER.encode() + stats_code.encode() + storage_code.encode())
    inputs = (InputRequirement(input_id="paired_units" if paired else "numeric_units",
        description="Complete pairs, independent across pair identifiers; raw data remain local." if paired else "Independent numeric units with group labels; raw data remain local.",
        format="UTF-8 CSV with columns pair,condition,value; exactly one condition 0 and 1 per pair" if paired else "UTF-8 CSV with columns unit,label,value; labels 0 or 1", privacy_class="RESTRICTED"),)
    control = control.model_copy(update={"required_inputs": inputs, "execution_status": "PLANNED",
        "privacy_requirements": PrivacyRequirements(rationale="Numeric input data must be executed where they reside.")})
    rule = None
    if config.kind == "REFERENCE":
        rule = DecisionRule(rule_id="rule." + uuid.uuid4().hex,
            description=f"Absolute mean-difference error <= {config.absolute_tolerance} relative to prespecified expected difference {config.expected_difference}.",
            specified_at=now(), limitations=("This is a technical reference calculation and does not establish biology.",))
    plan = ExecutionPlan(execution_id="execution." + uuid.uuid4().hex, control_id=control_id, pathway=pathway,
        required_inputs=inputs, software_versions=(SoftwareVersion(name="Python", version=platform.python_version()),),
        randomness="DETERMINISTIC" if config.kind == "REFERENCE" else "SEEDED",
        random_seed=None if config.kind == "REFERENCE" else config.random_seed, code_sha256=code_hash,
        decision_rule=rule, parameters=("Configuration sha256: " + digest(canonical_json(config.model_dump(mode="json"))), "Adapter: " + config.adapter) + (("Applicability rationale: " + config.adapter_rationale,) if config.adapter_rationale else ()),
        instructions="Run the fixed local runner on the specified CSV layout, verify the result, then import it into the saved project.",
        limitations=("This adapter handles complete pairs only; independence across pairs and sign invariance require researcher justification." if paired else "This adapter handles independent-unit technical references only.",
            "Clustered, temporal, covariate-adjusted, and full primary analyses require other adapters.",))
    updated = replace_project(project, controls=tuple(control if item.control_id == control_id else item for item in project.controls),
        privacy=PrivacyPolicy(rationale="Project includes restricted numeric input requirements; data remain local."),
        execution_plans=project.execution_plans + (plan,),
        provenance=project.provenance + (event("CONTROL_REVIEW", [control_id, plan.execution_id]),))
    documents = {"config.json": config.model_dump(mode="json"), "execution_plan.json": plan.model_dump(mode="json"),
                 "control.json": control.model_dump(mode="json"), "result.schema.json": ControlResult.model_json_schema(),
                 "environment.json": {"execution": "Python >=3.11; standard library only", "verification": "Install controlomics " + __version__ + "; the repository lock records the observed development dependencies", "planned_python": platform.python_version()}}
    with staged_directory(directory) as staged:
        for name, document in documents.items():
            (staged / name).write_bytes(canonical_json(document) + b"\n")
        (staged / "run_control.py").write_text(RUNNER, encoding="utf-8", newline="\n")
        (staged / "stats.py").write_text(stats_code, encoding="utf-8", newline="\n")
        (staged / "export_storage.py").write_text(storage_code, encoding="utf-8", newline="\n")
        (staged / "verify_results.py").write_text(VERIFIER, encoding="utf-8", newline="\n")
        files = tuple(documents) + ("run_control.py", "stats.py", "export_storage.py", "verify_results.py")
        hashes = {name: digest((staged / name).read_bytes()) for name in files}
        (staged / "manifest.json").write_bytes(canonical_json({"format": "controlomics.execution.v0.1", "code_sha256": code_hash,
            "artifact_hashes": hashes, "controlomics_version": __version__}) + b"\n")
        (staged / "README.md").write_text(
        "# Local control execution\n\nReview control.json, config.json, assumptions, and code before execution. "
        "Review the selected adapter and required CSV layout. Pair identifiers do not establish independence across pairs. This runner does not justify exchangeability. "
        "The numeric input stays local. No model-generated code is executed.\n\n"
        "Run: `python run_control.py --input input.csv --output results.json`.\n\n"
        "Verify with the installed package: `python verify_results.py results.json`.\n\n"
        "Import: `controlomics import-results project.json results.json --output updated.project.json`.\n\n"
        "The output must differ from the input and all package files. Complete result files use staged replacement; "
        "interrupted writes do not imply a completed result. The saved project snapshot should be retained separately. Artifact hashes detect changes relative to this manifest; "
        "they do not authenticate a maliciously replaced manifest or prove execution occurred.\n", encoding="utf-8", newline="\n")
    return updated


def import_result(project, result: ControlResult):
    plan = next((item for item in project.execution_plans if item.execution_id == result.execution_id), None)
    if plan is None:
        raise ValueError("result does not match a known execution plan")
    if any(item.result_id == result.result_id or item.execution_id == result.execution_id for item in project.results):
        raise ValueError("an execution result is already imported")
    code_versions = [item.version for item in result.software_versions if item.name == "controlomics_fixed_runner"]
    if plan.code_sha256 is not None and code_versions != [plan.code_sha256]:
        raise ValueError("result runner hash differs from the planned code")
    controls = tuple(item.model_copy(update={"execution_status": result.execution_status}) if item.control_id == result.control_id else item for item in project.controls)
    return replace_project(project, controls=controls, results=project.results + (result,),
        provenance=project.provenance + (event("EXECUTION_RESULT_IMPORT", [result.result_id, result.control_id, result.execution_id]),))


LOCAL_RESAMPLING_BUDGET = 4_000_000
LOCAL_EXECUTION_TIMEOUT = 35


class LocalExecutionError(ValueError):
    """A fixed public failure reason that contains no input values or paths."""

    MESSAGES = {
        "LOCAL_RESAMPLING_BUDGET": "Local resampling budget exceeded. Reduce the number of draws or use a dispatched execution package.",
        "LOCAL_EXECUTION_TIMEOUT": "Local execution exceeded its time limit. Reduce the workload or use a dispatched execution package. No result was imported.",
    }

    def __init__(self, code):
        self.code = code
        super().__init__(self.MESSAGES[code])


def execute_local(project, control_id, config, raw_input: bytes):
    # Only this fixed, hash-checked template is executable. Model text is never code.
    parsed = (statistics.read_paired_bytes if config.adapter == "PAIRED_DIFFERENCE" else statistics.read_numeric_bytes)(raw_input)
    units = len(parsed) if config.adapter == "PAIRED_DIFFERENCE" else len(parsed[0])
    if config.kind != "REFERENCE" and units * config.draws > LOCAL_RESAMPLING_BUDGET:
        raise LocalExecutionError("LOCAL_RESAMPLING_BUDGET")
    with TemporaryDirectory(prefix="controlomics_execution_") as temporary:
        folder = Path(temporary) / "package"
        updated = build_package(project, control_id, config, folder, pathway="LOCAL")
        input_path, result_path = Path(temporary) / "input.csv", Path(temporary) / "result.json"
        input_path.write_bytes(raw_input)
        try:
            process = subprocess.run([sys.executable, str(folder / "run_control.py"), "--input", str(input_path),
                "--output", str(result_path)], capture_output=True, text=True, timeout=LOCAL_EXECUTION_TIMEOUT, check=False)
        except subprocess.TimeoutExpired:
            raise LocalExecutionError("LOCAL_EXECUTION_TIMEOUT") from None
        if process.returncode != 0:
            raise ValueError("fixed-template local control execution failed")
        content = result_path.read_bytes()
        decode_json(content)
        return import_result(updated, ControlResult.model_validate_json(content))
