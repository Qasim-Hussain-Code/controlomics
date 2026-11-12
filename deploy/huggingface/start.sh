#!/bin/sh
# Start the Controlomics hosted prototype inside a Hugging Face Docker Space.
set -eu

# The platform supplies the Space host name. A PUBLIC_ORIGIN variable defined
# on the Space takes precedence.
if [ -z "${PUBLIC_ORIGIN:-}" ] && [ -n "${SPACE_HOST:-}" ]; then
  PUBLIC_ORIGIN="https://${SPACE_HOST}"
  export PUBLIC_ORIGIN
fi

# Sessions are held in worker memory and end at every restart, so a fresh
# random value for each start loses nothing. It exists only in this process
# environment. A CONTROLOMICS_SESSION_SECRET defined as a Space secret is kept.
if [ -z "${CONTROLOMICS_SESSION_SECRET:-}" ]; then
  CONTROLOMICS_SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
  export CONTROLOMICS_SESSION_SECRET
fi

exec env -u GUNICORN_CMD_ARGS gunicorn --config gunicorn.conf.py "controlomics.hosted:create_app()"
