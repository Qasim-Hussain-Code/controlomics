import base64
import io
import json
import threading
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from controlomics import execution, hosted
from controlomics.hosting_privacy import record_hosted_processing
from controlomics.inputs import NumericInputSummary
from controlomics.project import parse_project_json
from controlomics.server import SECURITY_HEADERS
from controlomics.workflow import propose_and_review_new
from tests.fixtures import ROOT, payload


ORIGIN = 'https://controlomics.example'
SECRET = b'Synthetic hosted session key for tests only.'


class UnreadBody:
    def read(self, *args):
        raise AssertionError('The rejected scientific body was read')


class Browser:
    def __init__(self, app):
        self.app, self.cookie, self.token = app, None, None

    def request(self, path, data=None, *, method=None, raw=None, overrides=None, stream=None):
        raw = raw if raw is not None else (json.dumps(data).encode() if data is not None else b'')
        method = method or ('POST' if data is not None or raw else 'GET')
        environ = {'REQUEST_METHOD': method, 'PATH_INFO': path, 'QUERY_STRING': '', 'SCRIPT_NAME': '',
                   'HTTP_HOST': 'controlomics.example', 'wsgi.url_scheme': 'https', 'REMOTE_ADDR': '127.0.0.1',
                   'wsgi.input': stream or io.BytesIO(raw), 'wsgi.errors': io.StringIO()}
        if self.cookie is not None:
            environ['HTTP_COOKIE'] = self.cookie
        if method == 'POST':
            environ.update({'HTTP_ORIGIN': ORIGIN, 'CONTENT_TYPE': 'application/json', 'CONTENT_LENGTH': str(len(raw))})
            if self.token is not None:
                environ['HTTP_X_CONTROLOMICS_TOKEN'] = self.token
        for name, value in (overrides or {}).items():
            if value is None:
                environ.pop(name, None)
            else:
                environ[name] = value
        response = {}

        def start(status, headers):
            response.update(status=int(status.split()[0]), headers=headers)

        body = b''.join(self.app(environ, start))
        headers = dict(response['headers'])
        if 'Set-Cookie' in headers:
            self.cookie = headers['Set-Cookie'].split(';', 1)[0]
        value = json.loads(body) if headers['Content-Type'] == 'application/json' and body else body
        if isinstance(value, dict) and 'token' in value:
            self.token = value['token']
        response.update(body=body, value=value, errors=environ['wsgi.errors'].getvalue())
        return response

    def consent(self):
        session = self.request('/api/session')
        if session['status'] != 200:
            raise AssertionError(session)
        return self.request('/api/hosting-consent', {'allowed': True, 'policy_revision': hosted.POLICY_REVISION})


