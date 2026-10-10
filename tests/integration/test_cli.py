import contextlib
import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from controlomics.cli import main
from tests.fixtures import ROOT


class CLITests(unittest.TestCase):
    def test_auxiliary_inputs_cannot_be_overwritten_by_exports(self):
        with TemporaryDirectory() as temporary, contextlib.redirect_stdout(io.StringIO()):
            target = Path(temporary) / "input.csv"
            original = (ROOT / "examples" / "positive_reference.csv").read_bytes()
            target.write_bytes(original)
            self.assertEqual(main(["inspect-input", str(target), "--output", str(target)]), 1)
            self.assertEqual(target.read_bytes(), original)
            config = Path(temporary) / "config.json"
            original = (ROOT / "examples" / "reference_execution.json").read_bytes()
            config.write_bytes(original)
            self.assertEqual(main(["execute", "absent.project.json", "--control-id", "fixture", "--config", str(config),
                "--input", str(target), "--output", str(config)]), 1)
            self.assertEqual(config.read_bytes(), original)

    def test_interrupted_command_returns_nonzero_and_retains_prior_output(self):
        with TemporaryDirectory() as temporary:
            target = Path(temporary) / "retained.json"
            target.write_bytes(b"retained")
            output = io.StringIO()
            with contextlib.redirect_stdout(output), patch("controlomics.cli.load_project", side_effect=KeyboardInterrupt()):
                self.assertEqual(main(["analyze", "absent.project.json", "--output", str(target)]), 130)
            self.assertIn("interrupted", output.getvalue())
            self.assertEqual(target.read_bytes(), b"retained")

    def test_offline_analyze_report_and_execute_commands(self):
        with TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            folder = Path(directory)
            project = folder / "project.json"
            intake_project = folder / "intake.project.json"
            self.assertEqual(main(["new", str(ROOT / "examples" / "hypothetical_intake.json"), "--output", str(intake_project)]), 0)
            self.assertEqual(main(["analyze", str(intake_project), "--output", str(project)]), 0)
            payload = json.loads(project.read_bytes())
            self.assertEqual(main(["execute", str(project), "--control-id", payload["controls"][0]["control_id"],
                "--config", str(ROOT / "examples" / "reference_execution.json"), "--input", str(ROOT / "examples" / "positive_reference.csv"),
                "--output", str(folder / "results.project.json")]), 0)
            self.assertEqual(main(["report", str(folder / "results.project.json"), "--output", str(folder / "report.html")]), 0)
            self.assertTrue((folder / "report.html").exists())

    def test_literature_preview_does_not_send_or_write_project(self):
        with TemporaryDirectory() as directory:
            output, audit = Path(directory) / "output.json", Path(directory) / "audit.json"
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = main(["retrieve", str(ROOT / "examples" / "transcriptomics.project.json"), "--query", "public method",
                    "--output", str(output), "--audit-output", str(audit)])
            self.assertEqual(code, 2)
            self.assertIn("No request sent", buffer.getvalue())
            self.assertFalse(output.exists())
            self.assertFalse(audit.exists())

    def test_model_context_must_be_an_object_and_failure_is_redacted(self):
        with TemporaryDirectory() as directory:
            context = Path(directory) / "context.json"
            context.write_text('["private_sentinel"]', encoding="utf-8")
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = main(["model-propose", str(ROOT / "examples" / "transcriptomics.project.json"),
                    "--context", str(context), "--endpoint", "https://model.example/v1/chat/completions", "--model", "fixture",
                    "--output", str(Path(directory)/"output.json"), "--audit-output", str(Path(directory)/"audit.json")])
            self.assertEqual(code, 1)
            self.assertNotIn("private_sentinel", buffer.getvalue())
            self.assertNotIn(str(context), buffer.getvalue())
