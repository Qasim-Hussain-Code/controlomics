import io
import logging
import runpy
import unittest
from types import SimpleNamespace

from tests.fixtures import ROOT


class HostedLoggingTests(unittest.TestCase):
    def setUp(self):
        self.config = runpy.run_path(str(ROOT / 'gunicorn.conf.py'))
        self.output = io.StringIO()
        self.handler = logging.StreamHandler(self.output)
        self.loggers = [logging.getLogger(name) for name in
                        ('controlomics.test.error', 'controlomics.test.access', 'gunicorn.http.wsgi')]
        for logger in self.loggers:
            original = (logger.handlers[:], logger.filters[:], logger.level, logger.disabled, logger.propagate)
            self.addCleanup(self.restore_logger, logger, original)
            logger.handlers = [self.handler]
            logger.filters = []
            logger.setLevel(logging.DEBUG)
            logger.disabled = False
            logger.propagate = False
        self.values = {'accesslog': '-'}
        self.server = SimpleNamespace(
            cfg=SimpleNamespace(set=self.values.__setitem__),
            log=SimpleNamespace(error_log=self.loggers[0], access_log=self.loggers[1]))

    @staticmethod
    def restore_logger(logger, original):
        handlers, filters, level, disabled, propagate = original
        logger.handlers, logger.filters, logger.disabled, logger.propagate = handlers, filters, disabled, propagate
        logger.setLevel(level)

    def test_startup_disables_already_configured_access_output(self):
        self.loggers[1].info('GET /?synthetic_marker=before HTTP/1.1')
        self.assertIn('synthetic_marker=before', self.output.getvalue())
        self.output.seek(0)
        self.output.truncate()
        self.config['on_starting'](self.server)
        self.loggers[1].info('GET /?synthetic_marker=after HTTP/1.1')
        self.assertIsNone(self.values['accesslog'])
        self.assertTrue(self.loggers[1].disabled)
        self.assertEqual(self.output.getvalue(), '')

    def test_error_and_wsgi_logs_redact_arguments_and_traceback(self):
        self.config['on_starting'](self.server)
        for logger in (self.loggers[0], self.loggers[2]):
            with self.subTest(logger=logger.name):
                self.output.seek(0)
                self.output.truncate()
                try:
                    raise ValueError('synthetic_traceback_marker')
                except ValueError:
                    logger.warning('synthetic_message %s', 'synthetic_argument_marker', exc_info=True, stack_info=True)
                self.assertEqual(self.output.getvalue(),
                                 'Hosted server diagnostic. Request and internal details omitted.\n')
