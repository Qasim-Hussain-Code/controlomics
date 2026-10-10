"""Public-source checks reject sensitive artifacts without printing their values."""

import contextlib
import io
import json
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.check_release import path_problem, png_findings, text_findings
from scripts.export_public_source import main as export_source
from scripts.build_distributions import main as build_distributions


class ReleaseHygieneTests(unittest.TestCase):
    def test_distribution_builder_rejects_image_metadata_before_build(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            metadata = b'Author\0Synthetic identifying metadata'
            raw = b'\x89PNG\r\n\x1a\n' + len(metadata).to_bytes(4, 'big') + b'tEXt' + metadata + b'\0'*4
            (root / 'image.png').write_bytes(raw)
            with patch('scripts.build_distributions.ROOT', root), patch('scripts.build_distributions.source_files', return_value=['image.png']), self.assertRaises(ValueError):
                build_distributions()
            self.assertEqual(list(root.iterdir()), [root / 'image.png'])

    def test_source_export_failure_preserves_prior_archive_and_record(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "pyproject.toml").write_text('[project]\nversion = "0.0.dev0"\n', encoding="utf-8")
            (root / "README.md").write_text("Synthetic public source\n", encoding="utf-8")
            private = root / "late.txt"
            private.write_text("person" + "@" + "private.invalid", encoding="utf-8")
            archive, record = root / "dist" / "source.zip", root / "dist" / "record.json"
            archive.parent.mkdir()
            archive.write_bytes(b"retained archive")
            record.write_bytes(b"retained record")
            with patch("scripts.export_public_source.ROOT", root), patch("scripts.export_public_source.source_files", return_value=["README.md", "late.txt"]):
                with self.assertRaises(ValueError):
                    export_source(["--output", str(archive), "--record", str(record)])
            self.assertEqual(archive.read_bytes(), b"retained archive")
            self.assertEqual(record.read_bytes(), b"retained record")
            self.assertFalse(list(archive.parent.glob(".controlomics_*.tmp")))

    def test_source_export_binds_complete_bytes_and_rejects_path_conflicts(self):
        with TemporaryDirectory() as temporary, contextlib.redirect_stdout(io.StringIO()):
            root = Path(temporary)
            (root / "pyproject.toml").write_text('[project]\nversion = "0.0.dev0"\n', encoding="utf-8")
            readme = root / "README.md"
            readme.write_text("Synthetic public source\n", encoding="utf-8")
            archive, record = root / "dist" / "source.zip", root / "dist" / "record.json"
            with patch("scripts.export_public_source.ROOT", root), patch("scripts.export_public_source.source_files", return_value=["README.md"]):
                export_source(["--output", str(archive), "--record", str(record)])
                self.assertEqual(json.loads(record.read_bytes())["files"], 1)
                with zipfile.ZipFile(archive) as package:
                    self.assertEqual(package.read("controlomics-0.0.dev0/README.md"), readme.read_bytes())
                before = archive.read_bytes()
                for output, metadata in ((archive, archive), (readme, record), (archive, readme)):
                    with self.assertRaises(ValueError):
                        export_source(["--output", str(output), "--record", str(metadata)])
                self.assertEqual(archive.read_bytes(), before)
                self.assertEqual(readme.read_text(encoding="utf-8"), "Synthetic public source\n")

    def test_sensitive_paths_and_unknown_datasets_are_rejected(self):
        for name in ('local_projects/private.json', '.env', '.aws/credentials',
                     'data/measurements.csv', 'examples/private.csv', '../escape',
                     'notes/secret.pem', 'private/sample.h5ad'):
            with self.subTest(name=name):
                self.assertIsNotNone(path_problem(name))
        self.assertIsNone(path_problem('examples/positive_reference.csv'))
        self.assertIsNone(path_problem('docs/NUMERICAL_VALIDATION.md'))

    def test_credentials_and_personal_details_are_reported_without_values(self):
        samples = [('ghp_' + 'a'*36, 'github_token'),
                   ('AKIA' + 'A'*16, 'aws_access_key'),
                   ('sk-' + 'b'*40, 'provider_key'),
                   ('-----BEGIN ' + 'PRIVATE KEY-----', 'private_key'),
                   ('person' + '@' + 'private.invalid', 'email_address'),
                   ('C:' + '\\Users\\' + 'SyntheticPerson\\file', 'personal_home_path')]
        for value, rule in samples:
            with self.subTest(rule=rule):
                findings = text_findings('public line\n' + value)
                self.assertEqual(findings, [{'rule': rule, 'line': 2}])
                self.assertNotIn(value, str(findings))
        self.assertEqual(text_findings('synthetic@example.org'), [])

    def test_image_metadata_and_truncated_chunks_are_rejected(self):
        signature = b'\x89PNG\r\n\x1a\n'
        def chunk(kind, raw):
            return len(raw).to_bytes(4, 'big') + kind + raw + b'\0'*4
        self.assertEqual(png_findings(signature + chunk(b'tEXt', b'Author\0Synthetic person')),
                         [{'rule': 'image_metadata'}])
        self.assertEqual(png_findings(signature + b'\0'), [{'rule': 'invalid_png'}])
        self.assertEqual(png_findings(signature + chunk(b'IEND', b'')), [])


if __name__ == '__main__':
    unittest.main()
