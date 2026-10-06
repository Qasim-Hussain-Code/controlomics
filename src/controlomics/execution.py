"""Reviewed fixed templates for small, local, independent-unit numeric controls."""

from __future__ import annotations

import json
import math
import platform
import subprocess
import sys
from tempfile import TemporaryDirectory
import uuid
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, model_validator

from controlomics import __version__
from controlomics import statistics
from controlomics.privacy import canonical_json, digest
from controlomics.project import decode_json, save_project
from controlomics.schemas import (
    ControlResult, DecisionRule, ExecutionPlan, InputRequirement, PrivacyPolicy, PrivacyRequirements,
    Record, SoftwareVersion, Text,
)
from controlomics.workflow import event, now, replace_project


class ExecutionConfig(Record):
    kind: Literal["REFERENCE", "PERMUTATION", "BOOTSTRAP"]
    assumptions: Annotated[tuple[Text, ...], Field(min_length=1)]
    random_seed: Annotated[int, Field(ge=0)] = 0
    draws: Annotated[int, Field(ge=100, le=10000)] = 999
    coverage: Annotated[float, Field(gt=0, lt=1, allow_inf_nan=False)] = 0.95
    expected_difference: Annotated[float, Field(allow_inf_nan=False)] | None = None
    absolute_tolerance: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 1e-9

    @model_validator(mode="after")
    def reference_value(self):
        if self.kind == "REFERENCE" and self.expected_difference is None:
            raise ValueError("a reference check requires an independently prespecified expected difference")
        if self.kind != "REFERENCE" and self.expected_difference is not None:
            raise ValueError("inferential controls do not use an automatic reference pass rule")
        return self


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
    from stats import read_numeric_bytes, mean_difference, permutation_test, bootstrap_difference
    started = datetime.now(timezone.utc).isoformat()
    with args.input.open("rb") as stream:
        raw_input = stream.read(2 * 1024 * 1024 + 1)
    values, labels = read_numeric_bytes(raw_input)
    effect = mean_difference(values, labels)
    output = {
        "schema_version": "0.1.0", "result_id": plan["execution_id"] + ".result",
        "control_id": plan["control_id"], "execution_id": plan["execution_id"],
        "execution_status": "COMPLETED", "started_at": started,
        "software_versions": [{"name": "Python", "version": platform.python_version()},
                              {"name": "controlomics_fixed_runner", "version": manifest["code_sha256"]}],
        "random_seed": plan["random_seed"],
        "input_hashes": [{"input_id": "numeric_units", "sha256": hashlib.sha256(raw_input).hexdigest()}],
        "effect_estimate": {"name": "mean(label=1)-mean(label=0)", "value": effect},
        "outcome": "INDETERMINATE", "warnings": ["Sampling independence and applicability are researcher-supplied assumptions."],
        "interpretive_metadata": config["assumptions"],
        "interpretation": "The numeric result alone does not establish biological validity or absence of an effect.",
    }
    if config["kind"] == "REFERENCE":
        passed = abs(effect - config["expected_difference"]) <= config["absolute_tolerance"]
        output.update(outcome="PASS" if passed else "FAIL", decision_rule_id=plan["decision_rule"]["rule_id"],
                      interpretation="Prespecified technical reference calculation " + ("matched" if passed else "did not match") + " its expected output. This does not establish the biological claim.")
    elif config["kind"] == "PERMUTATION":
        result = permutation_test(values, labels, seed=config["random_seed"], draws=config["draws"])
        output.update(p_value=result["p_value"],
            test_statistic={"name": "absolute mean difference", "value": abs(effect)},
            null_distribution_summary={"draws": result["draws"], "mean": result["null_mean"],
                "standard_deviation": result["null_sd"], "null_hypothesis": "Group labels are exchangeable for the tested mean-difference null.",
                "exchangeability_assumptions": config["assumptions"]})
        output["warnings"].append("Exact enumeration" if result["exact"] else "Monte Carlo p value uses the plus-one correction.")
        output["warnings"].append("Numerical tail comparisons use a relative tolerance of 1e-12 with zero absolute tolerance.")
    else:
        result = bootstrap_difference(values, labels, seed=config["random_seed"], draws=config["draws"], coverage=config["coverage"])
        output["confidence_interval"] = {"lower": result["lower"], "upper": result["upper"],
            "coverage": result["coverage"], "method": "Within-group percentile bootstrap with linear quantile interpolation"}
        output["warnings"].append("Percentile intervals can have poor coverage for small, biased, or dependent samples.")
    output["completed_at"] = datetime.now(timezone.utc).isoformat()
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\\n", encoding="utf-8")
    print("Wrote a local numeric control result; raw input values were not printed.")

