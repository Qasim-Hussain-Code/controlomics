import io
import unittest
from unittest.mock import patch

from controlomics.hosted import create_app
from tests.integration.test_hosted import Browser, ORIGIN, SECRET, UnreadBody


class WSGIErrorStreamTests(unittest.TestCase):
    def test_diagnostic_writes_are_redacted_through_real_wsgi_entry(self):
        app = create_app(ORIGIN, SECRET)
        original = app._handle

        def write_diagnostics(environ, start_response):
            stream = environ['wsgi.errors']
            stream.write('synthetic_private_write')
            stream.writelines(['synthetic_private_line_one', '', 'synthetic_private_line_two'])
            stream.flush()
            return original(environ, start_response)

        with patch.object(app, '_handle', side_effect=write_diagnostics):
            response = Browser(app).request('/')
        self.assertEqual(response['status'], 200)
        self.assertEqual(response['errors'], 'Hosted request diagnostic. Private details omitted.\n' * 3)
        self.assertNotIn('synthetic_private', str(response))
        self.assertEqual(app._sessions, {})

    def test_stream_wrapper_does_not_mutate_caller_environment_or_read_input(self):
        app = create_app(ORIGIN, SECRET)
        source = io.StringIO()
        environ = {'REQUEST_METHOD': 'GET', 'PATH_INFO': '/', 'QUERY_STRING': '',
                   'HTTP_HOST': 'controlomics.example', 'wsgi.url_scheme': 'https',
                   'wsgi.input': UnreadBody(), 'wsgi.errors': source}
        response = {}
        body = b''.join(app(environ, lambda status, headers: response.update(status=status, headers=headers)))
        self.assertTrue(response['status'].startswith('200 '))
        self.assertTrue(body)
        self.assertIs(environ['wsgi.errors'], source)
        self.assertFalse(source.closed)
        self.assertEqual(source.getvalue(), '')
