"""Small read-deadline extension for the pinned HTTP/1 Gunicorn thread worker."""

from __future__ import annotations

import time
from http import HTTPStatus

from controlomics.server import SECURITY_HEADERS

try:
    import gunicorn
    from gunicorn.http import errors as _errors
    from gunicorn.workers.gthread import ThreadWorker as _ThreadWorker
except ImportError:
    gunicorn, _errors, _ThreadWorker = None, None, object

READ_INACTIVITY_SECONDS = 10.0
READ_DEADLINE_SECONDS = 30.0
WRITE_TIMEOUT_SECONDS = 10.0
CONFIGURATION_ERROR = "Hosted worker requires pinned Gunicorn 26.2.0 and proxy-terminated HTTPS with internal HTTP/1 only."


class BoundedSocket:
    """Preserve selector semantics while bounding the worker's blocking I/O."""

    def __init__(self, sock):
        self._socket = sock
        self._deadline = None

    def __getattr__(self, name):
        return getattr(self._socket, name)

    def begin_request(self):
        self._deadline = time.monotonic() + READ_DEADLINE_SECONDS

    def _read(self, operation, *args):
        prior = self._socket.gettimeout()
        if prior == 0:
            return operation(*args)
        if self._deadline is None:
            raise RuntimeError("Hosted transport read was not initialized.")
        remaining = self._deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Hosted request read deadline exceeded.")
        interval = min(READ_INACTIVITY_SECONDS, remaining)
        if prior is not None:
            interval = min(interval, prior)
        self._socket.settimeout(interval)
        try:
            return operation(*args)
        finally:
            self._socket.settimeout(prior)

    def recv(self, *args):
        return self._read(self._socket.recv, *args)

    def recv_into(self, *args):
        return self._read(self._socket.recv_into, *args)

    def _write(self, operation, *args):
        prior = self._socket.gettimeout()
        if prior == 0:
            return operation(*args)
        self._socket.settimeout(min(WRITE_TIMEOUT_SECONDS, prior) if prior is not None else WRITE_TIMEOUT_SECONDS)
        try:
            return operation(*args)
        finally:
            self._socket.settimeout(prior)

    def send(self, *args):
        return self._write(self._socket.send, *args)

    def sendall(self, *args):
        return self._write(self._socket.sendall, *args)

    def makefile(self, *args, **kwargs):
        # The qualified parser uses recv and supplies the WSGI body stream.
        raise RuntimeError("Hosted request streams must be supplied by Gunicorn.")


class HostedThreadWorker(_ThreadWorker):
    """Keep Gunicorn parsing/scheduling; bound its socket reads before parsing."""

    def __init__(self, *args, **kwargs):
        if gunicorn is None or gunicorn.__version__ != "26.2.0":
            raise RuntimeError(CONFIGURATION_ERROR)
        super().__init__(*args, **kwargs)

    @classmethod
    def check_config(cls, cfg, log):
        if (gunicorn is None or gunicorn.__version__ != "26.2.0" or cfg.is_ssl
                or cfg.http_protocols != ["h1"] or cfg.http2_cleartext != "off"):
            raise RuntimeError(CONFIGURATION_ERROR)
        return super().check_config(cfg, log)

    def enqueue_req(self, conn):
        # The parent calls this for new, keepalive and deferred connections.
        # The listener and TConn initialization remain untouched.
        if not isinstance(conn.sock, BoundedSocket):
            conn.sock = BoundedSocket(conn.sock)
        conn.sock.begin_request()
        return super().enqueue_req(conn)

    def handle_error(self, req, client, addr, exc):
        # Parent error replies can echo malformed header values. Retain status
        # categories while omitting request, address and exception content.
        status = 500
        if isinstance(exc, _errors.ParseException):
            status = 400
            for name, code in (("LimitRequestHeaders", 431), ("ExpectationFailed", 417),
                               ("ForbiddenProxyRequest", 403), ("UnsupportedTransferCoding", 501),
                               ("ConfigurationProblem", 500)):
                if isinstance(exc, getattr(_errors, name)):
                    status = code
                    break
        self.log.warning("Hosted transport rejected a request. Details omitted.")
        body = b'{"error":"Hosted request was rejected. Private details are omitted."}'
        headers = b"".join(name.encode("ascii") + b": " + value.encode("ascii") + b"\r\n" for name, value in SECURITY_HEADERS)
        response = (f"HTTP/1.1 {status} {HTTPStatus(status).phrase}\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\nConnection: close\r\n".encode("ascii")
                    + headers + b"\r\n" + body)
        try:
            client.sendall(response)
        except OSError:
            pass
