import contextlib
import io
import json
import socket
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pydantic import ValidationError

from controlomics.cli import main
from controlomics.project import parse_project_json
from controlomics.schemas import InputRequirement
from tests.fixtures import ROOT, payload


class PrivacyTests(unittest.TestCase):
    def test_numeric_values_are_not_boolean_privacy_flags(self):
        for value in (0, 0.0, "false"):
            data = payload()
            data["privacy"]["network_enabled"] = value
            with self.subTest(value=value), self.assertRaises(ValidationError):
                parse_project_json(json.dumps(data))
        for value in (1, 1.0, "true"):
            data = payload()
            data["candidates"][0]["privacy_requirements"]["raw_data_must_remain_local"] = value
            with self.subTest(value=value), self.assertRaises(ValidationError):
                parse_project_json(json.dumps(data))

    def test_privacy_classification_cannot_understate_inputs_or_controls(self):
        data = payload()
        control = data["candidates"][0]
        control["required_inputs"][0]["privacy_class"] = "RESTRICTED"
        with self.assertRaises(ValidationError):
            parse_project_json(json.dumps(data))
        control["privacy_requirements"]["classification"] = "RESTRICTED"
        with self.assertRaises(ValidationError):
            parse_project_json(json.dumps(data))
        data["privacy"]["classification"] = "RESTRICTED"
        parse_project_json(json.dumps(data))

    def test_outbound_flags_fail_closed(self):
        for mutate in (
            lambda data: data["privacy"].update(network_enabled=True),
            lambda data: data["candidates"][0]["privacy_requirements"].update(external_transmission_allowed=True),
            lambda data: data["candidates"][0]["privacy_requirements"].update(raw_data_must_remain_local=False),
        ):
            data = payload()
            mutate(data)
            with self.assertRaises(ValidationError):
                parse_project_json(json.dumps(data))

    def test_unspecified_input_classification_is_restricted(self):
        requirement = InputRequirement(input_id="local", description="Unclassified input", format="local table")
        self.assertEqual(requirement.privacy_class, "RESTRICTED")

    def test_validation_and_schema_export_work_with_sockets_denied(self):
        with patch.object(socket.socket, "connect", side_effect=AssertionError("Unexpected network access")):
            with patch("socket.create_connection", side_effect=AssertionError("Unexpected network access")):
                with TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["validate", str(ROOT / "examples" / "transcriptomics.project.json")]), 0)
                    self.assertEqual(main(["export-schemas", directory]), 0)

    def test_errors_do_not_disclose_values_keys_or_paths(self):
        sentinel = "private_sentinel_9a1f"
        data = payload()
        data[sentinel] = "credential_like_synthetic_secret"
        with TemporaryDirectory() as directory:
            path = Path(directory) / f"{sentinel}.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["validate", str(path)]), 1)
            self.assertNotIn(sentinel, output.getvalue())
            self.assertNotIn("credential_like_synthetic_secret", output.getvalue())
            self.assertNotIn(directory, output.getvalue())

    def test_missing_file_error_is_redacted(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "private_path.json"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["validate", str(path)]), 1)
            self.assertNotIn(str(path), output.getvalue())

    def test_provenance_cannot_store_arbitrary_raw_prompts(self):
        data = payload()
        data["provenance"] = [{
            "provenance_id": "provenance.test", "action": "SCHEMA_VALIDATION",
            "recorded_at": "2026-10-05T01:00:00Z", "controlomics_version": "0.1.0.dev0",
            "record_ids": [data["analysis"]["analysis_id"]], "raw_prompt": "Synthetic restricted content",
        }]
        with self.assertRaises(ValidationError):
            parse_project_json(json.dumps(data))
