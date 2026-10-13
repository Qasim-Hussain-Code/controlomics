import socket
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from controlomics import hosted_worker


class HostedTransportTests(unittest.TestCase):
    def test_read_deadline_survives_blocking_mode_and_caps_each_read(self):
        native = Mock()
        native.gettimeout.return_value = None
        native.recv.return_value = b'a'
        bound = hosted_worker.BoundedSocket(native)
        with patch('controlomics.hosted_worker.time.monotonic', side_effect=(10, 15, 39.5, 40)):
            bound.begin_request()
            bound.setblocking(True)
            self.assertEqual(bound.recv(1), b'a')
            self.assertEqual(bound.recv(1), b'a')
            with self.assertRaises(TimeoutError):
                bound.recv(1)
        self.assertEqual([call.args[0] for call in native.settimeout.call_args_list], [10, None, 0.5, None])
        self.assertEqual(native.recv.call_count, 2)
        native.setblocking.assert_called_once_with(True)

    def test_tighter_native_timeout_nonblocking_and_restore_on_error(self):
        native = Mock()
        native.gettimeout.return_value = 0.25
        native.recv.side_effect = socket.timeout('Synthetic inactivity')
        bound = hosted_worker.BoundedSocket(native)
        bound.begin_request()
        with self.assertRaises(socket.timeout):
            bound.recv(1)
        self.assertEqual([call.args[0] for call in native.settimeout.call_args_list], [0.25, 0.25])
        native.reset_mock()
        native.gettimeout.return_value = 0
        native.recv.side_effect = BlockingIOError
        with self.assertRaises(BlockingIOError):
            bound.recv(1)
        native.settimeout.assert_not_called()

    def test_new_request_resets_read_deadline_and_recv_into_is_bounded(self):
        native = Mock()
        native.gettimeout.return_value = None
        native.recv_into.return_value = 1
        bound = hosted_worker.BoundedSocket(native)
        with patch('controlomics.hosted_worker.time.monotonic', side_effect=(10, 50, 51)):
            bound.begin_request()
            bound.begin_request()
            self.assertEqual(bound.recv_into(bytearray(1)), 1)
        self.assertEqual(native.settimeout.call_args_list[0].args[0], 10)

    def test_write_deadline_is_separate_from_expired_read_deadline(self):
        native = Mock()
        native.gettimeout.return_value = None
        bound = hosted_worker.BoundedSocket(native)
        with patch('controlomics.hosted_worker.time.monotonic', side_effect=(10, 100)):
            bound.begin_request()
            with self.assertRaises(TimeoutError):
                bound.recv(1)
            bound.sendall(b'Synthetic completed response')
        native.sendall.assert_called_once()
        self.assertEqual([call.args[0] for call in native.settimeout.call_args_list], [10, None])

    def test_socket_identity_and_selector_methods_are_preserved(self):
        native = Mock()
        bound = hosted_worker.BoundedSocket(native)
        self.assertEqual(bound.fileno(), native.fileno.return_value)
        self.assertEqual(bound.getsockname(), native.getsockname.return_value)
        bound.shutdown(socket.SHUT_WR)
        bound.close()
        native.shutdown.assert_called_once_with(socket.SHUT_WR)
        native.close.assert_called_once()
        with self.assertRaises(RuntimeError):
            bound.makefile('rb')

    def test_worker_fails_closed_for_unqualified_configuration(self):
        for configuration in (SimpleNamespace(is_ssl=True, http_protocols=['h1'], http2_cleartext='off'),
                              SimpleNamespace(is_ssl=False, http_protocols=['h2', 'h1'], http2_cleartext='off'),
                              SimpleNamespace(is_ssl=False, http_protocols=['h1'], http2_cleartext='upgrade')):
            with self.subTest(configuration=configuration), self.assertRaisesRegex(RuntimeError, 'proxy-terminated HTTPS'):
                hosted_worker.HostedThreadWorker.check_config(configuration, Mock())
