# Hugging Face Docker Space for the Controlomics hosted prototype.
# The Space holds this file and README.md only. The build downloads the public
# source archive at CONTROLOMICS_REF and installs the exact cloud dependencies.
FROM python:3.14-slim

ARG CONTROLOMICS_REF=main

# CONTROLOMICS_TRUST_PROXY=render selects the private-peer forwarding check
# written first for Render: HTTPS is accepted only when a direct private or
# loopback peer forwards it with the exact canonical Host.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    CONTROLOMICS_TRUST_PROXY=render

WORKDIR /srv/controlomics

RUN python -c "import io, os, tarfile, urllib.request; \
url = 'https://codeload.github.com/Qasim-Hussain-Code/controlomics/tar.gz/' + os.environ['CONTROLOMICS_REF']; \
archive = tarfile.open(fileobj=io.BytesIO(urllib.request.urlopen(url, timeout=120).read())); \
members = [member for member in archive.getmembers() if '/' in member.name]; \
[setattr(member, 'name', member.name.split('/', 1)[1]) for member in members]; \
archive.extractall('.', members=members, filter='data')" \
 && python -m pip install --no-cache-dir -r requirements-cloud.lock \
 && python -m pip install --no-cache-dir --no-build-isolation --no-deps . \
 && useradd --uid 1000 --no-create-home --shell /usr/sbin/nologin controlomics

USER 1000
EXPOSE 7860
CMD ["sh", "deploy/huggingface/start.sh"]
