import contextlib
import io
import json
import socket
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from controlomics.artifacts import open_review_bundle, validated_ledger
from controlomics.cli import main
from controlomics.evidence import EuropePMC
from controlomics.privacy import SafeTransport
from tests.fixtures import ROOT


class InterruptedTransportTests(unittest.TestCase):
    def network(self, phase, exception):
        stack = contextlib.ExitStack()
        connection = MagicMock()
        connection.getresponse.return_value.status = 200
        connection.getresponse.return_value.read.return_value = b'{}'
        addresses = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443))]
        resolve = stack.enter_context(patch('socket.getaddrinfo', return_value=addresses))
        stack.enter_context(patch('socket.create_connection'))
        stack.enter_context(patch('ssl.create_default_context'))
        stack.enter_context(patch('http.client.HTTPSConnection', return_value=connection))
        target = {'dns': resolve, 'request': connection.request,
                  'response': connection.getresponse, 'read': connection.getresponse.return_value.read,
                  'close': connection.close}[phase]
        target.side_effect = exception
        return stack, connection

    def test_interrupts_preserve_phase_and_propagate_without_private_details(self):
        for phase, expected in [('dns', 'NOT_STARTED'), ('request', 'ATTEMPTED'),
                                ('response', 'COMPLETED'), ('read', 'COMPLETED'), ('close', 'COMPLETED')]:
            for exception in (KeyboardInterrupt('private_sentinel'), SystemExit('private_sentinel')):
                with self.subTest(phase=phase, kind=type(exception).__name__):
                    transport = SafeTransport(frozenset({EuropePMC.host}))
                    request = EuropePMC(transport).prepare_search('public method')
                    network, connection = self.network(phase, exception)
                    with network, self.assertRaises(type(exception)) as caught:
                        transport.send(request, request.approval_hash)
                    self.assertIs(caught.exception, exception)
                    event = validated_ledger(transport.audit)[0]
                    self.assertEqual(event['payload_transmission'], expected)
                    self.assertEqual(event['status'], 'BLOCKED' if phase == 'dns' else 'FAILED')
                    self.assertIsNone(event['response_sha256'])
                    self.assertIsNone(event['response_bytes'])
                    self.assertNotIn('private_sentinel', json.dumps(event))
                    if phase != 'dns':
                        connection.close.assert_called_once()

    def test_interrupted_cli_ledgers_remain_usable_in_reports_and_bundles(self):
        project = ROOT / 'examples/transcriptomics.project.json'
        original = project.read_bytes()
        for command in ('retrieve', 'model-propose'):
            for phase in ('dns', 'request', 'response', 'read'):
                with self.subTest(command=command, phase=phase), TemporaryDirectory() as temporary:
                    folder = Path(temporary)
                    target, audit = folder / 'output.json', folder / 'network.json'
                    target.write_bytes(b'previous export')
                    args = [command, str(project), '--output', str(target), '--audit-output', str(audit)]
                    if command == 'retrieve':
                        args += ['--query', 'public method']
                    else:
                        context = folder / 'context.json'
                        context.write_text('{"question":"Synthetic public question"}', encoding='utf-8')
                        args += ['--context', str(context), '--endpoint', 'https://model.example/v1/chat/completions', '--model', 'fixture']
                    preview = io.StringIO()
                    with contextlib.redirect_stdout(preview), patch('socket.getaddrinfo') as resolve:
                        self.assertEqual(main(args), 2)
                        resolve.assert_not_called()
                    approval = json.loads(preview.getvalue().split('\nNo request sent')[0])['approve_hash']
                    output = io.StringIO()
                    network, _ = self.network(phase, KeyboardInterrupt('private_sentinel'))
                    with network, contextlib.redirect_stdout(output):
                        self.assertEqual(main(args + ['--approve-hash', approval]), 130)
                    ledger = validated_ledger(json.loads(audit.read_bytes()))
                    self.assertEqual(len(ledger), 1)
                    self.assertEqual(target.read_bytes(), b'previous export')
                    self.assertNotIn('private_sentinel', output.getvalue())
                    report, bundle = folder / 'report.html', folder / 'review.zip'
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(main(['report', str(project), '--network-audit', str(audit), '--output', str(report)]), 0)
                        self.assertEqual(main(['bundle-export', str(project), '--network-audit', str(audit), '--output', str(bundle)]), 0)
                    self.assertTrue(report.is_file())
                    self.assertEqual(open_review_bundle(bundle.read_bytes())[1], ledger)
        self.assertEqual(project.read_bytes(), original)