class HostedTests(unittest.TestCase):
    def setUp(self):
        self.app = hosted.create_app(ORIGIN, SECRET)
        self.browser = Browser(self.app)

    def assert_security(self, response):
        for name, value in SECURITY_HEADERS:
            self.assertEqual(response['headers'].count((name, value)), 1)
        self.assertEqual(response['errors'], '')
        self.assertNotIn('Access-Control-Allow-Origin', dict(response['headers']))

    def test_configuration_requires_exact_https_origin_and_secret(self):
        for origin in ('http://controlomics.example', 'https://controlomics.example/', 'https://controlomics.example:443',
                       'https://user:password@example.invalid', 'https://controlomics.example?private=1',
                       'https://CONTROLomics.example', 'https://controlomics.example.', 'https://a..example'):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                hosted.create_app(origin, SECRET)
        for secret in (None, b'short', 3):
            with self.subTest(secret=secret), patch.dict('os.environ', {}, clear=True), self.assertRaises(ValueError):
                hosted.create_app(ORIGIN, secret)
        with patch.dict('os.environ', {'RENDER_EXTERNAL_URL': ORIGIN, 'CONTROLOMICS_SESSION_SECRET': SECRET.decode()}, clear=True):
            self.assertEqual(hosted.create_app().origin, ORIGIN)

    def test_internal_health_probe_exposes_no_session_or_input(self):
        browser = Browser(hosted.create_app(ORIGIN, SECRET, trust_proxy=True))
        for method in ('GET', 'HEAD'):
            response = browser.request('/healthz', method=method, stream=UnreadBody(), overrides={
                'wsgi.url_scheme': 'http', 'REMOTE_ADDR': '10.0.0.4'})
            self.assertEqual(response['status'], 200)
            self.assertNotIn('Set-Cookie', dict(response['headers']))
            self.assertEqual(response['value'], b'' if method == 'HEAD' else {'status': 'ok', 'mode': 'HOSTED_TEMPORARY'})
        self.assertIsNone(browser.cookie)
        self.assertIsNone(browser.token)
        self.assertEqual(browser.app._sessions, {})

    def test_internal_health_exception_does_not_open_other_routes(self):
        browser = Browser(hosted.create_app(ORIGIN, SECRET, trust_proxy=True))
        proxy = {'wsgi.url_scheme': 'http', 'REMOTE_ADDR': '10.0.0.4'}
        for path, method in (('/api/session', 'GET'), ('/', 'GET'), ('/api/analyze', 'POST'), ('/healthz', 'POST')):
            response = browser.request(path, method=method, stream=UnreadBody(), overrides=proxy)
            self.assertEqual(response['status'], 403)
        self.assertEqual(browser.app._sessions, {})

    def test_internal_health_rejects_wrong_host_public_peer_and_query(self):
        browser = Browser(hosted.create_app(ORIGIN, SECRET, trust_proxy=True))
        proxy = {'wsgi.url_scheme': 'http', 'REMOTE_ADDR': '10.0.0.4'}
        for change in ({'HTTP_HOST': 'other.example'}, {'REMOTE_ADDR': '8.8.8.8'}, {'REMOTE_ADDR': '0.0.0.0'},
                       {'REMOTE_ADDR': '224.0.0.1'}, {'QUERY_STRING': 'private=1'}):
            response = browser.request('/healthz', stream=UnreadBody(), overrides={**proxy, **change})
            self.assertEqual(response['status'], 403)

    def test_internal_health_is_available_after_global_admission_exhaustion(self):
        browser = Browser(hosted.create_app(ORIGIN, SECRET, trust_proxy=True))
        with patch.object(hosted, 'REQUESTS_PER_MINUTE', 0):
            self.assertEqual(browser.request('/healthz', overrides={'wsgi.url_scheme': 'http', 'REMOTE_ADDR': '10.0.0.4'})['status'], 200)
            self.assertEqual(browser.request('/api/session', overrides={'HTTP_X_FORWARDED_PROTO': 'https'})['status'], 429)
    def test_assets_health_and_session_have_security_headers(self):
        for path in ('/', '/app.js', '/style.css', '/healthz', '/api/session'):
            with self.subTest(path=path):
                response = self.browser.request(path)
                self.assertEqual(response['status'], 200)
                self.assert_security(response)
        session = response['value']
        self.assertEqual(session['mode'], 'HOSTED_TEMPORARY')
        self.assertTrue(session['consent_required'])
        self.assertFalse(session['hosting_consent'])
        cookie_response = Browser(self.app).request('/api/session')
        cookie = dict(cookie_response['headers'])['Set-Cookie']
        for attribute in ('Secure', 'HttpOnly', 'SameSite=Strict', 'Path=/'):
            self.assertIn(attribute, cookie)
        self.assertNotIn('Domain=', cookie)
        self.assertNotIn(cookie.split(';')[0].split('=', 1)[1], json.dumps(cookie_response['value']))

    def test_consent_is_required_before_scientific_body_read(self):
        self.browser.request('/api/session')
        with patch('controlomics.hosted.handle_action') as action:
            response = self.browser.request('/api/analyze', {}, stream=UnreadBody())
        self.assertEqual(response['status'], 428)
        self.assertEqual(response['value']['code'], 'HOSTING_CONSENT_REQUIRED')
        action.assert_not_called()
        self.assert_security(response)

    def test_shared_link_queries_only_serve_unchanged_public_assets(self):
        queries = ('fbclid=synthetic_click_id', 'utm_source=facebook&utm_medium=social',
                   'next=https%3A%2F%2Felsewhere.example&fbclid=synthetic_click_id',
                   'project=%3Cscript%3Esynthetic_marker%3C%2Fscript%3E&fbclid=a&fbclid=b')
        for path in hosted.ASSETS:
            original = self.browser.request(path)
            for method in ('GET', 'HEAD'):
                for query in queries:
                    with self.subTest(path=path, method=method, query=query):
                        response = self.browser.request(path, method=method, stream=UnreadBody(), overrides={
                            'QUERY_STRING': query, 'HTTP_SEC_FETCH_SITE': 'cross-site',
                            'HTTP_ORIGIN': 'https://www.facebook.com', 'HTTP_REFERER': 'https://www.facebook.com/'})
                        self.assertEqual(response['status'], 200)
                        self.assertEqual(response['body'], original['body'] if method == 'GET' else b'')
                        self.assertEqual(response['headers'], original['headers'])
                        self.assertNotIn(b'synthetic_click_id', response['body'])
                        self.assert_security(response)
        self.assertEqual(self.app._sessions, {})
        self.assertIsNone(self.browser.cookie)
        self.assertIsNone(self.browser.token)

    def test_shared_link_queries_do_not_authorize_session_or_action_routes(self):
        self.browser.consent()
        original_sessions = dict(self.app._sessions)
        routes = [('/api/session', 'GET'), ('/api/session', 'HEAD'), ('/healthz', 'GET'),
                  ('/healthz', 'HEAD'), ('/not-an-asset', 'GET'), ('/', 'POST'), ('/', 'OPTIONS'),
                  ('/app.js', 'POST'), ('/api/hosting-consent', 'POST')]
        routes.extend((path, 'POST') for path in hosted.ACTION_PATHS)
        with patch('controlomics.hosted.handle_action') as action:
            for path, method in routes:
                with self.subTest(path=path, method=method):
                    response = self.browser.request(path, method=method, stream=UnreadBody(), overrides={
                        'QUERY_STRING': 'fbclid=synthetic_click_id'})
                    self.assertEqual(response['status'], 403)
                    self.assertEqual(response['value']['code'], 'HOSTED_ORIGIN_REJECTED')
                    self.assert_security(response)
            action.assert_not_called()
        self.assertEqual(self.app._sessions, original_sessions)

    def test_shared_link_queries_keep_host_tls_and_proxy_checks(self):
        query = {'QUERY_STRING': 'fbclid=synthetic_click_id'}
        direct_failures = ({'HTTP_HOST': 'elsewhere.example'}, {'HTTP_HOST': 'controlomics.example,controlomics.example'},
                           {'wsgi.url_scheme': 'http', 'HTTP_X_FORWARDED_PROTO': 'https'},
                           {'HTTP_X_FORWARDED_PROTO': 'http'}, {'HTTP_X_FORWARDED_PROTO': 'https,http'})
        for change in direct_failures:
            with self.subTest(mode='direct', change=change):
                self.assertEqual(self.browser.request('/', overrides={**query, **change}, stream=UnreadBody())['status'], 403)
        proxy = {'wsgi.url_scheme': 'http', 'HTTP_X_FORWARDED_PROTO': 'https', 'REMOTE_ADDR': '10.1.2.3', **query}
        browser = Browser(hosted.create_app(ORIGIN, SECRET, trust_proxy=True))
        self.assertEqual(browser.request('/', overrides=proxy, stream=UnreadBody())['status'], 200)
        failures = ({'HTTP_HOST': 'elsewhere.example'}, {'HTTP_X_FORWARDED_PROTO': None},
                    {'HTTP_X_FORWARDED_PROTO': 'http'}, {'HTTP_X_FORWARDED_PROTO': 'https,http'},
                    {'wsgi.url_scheme': 'ftp'})
        failures += tuple({'REMOTE_ADDR': peer} for peer in ('8.8.8.8', '0.0.0.0', '224.0.0.1', 'bad', ''))
        for change in failures:
            with self.subTest(mode='proxy', change=change):
                self.assertEqual(browser.request('/', overrides={**proxy, **change}, stream=UnreadBody())['status'], 403)
        self.assertEqual(browser.app._sessions, {})

    def test_shared_link_queries_do_not_relax_cross_origin_posts(self):
        self.browser.consent()
        for origin in ('https://www.facebook.com', 'null', None):
            with self.subTest(origin=origin), patch('controlomics.hosted.handle_action') as action:
                response = self.browser.request('/api/interpret', {}, stream=UnreadBody(), overrides={
                    'HTTP_ORIGIN': origin})
                self.assertEqual(response['status'], 403)
                action.assert_not_called()

    def test_consent_has_exact_policy_boolean_and_small_metadata_only(self):
        self.browser.request('/api/session')
        original_token = self.browser.token
        for data in ({'allowed': False, 'policy_revision': hosted.POLICY_REVISION},
                     {'allowed': 1, 'policy_revision': hosted.POLICY_REVISION},
                     {'allowed': True, 'policy_revision': 'old'},
                     {'allowed': True, 'policy_revision': hosted.POLICY_REVISION, 'project': {}}):
            with self.subTest(data=data):
                self.assertEqual(self.browser.request('/api/hosting-consent', data)['status'], 400)
        response = self.browser.request('/api/hosting-consent', {'allowed': True, 'policy_revision': hosted.POLICY_REVISION})
        self.assertEqual(response['status'], 200)
        self.assertFalse(response['value']['consent_required'])
        self.assertTrue(response['value']['hosting_consent'])
        self.assertNotEqual(original_token, self.browser.token)
        response = self.browser.request('/api/hosting-consent', raw=b'x' * 513, stream=UnreadBody())
        self.assertEqual(response['status'], 400)

    def test_cookie_tampering_cross_browser_token_and_cross_origin_read_no_body(self):
        self.browser.consent()
        other = Browser(self.app)
        other.consent()
        for overrides in ({'HTTP_COOKIE': self.browser.cookie + 'x'},
                          {'HTTP_COOKIE': self.browser.cookie + '; ' + self.browser.cookie},
                          {'HTTP_COOKIE': None}, {'HTTP_X_CONTROLOMICS_TOKEN': other.token},
                          {'HTTP_X_CONTROLOMICS_TOKEN': '\xff'}, {'HTTP_ORIGIN': 'https://elsewhere.example'},
                          {'HTTP_ORIGIN': ORIGIN + ',' + ORIGIN}, {'HTTP_SEC_FETCH_SITE': 'cross-site'}):
            with self.subTest(overrides=overrides):
                response = self.browser.request('/api/interpret', {}, overrides=overrides, stream=UnreadBody())
                self.assertEqual(response['status'], 403)
                self.assertEqual(response['value']['code'], 'SESSION_RENEWAL_REQUIRED')

    def test_cold_start_and_expiry_require_renewal_without_request_replay(self):
        with patch('controlomics.hosted.time.time', return_value=1000):
            self.browser.consent()
        with patch('controlomics.hosted.time.time', return_value=4600), patch('controlomics.hosted.handle_action') as action:
            response = self.browser.request('/api/analyze', {}, stream=UnreadBody())
            self.assertEqual(response['status'], 403)
            renewed = self.browser.request('/api/session')
            self.assertTrue(renewed['value']['consent_required'])
            action.assert_not_called()
        self.browser.consent()
        self.browser.app = hosted.create_app(ORIGIN, SECRET)
        with patch('controlomics.hosted.handle_action') as action:
            self.assertEqual(self.browser.request('/api/analyze', {}, stream=UnreadBody())['status'], 403)
            self.assertTrue(self.browser.request('/api/session')['value']['consent_required'])
            action.assert_not_called()

    def test_valid_session_refresh_preserves_cookie_consent_and_token(self):
        self.browser.consent()
        old_cookie, old_token = self.browser.cookie, self.browser.token
        response = self.browser.request('/api/session')
        self.assertFalse(response['value']['consent_required'])
        self.assertEqual((self.browser.cookie, self.browser.token), (old_cookie, old_token))
        self.assertNotIn('Set-Cookie', dict(response['headers']))

    def test_ambiguous_framing_and_oversize_rejected_without_body_read(self):
        self.browser.consent()
        for overrides in ({'CONTENT_LENGTH': None}, {'CONTENT_LENGTH': '2,2'}, {'CONTENT_LENGTH': '-1'},
                          {'CONTENT_LENGTH': '0'}, {'CONTENT_LENGTH': str(hosted.MAX_BODY + 1)},
                          {'CONTENT_LENGTH': '9' * 100}, {'CONTENT_TYPE': 'application/json,application/json'},
                          {'HTTP_CONTENT_LENGTH': '2'}, {'HTTP_TRANSFER_ENCODING': 'chunked'},
                          {'HTTP_TRANSFER_ENCODING': ''}):
            with self.subTest(overrides=overrides):
                self.assertEqual(self.browser.request('/api/parse-json', {}, overrides=overrides, stream=UnreadBody())['status'], 400)

    def test_invalid_json_short_body_and_nonobjects_are_redacted(self):
        self.browser.consent()
        for raw, overrides in ((b'{"secret":1,"secret":2}', {}), (b'[]', {}), (b'{"private_sentinel":NaN}', {}),
                               (b'{}', {'CONTENT_LENGTH': '5'}), (b'\xff', {})):
            with self.subTest(raw=raw):
                response = self.browser.request('/api/parse-json', raw=raw, overrides=overrides)
                self.assertEqual(response['status'], 400)
                self.assertNotIn(b'private_sentinel', response['body'])
                self.assert_security(response)

    def test_origin_and_proxy_trust_do_not_use_forwarded_host_or_client_identity(self):
        for overrides in ({'HTTP_HOST': 'elsewhere.example', 'HTTP_X_FORWARDED_HOST': 'controlomics.example'},
                          {'HTTP_HOST': 'controlomics.example,controlomics.example'}, {'QUERY_STRING': 'private=1'},
                          {'wsgi.url_scheme': 'http', 'HTTP_X_FORWARDED_PROTO': 'https'},
                          {'HTTP_X_FORWARDED_PROTO': 'https,http'}):
            with self.subTest(overrides=overrides):
                self.assertEqual(self.browser.request('/api/session', overrides=overrides)['status'], 403)
        browser = Browser(hosted.create_app(ORIGIN, SECRET, trust_proxy=True))
        proxy = {'wsgi.url_scheme': 'http', 'HTTP_X_FORWARDED_PROTO': 'https', 'REMOTE_ADDR': '10.1.2.3'}
        self.assertEqual(browser.request('/api/session', overrides=proxy)['status'], 200)
        for peer in ('8.8.8.8', '0.0.0.0', '224.0.0.1', 'bad', ''):
            with self.subTest(peer=peer):
                self.assertEqual(browser.request('/api/session', overrides={**proxy, 'REMOTE_ADDR': peer})['status'], 403)
                self.assertEqual(browser.request('/api/session', overrides={**proxy, 'REMOTE_ADDR': peer, 'wsgi.url_scheme': 'https'})['status'], 403)

    def test_two_global_actions_have_no_queue_and_one_action_per_session(self):
        browsers = [Browser(self.app) for _ in range(3)]
        for browser in browsers:
            browser.consent()
        ready = [threading.Event(), threading.Event()]
        release = threading.Event()
        responses = []

        def action(path, data):
            ready[data['slot']].set()
            if not release.wait(3):
                raise AssertionError('Concurrent fixture was not released')
            return {'fixture': True}

        with patch('controlomics.hosted.handle_action', side_effect=action):
            threads = [threading.Thread(target=lambda i=i: responses.append(browsers[i].request('/api/interpret', {'slot': i}))) for i in range(2)]
            for thread in threads:
                thread.start()
            try:
                self.assertTrue(all(event.wait(2) for event in ready))
                response = browsers[2].request('/api/interpret', {}, stream=UnreadBody())
                self.assertEqual(response['status'], 503)
            finally:
                release.set()
                for thread in threads:
                    thread.join(timeout=3)
            self.assertTrue(all(not thread.is_alive() for thread in threads))
            self.assertEqual([response['status'] for response in responses], [200, 200])
        release.clear()
        ready[0].clear()
        with patch('controlomics.hosted.handle_action', side_effect=action):
            thread = threading.Thread(target=lambda: responses.append(browsers[0].request('/api/interpret', {'slot': 0})))
            thread.start()
            try:
                self.assertTrue(ready[0].wait(2))
                response = browsers[0].request('/api/interpret', {}, stream=UnreadBody())
                self.assertEqual(response['status'], 429)
                self.assertEqual(response['value']['code'], 'SESSION_BUSY')
            finally:
                release.set()
                thread.join(timeout=3)

    def test_action_execution_and_global_get_limits_are_bounded(self):
        self.browser.consent()
        with patch('controlomics.hosted.handle_action', return_value={}), patch('controlomics.hosted.SESSION_REQUESTS_PER_MINUTE', 2):
            self.assertEqual(self.browser.request('/api/interpret', {})['status'], 200)
            self.assertEqual(self.browser.request('/api/interpret', {}, stream=UnreadBody())['status'], 429)
        with patch('controlomics.hosted.handle_action', return_value={}):
            for _ in range(2):
                self.assertEqual(self.browser.request('/api/execute', {})['status'], 200)
            self.assertEqual(self.browser.request('/api/execute', {}, stream=UnreadBody())['status'], 429)
        app = hosted.create_app(ORIGIN, SECRET)
        with patch('controlomics.hosted.REQUESTS_PER_MINUTE', 2):
            for path in ('/healthz', '/api/session'):
                self.assertEqual(Browser(app).request(path)['status'], 200)
            self.assertEqual(Browser(app).request('/healthz')['status'], 429)

    def test_session_capacity_is_bounded_and_expired_metadata_is_removed(self):
        with patch('controlomics.hosted.MAX_SESSIONS', 2), patch('controlomics.hosted.time.time', return_value=1000):
            self.assertEqual(Browser(self.app).request('/api/session')['status'], 200)
            self.assertEqual(Browser(self.app).request('/api/session')['status'], 200)
            self.assertEqual(Browser(self.app).request('/api/session')['status'], 503)
            self.assertEqual(len(self.app._sessions), 2)
        with patch('controlomics.hosted.time.time', return_value=4600):
            self.assertEqual(Browser(self.app).request('/api/session')['status'], 200)
            self.assertEqual(len(self.app._sessions), 1)

    def test_imported_hosting_receipt_cannot_grant_active_consent(self):
        project = record_hosted_processing(parse_project_json(json.dumps(payload())), processor_origin=ORIGIN,
                                          session_binding_sha256='0' * 64, granted_at=datetime.now(timezone.utc))
        self.browser.request('/api/session')
        response = self.browser.request('/api/analyze', {'project': project.model_dump(mode='json')}, stream=UnreadBody())
        self.assertEqual(response['status'], 428)

    def test_project_receipt_is_recorded_without_shared_project_storage(self):
        self.browser.consent()
        value = payload()
        with patch('controlomics.hosted.handle_action', side_effect=lambda path, data: {'project': data['project']}) as action:
            response = self.browser.request('/api/analyze', {'project': value, 'private_sentinel': 'synthetic_private_field'})
        self.assertEqual(response['status'], 200)
        project = response['value']['project']
        receipt = project['privacy']['hosted_processing_receipts'][0]
        self.assertEqual(receipt['processor_origin'], ORIGIN)
        self.assertEqual(receipt['policy_revision'], hosted.POLICY_REVISION)
        self.assertEqual(project['candidates'], value['candidates'])
        self.assertIn('hosting_processing', response['value'])
        self.assertNotIn('private_sentinel', repr(vars(self.app)))
        self.assertNotIn('synthetic_private_field', repr(self.app._sessions))
        action.assert_called_once()

    def test_actual_new_project_report_archive_and_input_summary_disclose_hosting(self):
        self.browser.consent()
        value = payload()
        value['candidates'] = []
        response = self.browser.request('/api/analyze', {'project': value})
        self.assertEqual(response['status'], 200)
        project = response['value']['project']
        self.assertEqual(len(project['privacy']['hosted_processing_receipts']), 1)
        report = self.browser.request('/api/report', {'project': project})
        self.assertEqual(report['status'], 200)
        self.assertIn(ORIGIN.encode(), report['body'])
        archive = self.browser.request('/api/review-bundle', {'project': project})
        self.assertEqual(archive['status'], 200)
        with zipfile.ZipFile(io.BytesIO(archive['body'])) as bundle:
            saved = json.loads(bundle.read('project.json'))
            self.assertEqual(saved['privacy']['hosted_processing_receipts'], project['privacy']['hosted_processing_receipts'])
        inspected = self.browser.request('/api/inspect-input', {'adapter': 'INDEPENDENT_REFERENCE', 'csv': 'unit,label,value\na,0,1\nb,0,2\nc,1,3\nd,1,4\n'})
        self.assertEqual(inspected['status'], 200)
        summary = NumericInputSummary.model_validate_json(json.dumps(inspected['value']['input_summary']))
        self.assertTrue(any('temporary first-party' in item for item in summary.limitations))

    def test_existing_compute_budget_rejects_before_staging_or_subprocess(self):
        self.browser.consent()
        value = payload()
        value['candidates'] = []
        project = propose_and_review_new(parse_project_json(json.dumps(value)))
        csv = 'unit,label,value\n' + ''.join(f'unit.{i},{i % 2},{i % 7}\n' for i in range(2000))
        with patch.object(execution, 'TemporaryDirectory', side_effect=AssertionError('Unexpected staging')), \
                patch.object(execution.subprocess, 'run', side_effect=AssertionError('Unexpected process')):
            response = self.browser.request('/api/execute', {'project': project.model_dump(mode='json'),
                'control_id': project.controls[0].control_id, 'config': {'kind': 'PERMUTATION', 'draws': 10000, 'assumptions': ['Synthetic independent units.']}, 'csv': csv})
        self.assertEqual(response['status'], 400)
        self.assertEqual(response['value']['code'], 'LOCAL_RESAMPLING_BUDGET')

    def test_actual_numeric_execution_cleans_owned_temporary_input(self):
        self.browser.consent()
        value = payload()
        value['candidates'] = []
        project = propose_and_review_new(parse_project_json(json.dumps(value)))
        directories = []
        original = TemporaryDirectory

        def owned(*args, **kwargs):
            directory = original(*args, **kwargs)
            directories.append(Path(directory.name))
            return directory

        with patch.object(execution, 'TemporaryDirectory', side_effect=owned):
            response = self.browser.request('/api/execute', {'project': project.model_dump(mode='json'),
                'control_id': project.controls[0].control_id,
                'config': {'kind': 'REFERENCE', 'expected_difference': 2.0, 'assumptions': ['Synthetic independent units.']},
                'csv': (ROOT / 'examples/positive_reference.csv').read_text()})
        self.assertEqual(response['status'], 200, response['value'])
        self.assertEqual(response['value']['project']['results'][0]['outcome'], 'PASS')
        self.assertTrue(directories)
        self.assertTrue(all(not directory.exists() for directory in directories))
        self.assertEqual(len(response['value']['project']['privacy']['hosted_processing_receipts']), 1)

    def test_dispatched_package_preserves_receipt_and_omits_raw_inputs(self):
        self.browser.consent()
        value = payload()
        value['candidates'] = []
        project = propose_and_review_new(parse_project_json(json.dumps(value)))
        response = self.browser.request('/api/package', {'project': project.model_dump(mode='json'),
            'control_id': project.controls[0].control_id,
            'config': {'kind': 'REFERENCE', 'expected_difference': 2.0, 'assumptions': ['Synthetic independent units.']}})
        self.assertEqual(response['status'], 200, response['value'])
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(response['value']['package_base64']))) as package:
            saved = json.loads(package.read('project.json'))
            self.assertEqual(len(saved['privacy']['hosted_processing_receipts']), 1)
            self.assertIn('hosting_processing.json', package.namelist())
            self.assertNotIn('input.csv', package.namelist())

    def test_errors_release_slots_and_do_not_echo_or_log_private_content(self):
        self.browser.consent()
        with patch('controlomics.hosted.handle_action', side_effect=RuntimeError('private_sentinel token=synthetic')):
            response = self.browser.request('/api/interpret', {'question': 'private_sentinel'})
        self.assertEqual(response['status'], 500)
        self.assertNotIn(b'private_sentinel', response['body'])
        self.assert_security(response)
        with patch('controlomics.hosted.handle_action', return_value={}):
            self.assertEqual(self.browser.request('/api/interpret', {})['status'], 200)

    def test_provider_requests_still_require_exact_request_approval(self):
        self.browser.consent()
        value = payload()
        with patch('controlomics.privacy.http.client.HTTPSConnection', side_effect=AssertionError('Unexpected provider request')) as connection:
            response = self.browser.request('/api/literature/retrieve', {'project': value, 'provider': 'europepmc',
                'query': 'public permutation method', 'public_confirmed': True, 'approve_hash': 'not-the-preview-hash'})
        self.assertEqual(response['status'], 200)
        self.assertIn('error', response['value'])
        connection.assert_not_called()

    def test_model_preview_never_echoes_or_retains_supplied_credentials(self):
        self.browser.consent()
        marker = 'synthetic_private_key_for_check'
        with patch('controlomics.privacy.http.client.HTTPSConnection', side_effect=AssertionError('Unexpected provider request')) as connection:
            response = self.browser.request('/api/model/preview', {'endpoint': 'https://api.example/v1/chat/completions',
                'model': 'synthetic_fixture', 'api_key': marker, 'fields': {'question': 'Public synthetic scientific question.'},
                'public_confirmed': True})
        self.assertEqual(response['status'], 200, response['value'])
        self.assertNotIn(marker.encode(), response['body'])
        self.assertNotIn(marker, repr(vars(self.app)))
        self.assert_security(response)
        connection.assert_not_called()

    def test_evaluation_hashes_and_metrics_are_unchanged_by_outer_receipt(self):
        from controlomics.evaluation import EvaluationBundle, bundle_hash, evaluate
        from tests.scientific.test_evaluation import bundle_payload

        self.browser.consent()
        value = bundle_payload()
        before = json.dumps(value, sort_keys=True)
        bundle = EvaluationBundle.model_validate_json(json.dumps(value))
        response = self.browser.request('/api/evaluate', {'bundle': value})
        self.assertEqual(response['status'], 200, response['value'])
        self.assertEqual(response['value']['evaluation']['bundle_sha256'], bundle_hash(bundle))
        self.assertEqual(response['value']['evaluation']['metrics'], evaluate(bundle)['metrics'])
        self.assertEqual(json.dumps(value, sort_keys=True), before)
        self.assertEqual(response['value']['hosting_processing']['processor_origin'], ORIGIN)
