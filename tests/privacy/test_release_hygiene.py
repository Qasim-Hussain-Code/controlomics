"""Public-source checks reject sensitive artifacts without printing their values."""

import unittest

from scripts.check_release import path_problem, png_findings, text_findings


class ReleaseHygieneTests(unittest.TestCase):
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
