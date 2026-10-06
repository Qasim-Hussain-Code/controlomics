"""Measure the small local validation workload and on-disk project files."""

import ctypes
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from controlomics.project import export_json_schemas, load_project
from controlomics.execution import ExecutionConfig, execute_local, specify_paired_control
from controlomics.artifacts import create_review_bundle, open_review_bundle
from controlomics.reports import render_report
from controlomics.workflow import audit_project, propose, replace_project, review_methods
from controlomics.formats import export_workflow_schemas
from controlomics.evaluation import EvaluationBundle, evaluate


def peak_memory_bytes():
    if os.name != "nt":
        return None
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in (
                "peak_working_set", "working_set", "peak_paged_pool", "paged_pool",
                "peak_nonpaged_pool", "nonpaged_pool", "pagefile", "peak_pagefile",
            )
        ]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        return None
    return counters.peak_working_set


def main():
    root = Path(__file__).resolve().parents[1]
    for name in ("transcriptomics.project.json", "microscopy_ml.project.json"):
        original = load_project(root / "examples" / name)
        project = review_methods(propose(replace_project(original, candidates=())))
        project = execute_local(project, project.controls[0].control_id,
            ExecutionConfig(kind="REFERENCE", expected_difference=2.0, assumptions=("Synthetic resource measurement only.",)),
            (root / "examples" / "positive_reference.csv").read_bytes())
        render_report(audit_project(project))
    with TemporaryDirectory() as temporary:
        export_json_schemas(Path(temporary))
        export_workflow_schemas(Path(temporary) / "workflow")
    evaluation = EvaluationBundle.model_validate_json((root / "examples" / "benchmark.design.unassessed.json").read_bytes())
    evaluate(evaluation)
    project = specify_paired_control(project, project.claims[0].claim_id, "Hypothetical complete pairs for resource measurement.", ("Synthetic independent pairs and sign-invariant null.",))
    project = execute_local(project, project.controls[-1].control_id, ExecutionConfig.model_validate_json((root / "examples" / "paired_execution.json").read_bytes()),
        (root / "examples" / "paired_reference.csv").read_bytes())
    open_review_bundle(create_review_bundle(project, evaluation=evaluation))
    project_bytes = 0
    for path in root.rglob("*"):
        parts = path.relative_to(root).parts
        if any(part in (".venv", ".git", "__pycache__", "build", "dist", "local_projects", "data", "cache") or part.endswith(".egg-info") for part in parts):
            continue
        if path.is_file():
            project_bytes += path.stat().st_size
    environment_bytes = sum(path.stat().st_size for path in (root / ".venv").rglob("*") if path.is_file())
    print(json.dumps({
        "workload": "Two local project validations, method reviews, fixed synthetic reference executions, audits and reports, ten core and eighteen workflow schema exports, six-case unassessed evaluation, paired sign-flip execution, and review archive roundtrip",
        "project_file_bytes": project_bytes,
        "virtual_environment_file_bytes": environment_bytes,
        "peak_python_working_set_bytes": peak_memory_bytes(),
        "notes": "Project file sizes exclude Git, bytecode, builds and local research artifacts; peak memory describes this parent Python process only, not subprocesses or the browser.",
    }, indent=2))


if __name__ == "__main__":
    main()
