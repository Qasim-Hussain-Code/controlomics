"""Build the static in-browser workspace from a built wheel and pinned Pyodide files.

The output directory must not exist. It is prepared beside its destination and
renamed only when complete. Pyodide files are downloaded once into a cache and
accepted only when their SHA-256 matches the values pinned here, which were
checked against the integrity-verified npm release; package wheels must match
the pinned lock file. The built site makes no request to a third party.
"""

import argparse
import hashlib
import json
import re
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT/'src'/'controlomics'/'web'
PYODIDE_VERSION = '314.0.7'
PYODIDE_URL = f'https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/'
# SHA-256 of each core file, matching package/ in the npm tarball for this version.
CORE = {
    'pyodide.mjs': '6f1d60f7bf529beb300f0f47983c921d3982363640ba20af0e38efdddbc66109',
    'pyodide.asm.mjs': 'f7cdc8ece80678ceb712f8e65ebe6d3a83203a180c399865f49612a051693635',
    'pyodide.asm.wasm': 'cc36e3cab04fdfc9a63ff13eb52eae2b911bf46c025cc7b281f394bd3de1d5e6',
    'python_stdlib.zip': 'fa1957e5777068fc4f7437f96d860ae2fbe9c19732ba06c84e004ec16dd7dd7a',
    'pyodide-lock.json': '5dc2fc119108bc148c7457dc86e7675b5c87e1cafd420b9c34c1eaef7b36c010',
}
PACKAGES = ('pydantic',)
ASSETS = ('app.js', 'style.css', 'browser.js', 'browser.css', 'browser_worker.js')
# GitHub Pages cannot send headers, so the page carries the local server's policy
# as a meta element. frame-ancestors has no effect there and is omitted. Approved
# requests go to Europe PMC, Crossref, or a model endpoint the visitor names, so
# connections are limited to HTTPS; the exact-approval gate in Python is the boundary.
POLICY = ("default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self' https:; img-src 'none'; "
          "worker-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cached(name, expected, cache):
    """Return a cached Pyodide file with the expected digest, downloading it if needed."""
    path = cache/name
    if path.is_file() and sha256(path) == expected:
        return path
    cache.mkdir(parents=True, exist_ok=True)
    for _ in range(3):
        try:
            with urllib.request.urlopen(PYODIDE_URL + name, timeout=120) as response:
                raw = response.read()
        except OSError:
            continue
        if hashlib.sha256(raw).hexdigest() == expected:
            partial = path.with_name(path.name + '.part')
            partial.write_bytes(raw)
            partial.replace(path)
            return path
        raise ValueError('downloaded Pyodide file differs from its pinned digest: ' + name)
    raise OSError('Pyodide file could not be downloaded: ' + name)


def required_packages(lock, names):
    """Lock entries for the named packages and their declared dependencies."""
    entries, queue = {}, list(names)
    while queue:
        # Dependencies are listed with either separator; lock keys use the PEP 503 form.
        name = re.sub(r'[-_.]+', '-', queue.pop()).lower()
        if name in entries:
            continue
        entry = lock['packages'][name]
        entries[name] = entry
        queue.extend(entry.get('depends', ()))
    return entries


def page(markup):
    """The interface page with relative asset paths, the policy, and the runtime scripts."""
    for asset in ('/style.css', '/app.js'):
        if markup.count(f'"{asset}"') != 1:
            raise ValueError('interface page asset reference changed: ' + asset)
        markup = markup.replace(f'"{asset}"', f'"{asset[1:]}"')
    head = ('  <meta http-equiv="Content-Security-Policy" content="' + POLICY + '">\n'
            '  <meta name="referrer" content="no-referrer">\n')
    markup = markup.replace('  <meta name="viewport"', head + '  <meta name="viewport"', 1)
    runtime = '  <link rel="stylesheet" href="browser.css">\n  <script src="browser.js"></script>\n'
    if markup.count('  <script src="app.js" defer></script>\n') != 1:
        raise ValueError('interface page script reference changed')
    return markup.replace('  <script src="app.js" defer></script>\n', runtime + '  <script src="app.js" defer></script>\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--wheel', type=Path, required=True, help='Built Controlomics wheel to install in the browser.')
    parser.add_argument('--output', type=Path, default=ROOT/'dist'/'browser', help='New directory for the static site.')
    parser.add_argument('--cache', type=Path, default=ROOT/'local_projects'/'pyodide_cache'/PYODIDE_VERSION,
                        help='Download cache for pinned Pyodide files.')
    args = parser.parse_args(argv)
    if args.output.exists():
        raise SystemExit('The output directory must not exist.')
    if not re.fullmatch(r'controlomics-[0-9A-Za-z.]+-py3-none-any\.whl', args.wheel.name) or not zipfile.is_zipfile(args.wheel):
        raise SystemExit('Supply a built Controlomics wheel.')
    with zipfile.ZipFile(args.wheel) as wheel:
        if 'controlomics/browser.py' not in wheel.namelist():
            raise SystemExit('The wheel does not contain the browser runtime.')
    core = {name: cached(name, digest, args.cache) for name, digest in CORE.items()}
    lock = json.loads(core['pyodide-lock.json'].read_bytes())
    packages = {entry['file_name']: cached(entry['file_name'], entry['sha256'], args.cache)
                for entry in required_packages(lock, PACKAGES).values()}
    staging = args.output.with_name('.' + args.output.name + '.building')
    if staging.exists():
        shutil.rmtree(staging)
    (staging/'pyodide').mkdir(parents=True)
    try:
        (staging/'index.html').write_text(page((WEB/'index.html').read_text(encoding='utf-8')), encoding='utf-8', newline='\n')
        for asset in ASSETS:
            shutil.copyfile(WEB/asset, staging/asset)
        for name, path in {**core, **packages}.items():
            shutil.copyfile(path, staging/'pyodide'/name)
        shutil.copyfile(args.wheel, staging/args.wheel.name)
        # The worker downloads and checks these itself before Pyodide starts, so an
        # interrupted transfer is retried instead of leaving Pyodide waiting.
        manifest = {'pyodide': PYODIDE_VERSION, 'packages': list(PACKAGES),
                    'core': {name: digest for name, digest in CORE.items() if name != 'pyodide.mjs'},
                    'package_files': {entry['file_name']: entry['sha256'] for entry in required_packages(lock, PACKAGES).values()},
                    'wheel': {'file': args.wheel.name, 'sha256': sha256(args.wheel)}}
        (staging/'browser_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
        # Serve files as they are; GitHub Pages would otherwise process the site with Jekyll.
        (staging/'.nojekyll').write_bytes(b'')
        staging.rename(args.output)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    total = sum(path.stat().st_size for path in args.output.rglob('*') if path.is_file())
    print(f'Built {args.output} ({total / 1e6:.1f} MB) with Pyodide {PYODIDE_VERSION}.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
