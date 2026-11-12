"""Browser runtime tests under CPython. Pyodide-specific loading is checked separately."""

import base64
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

from controlomics import browser, execution
from controlomics.execution import ExecutionConfig, execute_local
from controlomics.project import parse_project_json
from controlomics.workflow import propose, review_methods
from tests.fixtures import payload

INDEPENDENT = b'unit,label,value\na,0,0\nb,0,1\nc,1,2\nd,1,3\n'


def reviewed():
    data = payload()
    data['candidates'] = []
    return review_methods(propose(parse_project_json(json.dumps(data))))


def call(path, body):
    return json.loads(browser.dispatch(path, json.dumps(body)))


class BrowserDispatchTests(unittest.TestCase):
    def test_session_declares_browser_mode_with_a_valid_token(self):
        data = json.loads(browser.session())
        self.assertEqual(data['deployment'], {'mode': 'BROWSER'})
        self.assertRegex(data['token'], r'^[A-Za-z0-9_-]{32,128}$')

    def test_invalid_bodies_and_unknown_actions_use_the_fixed_redacted_reply(self):
        for raw in ('', 'not json', '[1]', '{"a": 1, "a": 2}', 'x' * (2 * 1024 * 1024 + 1)):
            reply = json.loads(browser.dispatch('/api/parse-json', raw))
            self.assertEqual(reply, {'status': 400, 'json': {'error': browser.REDACTED_FAILURE}})
        self.assertEqual(call('/api/unknown', {'project': payload()})['status'], 400)

    def test_actions_return_the_same_records_as_the_local_dispatch(self):
        from controlomics.server import handle_action
        body = {'content': json.dumps(payload())}
        reply = call('/api/parse-json', body)
        self.assertEqual(reply, {'status': 200, 'json': json.loads(json.dumps(handle_action('/api/parse-json', body)))})
        analysis = call('/api/analyze', {'project': payload()})
        self.assertEqual(analysis['status'], 200)
        self.assertEqual(set(analysis['json']), {'project', 'design_profiles'})

    def test_downloads_are_returned_as_base64_with_type_and_filename(self):
        reply = call('/api/report', {'project': payload()})
        self.assertEqual((reply['status'], reply['content_type'], reply['filename']), (200, 'text/html', 'controlomics.report.html'))
        self.assertIn(b'<html', base64.b64decode(reply['body_base64']).lower())

    def test_unapproved_literature_requests_record_nothing_and_send_nothing(self):
        reply = call('/api/literature/retrieve', {'project': payload(), 'provider': 'crossref', 'query': 'yeast',
                                                  'public_confirmed': True, 'approve_hash': '0' * 64})
        self.assertNotIn('fetch', reply)
        self.assertEqual(reply['json']['network_audit'], [])


