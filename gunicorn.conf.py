"""Bounded single-worker deployment; research content must never enter logs."""

import logging
import os

bind = "0.0.0.0:" + os.environ.get("PORT", "10000")
workers = 1
worker_class = "controlomics.hosted_worker.HostedThreadWorker"
threads = 4
worker_connections = 32
worker_tmp_dir = "/dev/shm"
timeout = 60
graceful_timeout = 60
keepalive = 2
limit_request_line = 4094
limit_request_fields = 32
limit_request_field_size = 4096
accesslog = None
errorlog = "-"
loglevel = "warning"
capture_output = False
# The adapter verifies proxy address, canonical Host and HTTPS itself. Gunicorn
# must not convert arbitrary forwarded headers into a trusted HTTPS scheme.
forwarded_allow_ips = ""
secure_scheme_headers = {}
forwarder_headers = ""
strip_header_spaces = False
permit_obsolete_folding = False
permit_unconventional_http_method = False
permit_unconventional_http_version = False
casefold_http_method = False
header_map = "refuse"
http_protocols = "h1"
http2_cleartext = "off"


class _RedactedDiagnostics(logging.Filter):
    def filter(self, record):
        record.msg = "Hosted server diagnostic. Request and internal details omitted."
        record.args = ()
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return True


def on_starting(server):
    # The host can inject --access-logfile after this file is loaded. Enforce
    # the privacy policy after argument parsing, including an existing service
    # that still uses the previous stored start command.
    server.cfg.set("accesslog", None)
    server.log.access_log.disabled = True
    # Gunicorn can include invalid header values in warning messages. Apply the
    # filter before workers start; it is inherited by the single worker.
    redact = _RedactedDiagnostics()
    server.log.error_log.addFilter(redact)
    logging.getLogger("gunicorn.http.wsgi").addFilter(redact)
