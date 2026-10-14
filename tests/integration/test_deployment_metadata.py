import logging
import os
import unittest
from unittest.mock import patch

from controlomics.hosted import create_app
from tests.integration.test_hosted import Browser, ORIGIN, SECRET


class DeploymentMetadataTests(unittest.TestCase):
    def test_public_revision_and_current_access_logger_state_are_reported(self):
        revision = 'a' * 40
        with patch.dict(os.environ, {'RENDER_GIT_COMMIT': revision}):
            browser = Browser(create_app(ORIGIN, SECRET))
        logger = logging.getLogger('gunicorn.access')
        with patch.object(logger, 'disabled', False):
            response = browser.request('/', overrides={'HTTP_X_CONTROLOMICS_REVISION': 'b' * 40})
            headers = dict(response['headers'])
            self.assertEqual(headers['X-Controlomics-Revision'], revision)
            self.assertEqual(headers['X-Controlomics-Access-Log'], 'unverified')
        with patch.object(logger, 'disabled', True):
            headers = dict(browser.request('/healthz')['headers'])
            self.assertEqual(headers['X-Controlomics-Revision'], revision)
            self.assertEqual(headers['X-Controlomics-Access-Log'], 'disabled')
        self.assertNotIn('Set-Cookie', headers)
        self.assertEqual(browser.app._sessions, {})

    def test_missing_or_noncanonical_revision_never_enters_response_headers(self):
        values = ('', 'a' * 39, 'a' * 41, 'A' * 40, 'g' * 40,
                  'a' * 40 + '\r\nX-Injected: value', '/'.join(('', 'home', 'synthetic', 'private')),
                  'synthetic@example.org', 'Bearer synthetic_value_only')
        for value in values:
            with self.subTest(value=value), patch.dict(os.environ, {'RENDER_GIT_COMMIT': value}):
                browser = Browser(create_app(ORIGIN, SECRET))
                response = browser.request('/')
                headers = dict(response['headers'])
                self.assertEqual(response['status'], 200)
                self.assertNotIn('X-Controlomics-Revision', headers)
                self.assertNotIn('X-Controlomics-Access-Log', headers)
                self.assertNotIn('X-Injected', headers)
                self.assertIsNone(browser.cookie)

    def test_public_metadata_does_not_authorize_private_actions(self):
        with patch.dict(os.environ, {'RENDER_GIT_COMMIT': 'a' * 40}):
            browser = Browser(create_app(ORIGIN, SECRET))
        response = browser.request('/api/interpret', {}, overrides={'HTTP_X_CONTROLOMICS_REVISION': 'a' * 40})
        self.assertEqual(response['status'], 403)
        self.assertEqual(response['value']['code'], 'SESSION_RENEWAL_REQUIRED')
        self.assertEqual(browser.app._sessions, {})
