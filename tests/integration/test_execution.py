import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from controlomics.execution import ExecutionConfig, build_package, import_result
from controlomics.project import parse_project_json
from controlomics.schemas import ControlResult
from controlomics.workflow import audit_project, propose, review_methods
from tests.fixtures import ROOT, payload


class ExecutionTests(unittest.TestCase):
    def project(self):
        data = payload()
        data["candidates"] = []
        return review_methods(propose(parse_project_json(json.dumps(data))))

    def run_package(self, kind, expected=None):
        project = self.project()
        config = ExecutionConfig(kind=kind, assumptions=("Independent synthetic units for software tests.",),
                                 expected_difference=expected, draws=199)
        with TemporaryDirectory() as directory:
            folder = Path(directory) / "package"
            updated = build_package(project, project.controls[0].control_id, config, folder)
            result_path = folder / "result.json"
            process = subprocess.run([sys.executable, str(folder / "run_control.py"), "--input", str(ROOT / "examples" / "positive_reference.csv"),
                                      "--output", str(result_path)], capture_output=True, text=True, timeout=20)
            self.assertEqual(process.returncode, 0, process.stderr)
            result = ControlResult.model_validate_json(result_path.read_bytes())
            verification = subprocess.run([sys.executable, str(folder / "verify_results.py"), str(result_path)],
                capture_output=True, text=True, timeout=20)
            self.assertEqual(verification.returncode, 0, verification.stdout)
            updated = import_result(updated, result)
            return updated

    def test_reference_pass_and_failure_are_prespecified(self):
        passing = self.run_package("REFERENCE", 2.0)
        self.assertEqual(passing.results[0].outcome, "PASS")
        failing = self.run_package("REFERENCE", 3.0)
        self.assertEqual(failing.results[0].outcome, "FAIL")
        self.assertEqual(audit_project(failing).audits[0].assessment, "CONTROL_FAILURE")

    def test_permutation_does_not_declare_negative_control_pass(self):
        project = self.run_package("PERMUTATION")
        self.assertEqual(project.results[0].outcome, "INDETERMINATE")
        self.assertAlmostEqual(project.results[0].p_value, 0.2)

    def test_bootstrap_and_duplicate_result_guard(self):
        project = self.run_package("BOOTSTRAP")
        self.assertIsNotNone(project.results[0].confidence_interval)
        with self.assertRaises(ValueError):
            import_result(project, project.results[0])

    def test_tampered_code_is_not_executed(self):
        project = self.project()
        with TemporaryDirectory() as directory:
            folder = Path(directory) / "package"
            build_package(project, project.controls[0].control_id,
                ExecutionConfig(kind="REFERENCE", expected_difference=2.0, assumptions=("Synthetic units",)), folder)
            with (folder / "stats.py").open("a", encoding="utf-8") as stream:
                stream.write("\n# Changed artifact\n")
            process = subprocess.run([sys.executable, str(folder / "run_control.py"), "--input", str(ROOT / "examples" / "positive_reference.csv"),
                "--output", str(folder / "result.json")], capture_output=True, text=True, timeout=20)
            self.assertEqual(process.returncode, 1)
            self.assertFalse((folder / "result.json").exists())

    def test_result_verifier_rejects_forged_runner_binding(self):
        project = self.project()
        with TemporaryDirectory() as directory:
            folder = Path(directory) / "package"
            build_package(project, project.controls[0].control_id,
                ExecutionConfig(kind="REFERENCE", expected_difference=2.0, assumptions=("Synthetic units",)), folder)
            result_path = folder / "result.json"
            subprocess.run([sys.executable, str(folder / "run_control.py"), "--input", str(ROOT / "examples" / "positive_reference.csv"),
                "--output", str(result_path)], capture_output=True, check=True, timeout=20)
            result = json.loads(result_path.read_bytes())
            result["software_versions"][1]["version"] = "0" * 64
            result_path.write_text(json.dumps(result), encoding="utf-8")
            process = subprocess.run([sys.executable, str(folder / "verify_results.py"), str(result_path)],
                capture_output=True, text=True, timeout=20)
            self.assertEqual(process.returncode, 1)
            self.assertNotIn(str(result_path), process.stdout)