if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, OverflowError):
        print("Execution failed; input values and local paths are omitted.")
        raise SystemExit(1)
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
    if directory.exists() and any(directory.iterdir()):
        raise ValueError("execution package directory must be new or empty")
    if any(plan.control_id == control_id for plan in project.execution_plans):
        raise ValueError("control already has an execution plan; create a separate project snapshot for a new run")
    directory.mkdir(parents=True, exist_ok=True)
    stats_code = Path(statistics.__file__).read_text(encoding="utf-8").replace("\r\n", "\n")
    code_hash = digest(RUNNER.encode() + stats_code.encode())
    inputs = (InputRequirement(input_id="numeric_units", description="Independent numeric units with group labels; raw data remain local.",
                               format="UTF-8 CSV with columns unit,label,value; labels 0 or 1", privacy_class="RESTRICTED"),)
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
        decision_rule=rule, parameters=("Configuration sha256: " + digest(canonical_json(config.model_dump(mode="json"))),),
        instructions="Run the fixed local runner on independent-unit numeric input, verify the result, then import it into the saved project.",
        limitations=("Only small, two-group independent-unit numeric controls are executable by this adapter. Paired, clustered, covariate-adjusted, and full primary analyses are outside this adapter.",))
    updated = replace_project(project, controls=tuple(control if item.control_id == control_id else item for item in project.controls),
        privacy=PrivacyPolicy(rationale="Project includes restricted numeric input requirements; data remain local."),
        execution_plans=project.execution_plans + (plan,),
        provenance=project.provenance + (event("CONTROL_REVIEW", [control_id, plan.execution_id]),))
    documents = {"config.json": config.model_dump(mode="json"), "execution_plan.json": plan.model_dump(mode="json"),
                 "control.json": control.model_dump(mode="json"), "result.schema.json": ControlResult.model_json_schema(),
                 "environment.json": {"execution": "Python >=3.11; standard library only", "verification": "Install controlomics " + __version__ + "; the repository lock records the observed development dependencies", "planned_python": platform.python_version()}}
    for name, document in documents.items():
        (directory / name).write_bytes(canonical_json(document) + b"\n")
    (directory / "run_control.py").write_text(RUNNER, encoding="utf-8", newline="\n")
    (directory / "stats.py").write_text(stats_code, encoding="utf-8", newline="\n")
    (directory / "verify_results.py").write_text(VERIFIER, encoding="utf-8", newline="\n")
    files = tuple(documents) + ("run_control.py", "stats.py", "verify_results.py")
    hashes = {name: digest((directory / name).read_bytes()) for name in files}
    (directory / "manifest.json").write_bytes(canonical_json({"format": "controlomics.execution.v0.1", "code_sha256": code_hash,
        "artifact_hashes": hashes, "controlomics_version": __version__}) + b"\n")
    (directory / "README.md").write_text(
        "# Local control execution\n\nReview control.json, config.json, assumptions, and code before execution. "
        "Rows must represent independent units; this runner does not correct dependence or justify exchangeability. "
        "The numeric input stays local. No model-generated code is executed.\n\n"
        "Run: `python run_control.py --input input.csv --output results.json`.\n\n"
        "Verify with the installed package: `python verify_results.py results.json`.\n\n"
        "Import: `controlomics import-results project.json results.json --output updated.project.json`.\n\n"
        "The saved project snapshot should be retained separately. Artifact hashes detect changes relative to this manifest; "
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


def execute_local(project, control_id, config, raw_input: bytes):
    # Only this fixed, hash-checked template is executable. Model text is never code.
    statistics.read_numeric_bytes(raw_input)
    with TemporaryDirectory(prefix="controlomics_execution_") as temporary:
        folder = Path(temporary) / "package"
        updated = build_package(project, control_id, config, folder, pathway="LOCAL")
        input_path, result_path = Path(temporary) / "input.csv", Path(temporary) / "result.json"
        input_path.write_bytes(raw_input)
        process = subprocess.run([sys.executable, str(folder / "run_control.py"), "--input", str(input_path),
            "--output", str(result_path)], capture_output=True, text=True, timeout=35, check=False)
        if process.returncode != 0:
            raise ValueError("fixed-template local control execution failed")
        content = result_path.read_bytes()
        decode_json(content)
        return import_result(updated, ControlResult.model_validate_json(content))
