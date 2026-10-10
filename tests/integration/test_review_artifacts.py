import base64
import io
import json
import unittest
import warnings
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from controlomics.artifacts import create_review_bundle, open_review_bundle
from controlomics.evaluation import (AnnotationSubmission, EvaluationBundle, apply_annotations, bundle_hash,
    annotation_template, evaluate)
from controlomics.privacy import PreparedRequest, SafeField, canonical_json, digest
from controlomics.project import parse_project_json
from controlomics.server import handle_action
from tests.fixtures import payload
from tests.scientific.test_evaluation import bundle_payload


class ReviewArtifactsTests(unittest.TestCase):
    def project(self):
        return parse_project_json(json.dumps(payload()))

    def evaluation(self):
        return EvaluationBundle.model_validate_json(json.dumps(bundle_payload()))

    def archive_changed(self, raw, name, content, update_hash=False, extra=None):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            documents = {item: archive.read(item) for item in archive.namelist()}
        documents[name] = content
        if update_hash:
            manifest = json.loads(documents['manifest.json'])
            manifest['artifacts'][name] = {'sha256': digest(content), 'bytes': len(content)}
            documents['manifest.json'] = canonical_json(manifest)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for item, value in documents.items():
                archive.writestr(item, value)
            if extra:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    archive.writestr(*extra)
        return buffer.getvalue()

    def test_archive_roundtrip_optional_evaluation_and_ledger(self):
        request = PreparedRequest('LITERATURE', 'GET', 'https://api.crossref.org/works/10.1000%2Fexample',
            (SafeField('public_identifier', '10.1000/example', 'SAFE'),))
        ledger = [{**request.preview(), 'request_sha256': request.approval_hash, 'sent_at': '2026-10-06T01:00:00Z',
            'status': 'FAILED', 'body_sha256': None, 'credential_supplied': False, 'payload_transmission': 'NOT_STARTED'}]
        project, restored, evaluation, revisions, manifest = open_review_bundle(create_review_bundle(self.project(), ledger, self.evaluation()))
        self.assertEqual(project, self.project())
        self.assertEqual(restored[0]['request_sha256'], request.approval_hash)
        self.assertEqual(evaluation, self.evaluation())
        self.assertEqual(revisions, [])
        self.assertIn('report.html', manifest.artifacts)
        result = handle_action('/api/open-bundle', {'archive_base64': base64.b64encode(create_review_bundle(project)).decode()})
        self.assertEqual(result['project']['manifest']['project_id'], project.manifest.project_id)

    def test_changed_content_rejected(self):
        raw = create_review_bundle(self.project())
        with self.assertRaises(ValueError):
            open_review_bundle(self.archive_changed(raw, 'project.json', b'{}'))

    def test_duplicate_traversal_unknown_and_symlink_members_rejected(self):
        raw = create_review_bundle(self.project())
        for name in ('../outside.json', 'credentials.json', 'project.json'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                open_review_bundle(self.archive_changed(raw, 'report.html', b'harmless', extra=(name, b'x')))
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            documents = {item: archive.read(item) for item in archive.namelist()}
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            for name, value in documents.items():
                info = zipfile.ZipInfo(name)
                if name == 'report.html':
                    info.create_system = 3
                    info.external_attr = (0o120777 << 16)
                archive.writestr(info, value)
        with self.assertRaises(ValueError):
            open_review_bundle(buffer.getvalue())

    def test_oversized_expansion_and_malformed_archive_rejected(self):
        raw = create_review_bundle(self.project())
        with self.assertRaises(ValueError):
            open_review_bundle(self.archive_changed(raw, 'report.html', b'x' * (4 * 1024 * 1024 + 1)))
        with self.assertRaises(ValueError):
            open_review_bundle(b'not a zip archive')

    def test_imported_html_not_used_as_report(self):
        raw = create_review_bundle(self.project())
        changed = self.archive_changed(raw, 'report.html', b'<script>untrusted()</script>', update_hash=True)
        project, ledger, *_ = open_review_bundle(changed)
        with zipfile.ZipFile(io.BytesIO(create_review_bundle(project, ledger))) as archive:
            self.assertNotIn(b'untrusted()', archive.read('report.html'))

    def test_credentials_and_raw_body_rejected_from_ledger(self):
        for event in ({'Authorization': 'synthetic only'}, {'body': 'raw source'}):
            with self.assertRaises(ValueError):
                create_review_bundle(self.project(), [event])

    def submission(self, bundle, **changes):
        data = {'bundle_sha256': bundle_hash(bundle), 'judgment_origin': 'DEVELOPMENT_FIXTURE',
            'annotator': 'Synthetic software fixture', 'human_attested': True,
            'judgments': [item.model_dump(mode='json') for item in self.evaluation().judgments],
            'evidence_decisions': [item.model_dump(mode='json') for item in bundle.evidence_decisions]}
        data.update(changes)
        return AnnotationSubmission.model_validate_json(json.dumps(data))

    def test_annotation_binds_snapshot_and_preserves_predictions(self):
        source = self.evaluation()
        blank = annotation_template(source.dataset, source.predictions)
        updated, revision = apply_annotations(blank, self.submission(blank))
        self.assertEqual(updated.dataset, blank.dataset)
        self.assertEqual(updated.predictions, blank.predictions)
        self.assertEqual(evaluate(updated)['metrics']['recommendation_precision']['value'], 0.5)
        self.assertEqual(revision.previous_sha256, bundle_hash(blank))
        restored = open_review_bundle(create_review_bundle(self.project(), (), updated, [revision.model_dump(mode='json')]))
        self.assertEqual(restored[2], updated)

    def test_annotation_requires_actual_attestation_and_exact_snapshot(self):
        bundle = self.evaluation()
        with self.assertRaises(ValueError):
            self.submission(bundle, human_attested=False)
        with self.assertRaises(ValueError):
            apply_annotations(bundle, self.submission(bundle, bundle_sha256='0' * 64))
        with self.assertRaises(ValueError):
            self.submission(bundle, annotator='')

    def test_annotation_cannot_alter_predicted_evidence_decisions(self):
        bundle = self.evaluation()
        evidence = [item.model_dump(mode='json') for item in bundle.evidence_decisions]
        evidence[0]['predicted_decision'] = False
        with self.assertRaises(ValueError):
            apply_annotations(bundle, self.submission(bundle, evidence_decisions=evidence))

    def test_revision_chain_must_end_at_current_bundle(self):
        bundle = self.evaluation()
        _, revision = apply_annotations(bundle, self.submission(bundle))
        data = revision.model_dump(mode='json')
        data['updated_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            create_review_bundle(self.project(), (), bundle, [data])

    def test_cli_bundle_roundtrip_regenerates_report_and_rejects_overwrite(self):
        from contextlib import redirect_stdout
        from controlomics.cli import main
        from controlomics.project import load_project, save_project
        with TemporaryDirectory() as temporary, redirect_stdout(io.StringIO()):
            folder = Path(temporary)
            save_project(self.project(), folder / 'project.json')
            self.assertEqual(main(['bundle-export', str(folder / 'project.json'), '--output', str(folder / 'review.zip')]), 0)
            self.assertEqual(main(['bundle-import', str(folder / 'review.zip'), '--directory', str(folder / 'restored')]), 0)
            self.assertEqual(load_project(folder / 'restored' / 'project.json'), self.project())
            self.assertIn('Controlomics scientific audit', (folder / 'restored' / 'report.html').read_text(encoding='utf-8'))
            self.assertEqual(main(['bundle-import', str(folder / 'review.zip'), '--directory', str(folder / 'restored')]), 1)

    def test_failed_cli_restore_leaves_no_partial_records(self):
        from contextlib import redirect_stdout
        from controlomics.cli import main
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive, target = root / 'review.zip', root / 'restored'
            raw = create_review_bundle(self.project())
            archive.write_bytes(raw)
            output = io.StringIO()
            with redirect_stdout(output), patch('controlomics.cli.write_report', side_effect=OSError('private_sentinel')):
                self.assertEqual(main(['bundle-import', str(archive), '--directory', str(target)]), 1)
            self.assertNotIn('private_sentinel', output.getvalue())
            self.assertFalse(target.exists())
            self.assertEqual(list(root.iterdir()), [archive])
            self.assertEqual(archive.read_bytes(), raw)

    def test_cli_annotations_emit_revision_bound_to_output(self):
        from contextlib import redirect_stdout
        from controlomics.cli import main
        with TemporaryDirectory() as temporary, redirect_stdout(io.StringIO()):
            folder = Path(temporary)
            source = self.evaluation()
            (folder / 'bundle.json').write_text(source.model_dump_json(), encoding='utf-8')
            (folder / 'submission.json').write_text(self.submission(source).model_dump_json(), encoding='utf-8')
            self.assertEqual(main(['annotate', str(folder / 'bundle.json'), str(folder / 'submission.json'), '--output', str(folder / 'updated.json'), '--revision-output', str(folder / 'revision.json')]), 0)
            updated = EvaluationBundle.model_validate_json((folder / 'updated.json').read_bytes())
            self.assertEqual(json.loads((folder / 'revision.json').read_bytes())['updated_sha256'], bundle_hash(updated))

    def test_full_ledger_rejects_extra_headers_changed_query_and_inconsistent_receipt(self):
        request = PreparedRequest('LITERATURE', 'GET', 'https://api.crossref.org/works/10.1000%2Fexample',
            (SafeField('public_identifier', '10.1000/example', 'SAFE'),))
        event = {**request.preview(), 'request_sha256': request.approval_hash, 'sent_at': '2026-10-06T01:00:00Z',
            'status': 'FAILED', 'body_sha256': None, 'credential_supplied': False, 'payload_transmission': 'NOT_STARTED'}
        for changes in ({'Authorization': 'synthetic'}, {'body': 'synthetic'}, {'url': 'https://api.crossref.org/works/10.1000%2Fdifferent'},
            {'status': 'COMPLETED'}, {'response_sha256': '0' * 64, 'response_bytes': 1}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                create_review_bundle(self.project(), [{**event, **changes}])
