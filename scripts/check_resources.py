"""Measure the small local validation workload and on-disk project files."""

import ctypes
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from controlomics.project import export_json_schemas, load_project


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
        load_project(root / "examples" / name)
    with TemporaryDirectory() as temporary:
        export_json_schemas(Path(temporary))
    project_bytes = 0
    for path in root.rglob("*"):
        parts = path.relative_to(root).parts
        if any(part in (".venv", ".git", "__pycache__") or part.endswith(".egg-info") for part in parts):
            continue
        if path.is_file():
            project_bytes += path.stat().st_size
    environment_bytes = sum(path.stat().st_size for path in (root / ".venv").rglob("*") if path.is_file())
    print(json.dumps({
        "workload": "Two local example validations and ten schema exports",
        "project_file_bytes": project_bytes,
        "virtual_environment_file_bytes": environment_bytes,
        "peak_python_working_set_bytes": peak_memory_bytes(),
        "notes": "File sizes exclude Git and bytecode; peak memory describes this process only.",
    }, indent=2))


if __name__ == "__main__":
    main()
