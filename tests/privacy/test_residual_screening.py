"""Synthetic privacy regressions for residue variants and contextual labels."""

import contextlib
import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from controlomics.cli import main
from controlomics.privacy import SafeField, screen_text
from controlomics.server import handle_action
from tests.fixtures import ROOT


def protein(length, residue, position):
    # A generated alphabet fixture, not a supplied biological sequence.
    sequence = ("ACDEFGHIKLMNPQRSTVWY" * ((length + 19) // 20))[:length]
    return sequence[:position] + residue + sequence[position + 1:]


def restricted_samples():
    for residue, length in (("U", 230), ("X", 120), ("U", 60), ("X", 60)):
        for position in (0, length // 2, length - 1):
            yield protein(length, residue, position)
    for label in ("Password", "PASSWORD", "pAsSwOrD", "API_KEY", "Api Key", "API-KEY", "Token", "TOKEN"):
        for separator in (": ", "="):
            yield label + separator + "synthetic_fixture_only"
    for label in ("Patient ID", "PATIENT_ID", "Subject Identifier", "CLINICAL-NUMBER",
            "Medical record number", "MEDICAL_RECORD_ID", "Medical-Record-Identifier"):
        for separator in (": ", "="):
            yield label + separator + "synthetic_identifier_only"


class ResidualScreeningTests(unittest.TestCase):
    def test_rare_or_unknown_residue_does_not_hide_long_protein_token(self):
        for residue, length in (("U", 230), ("X", 120), ("U", 60), ("X", 60)):
            for position in (0, length // 2, length - 1):
                token = protein(length, residue, position)
                for text in (token, "sequence_" + token, "Sequence: [" + token + "]"):
                    with self.subTest(residue=residue, length=length, position=position):
                        self.assertEqual(screen_text(text), "RESTRICTED")
                        with self.assertRaisesRegex(ValueError, "privacy screening"):
                            SafeField("claim", text, "SAFE")

    def test_credential_and_identifier_labels_are_case_insensitive(self):
        for index, text in enumerate(restricted_samples()):
            with self.subTest(index=index):
                self.assertEqual(screen_text(text), "RESTRICTED")
                for field in ("claim", "public_query"):
                    with self.assertRaisesRegex(ValueError, "privacy screening"):
                        SafeField(field, text, "SAFE")

    def test_protein_extension_preserves_nucleotide_and_protein_thresholds(self):
        for length in (60, 76, 79):
            text = ("ACGU" * 20)[:length]
            self.assertEqual(screen_text(text), "SENSITIVE_SCIENTIFIC")
            self.assertEqual(SafeField("claim", text, "SAFE").value, text)
        self.assertEqual(screen_text("ACGU" * 20), "RESTRICTED")
        for residue in ("U", "X"):
            self.assertEqual(screen_text(protein(59, residue, 29)), "SENSITIVE_SCIENTIFIC")
            self.assertEqual(screen_text(protein(60, residue, 30)), "RESTRICTED")

    def test_context_words_and_short_residue_names_are_not_secret_values(self):
        texts = ("Password handling and token approval are reviewed locally.",
            "The API key remains outside model context.",
            "Patient ID and medical record number are field names in this hypothetical description.",
            "Protein residue U and an unknown residue X require appropriate annotation.",
            "A standard sequence accession is a public bibliographic identifier.")
        for text in texts:
            self.assertEqual(screen_text(text), "SENSITIVE_SCIENTIFIC")
            self.assertEqual(SafeField("claim", text, "SAFE").value, text)

    def test_model_and_literature_previews_reject_before_network_or_transport(self):
        with patch("socket.getaddrinfo") as lookup, patch("socket.create_connection") as connect, \
                patch("controlomics.privacy.SafeTransport.send") as send:
            for index, text in enumerate(restricted_samples()):
                with self.subTest(index=index):
                    with self.assertRaisesRegex(ValueError, "privacy screening"):
                        handle_action("/api/model/preview", {"fields": {"claim": text},
                            "public_confirmed": True, "endpoint": "https://model.example/v1/chat/completions",
                            "model": "synthetic-fixture"})
                    with self.assertRaisesRegex(ValueError, "privacy screening"):
                        handle_action("/api/literature/preview", {"query": text,
                            "public_confirmed": True, "provider": "europepmc"})
            lookup.assert_not_called()
            connect.assert_not_called()
            send.assert_not_called()

    def test_cli_screening_rejects_without_preview_echo_or_outputs(self):
        with TemporaryDirectory() as temporary, patch("socket.getaddrinfo") as lookup, \
                patch("socket.create_connection") as connect, patch("controlomics.privacy.SafeTransport.send") as send:
            directory = Path(temporary)
            context, output, audit = [directory / name for name in ("context.json", "output.json", "audit.json")]
            for index, text in enumerate(restricted_samples()):
                context.write_text(json.dumps({"claim": text}), encoding="utf-8")
                console = io.StringIO()
                with self.subTest(index=index), contextlib.redirect_stdout(console):
                    self.assertEqual(main(["model-propose", str(ROOT / "examples/transcriptomics.project.json"),
                        "--context", str(context), "--endpoint", "https://model.example/v1/chat/completions",
                        "--model", "synthetic-fixture", "--output", str(output), "--audit-output", str(audit)]), 1)
                self.assertNotIn(text, console.getvalue())
                self.assertNotIn(str(context), console.getvalue())
                self.assertFalse(output.exists())
                self.assertFalse(audit.exists())
            lookup.assert_not_called()
            connect.assert_not_called()
            send.assert_not_called()