class BrowserTransmissionTests(unittest.TestCase):
    """The page transmits approved requests; Python checks first and records the outcome."""

    def setUp(self):
        self.project = payload()
        preview = call('/api/literature/preview', {'provider': 'europepmc', 'query': 'yeast heat shock', 'public_confirmed': True})
        self.approval = preview['json']['approve_hash']
        self.body = {'project': self.project, 'provider': 'europepmc', 'query': 'yeast heat shock',
                     'public_confirmed': True, 'approve_hash': self.approval}

    def finish(self, outcome, body=None, path='/api/literature/retrieve'):
        body = body or self.body
        first = json.loads(browser.dispatch(path, json.dumps(body)))
        return first, json.loads(browser.dispatch(path, json.dumps(body), json.dumps({first['fetch']['request_sha256']: outcome})))

    def test_first_pass_returns_the_exact_approved_request_and_records_nothing(self):
        with patch('socket.getaddrinfo', side_effect=AssertionError('the page transmits, not Python')), \
             patch('socket.create_connection', side_effect=AssertionError('the page transmits, not Python')):
            first = call('/api/literature/retrieve', self.body)
        request = first['fetch']
        self.assertEqual(first['status'], 0)
        self.assertEqual((request['method'], request['purpose'], request['request_sha256'], request['credential']), ('GET', 'LITERATURE', self.approval, False))
        self.assertTrue(request['url'].startswith('https://www.ebi.ac.uk/europepmc/webservices/rest/search?'))
        self.assertIsNone(request['body'])

    def test_completed_outcome_is_parsed_and_recorded_with_its_hash(self):
        raw = json.dumps({'resultList': {'result': []}}).encode()
        _, reply = self.finish({'phase': 'COMPLETED', 'ok': True, 'body_base64': base64.b64encode(raw).decode()})
        self.assertEqual(reply['status'], 200)
        [event] = reply['json']['network_audit']
        self.assertEqual((event['status'], event['payload_transmission'], event['response_bytes']), ('COMPLETED', 'COMPLETED', len(raw)))
        self.assertEqual(event['response_sha256'], __import__('hashlib').sha256(raw).hexdigest())

    def test_failed_outcomes_keep_the_phase_the_page_reached(self):
        cases = (({'phase': 'ATTEMPTED', 'ok': False}, 'ATTEMPTED'),
                 ({'phase': 'COMPLETED', 'ok': False}, 'COMPLETED'),
                 ({'phase': 'COMPLETED', 'ok': True, 'body_base64': base64.b64encode(b'x' * (2 * 1024 * 1024 + 1)).decode()}, 'COMPLETED'),
                 ({'phase': 'COMPLETED', 'ok': True, 'body_base64': base64.b64encode(b'not json').decode()}, 'COMPLETED'),
                 ({'phase': 'SENT', 'ok': True}, 'ATTEMPTED'),
                 ({'phase': 'ATTEMPTED', 'ok': True, 'body_base64': ''}, 'ATTEMPTED'))
        for outcome, phase in cases:
            _, reply = self.finish(outcome)
            self.assertIn('error', reply['json'], outcome)
            [event] = reply['json']['network_audit']
            self.assertEqual((event['status'], event['payload_transmission']), ('FAILED', phase), outcome)

    def test_outcomes_must_be_an_object(self):
        reply = json.loads(browser.dispatch('/api/literature/retrieve', json.dumps(self.body), '[]'))
        self.assertEqual(reply, {'status': 400, 'json': {'error': browser.REDACTED_FAILURE}})

    def test_model_requests_name_a_credential_without_returning_it(self):
        body = {'project': self.project, 'endpoint': 'https://models.example.org/v1/chat/completions', 'model': 'synthetic-model',
                'fields': {'question': 'Does the synthetic fixture parse?'}, 'public_confirmed': True, 'api_key': 'synthetic-key-value'}
        preview = call('/api/model/preview', body)
        body['approve_hash'] = preview['json']['approve_hash']
        first, reply = self.finish({'phase': 'COMPLETED', 'ok': True, 'body_base64': base64.b64encode(b'{"choices": []}').decode()},
                                   body, '/api/model/run')
        self.assertTrue(first['fetch']['credential'])
        self.assertNotIn('synthetic-key-value', json.dumps(first) + json.dumps(reply))
        [event] = reply['json']['network_audit']
        self.assertEqual((event['status'], event['credential_supplied']), ('COMPLETED', True))
        self.assertIn('error', reply['json'])

    def test_malformed_credentials_fail_before_any_transmission(self):
        body = {'project': self.project, 'endpoint': 'https://models.example.org/v1/chat/completions', 'model': 'synthetic-model',
                'fields': {'question': 'Does the synthetic fixture parse?'}, 'public_confirmed': True, 'api_key': 'bad\nkey'}
        body['approve_hash'] = call('/api/model/preview', body)['json']['approve_hash']
        reply = call('/api/model/run', body)
        self.assertNotIn('fetch', reply)
        [event] = reply['json']['network_audit']
        self.assertEqual((event['status'], event['payload_transmission']), ('FAILED', 'NOT_STARTED'))


class InProcessRunnerTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, execution, 'subprocess', subprocess)

    def test_in_process_execution_matches_the_separate_process_result(self):
        project = reviewed()
        control = project.controls[0].control_id
        config = ExecutionConfig(kind='PERMUTATION', assumptions=('Synthetic software fixture only.',))
        separate = execute_local(project, control, config, INDEPENDENT).results[0]
        browser.install()
        modules = set(sys.modules)
        inside = execute_local(project, control, config, INDEPENDENT).results[0]
        self.assertIsNotNone(separate.p_value)
        varying = {'result_id', 'started_at', 'completed_at', 'execution_id'}
        expected = {key: value for key, value in separate.model_dump().items() if key not in varying}
        self.assertEqual({key: value for key, value in inside.model_dump().items() if key not in varying}, expected)
        self.assertNotIn('stats', set(sys.modules) - modules)
        self.assertNotIn('export_storage', set(sys.modules) - modules)

    def test_only_the_fixed_runner_can_be_started(self):
        for args in ([sys.executable, '-c', 'print(1)'], ['/bin/sh', 'run_control.py'], [sys.executable]):
            with self.assertRaises(ValueError):
                browser.InProcessRunner.run(args, capture_output=True, text=True, timeout=1)

    def test_runner_failure_becomes_a_nonzero_exit_without_raising(self):
        result = browser.InProcessRunner.run([sys.executable, 'missing/run_control.py'], capture_output=True, text=True, timeout=1)
        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
