"""Install a built wheel in a clean temporary environment and smoke-test offline behavior."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import venv
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    package = parser.add_mutually_exclusive_group(required=True)
    package.add_argument('--wheel', type=Path)
    package.add_argument('--sdist', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--wheelhouse', type=Path, help='Use only locally downloaded dependency wheels; no index.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    artifact = (args.wheel or args.sdist).resolve(strict=True)
    with TemporaryDirectory(prefix='controlomics_install_check_') as temporary:
        base = Path(temporary)
        environment = base/'environment'
        print('Creating a clean temporary environment.', flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment/('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
        command = [str(python), '-m', 'pip', 'install', '--disable-pip-version-check', '--no-cache-dir',
                   '--constraint', str(root/'requirements-dev.lock')]
        if args.wheelhouse:
            command += ['--no-index', '--find-links', str(args.wheelhouse.resolve(strict=True))]
        if args.sdist:
            builder = [str(python), '-m', 'pip', 'install', '--disable-pip-version-check', '--no-cache-dir',
                       '--constraint', str(root/'requirements-dev.lock'), 'setuptools==83.0.0']
            if args.wheelhouse:
                builder += ['--no-index', '--find-links', str(args.wheelhouse.resolve(strict=True))]
            subprocess.run(builder, cwd=base, capture_output=True, check=True, timeout=120)
            command.append('--no-build-isolation')
        command.append(str(artifact))
        print('Installing our local ' + ('wheel.' if args.wheel else 'source distribution.'), flush=True)
        try:
            subprocess.run(command, cwd=base, capture_output=True, check=True, timeout=180)
        except subprocess.CalledProcessError as error:
            diagnostics = base/'diagnostics.txt'
            diagnostic_text = ((error.stdout or b'') + (error.stderr or b'')).decode('utf-8', errors='replace')
            diagnostic_text = re.sub(re.escape(os.path.expanduser('~')), '<home>', diagnostic_text, flags=re.IGNORECASE)
            diagnostics.write_text(diagnostic_text, encoding='utf-8')
            # Keep diagnostic output local and omit it from public records.
            local = root/'local_projects/release'
            local.mkdir(parents=True, exist_ok=True)
            (local/'install_failure.log').write_bytes(diagnostics.read_bytes())
            raise RuntimeError('clean installation failed; see local_projects/release/install_failure.log') from None
        subprocess.run([str(python), '-m', 'pip', 'check'], cwd=base, capture_output=True, check=True, timeout=20)
        print('Checking isolated imports and CLI behavior.', flush=True)
        smoke = '''import importlib.metadata, json, sys
from pathlib import Path
import controlomics
from controlomics.server import handle_action
from controlomics.statistics import paired_permutation
from controlomics.project import parse_project_json
from controlomics.artifacts import create_review_bundle, open_review_bundle
assert Path(controlomics.__file__).is_relative_to(Path(sys.prefix))
metadata = importlib.metadata.metadata('controlomics')
assert not any(metadata.get_all(key) for key in ('Author','Author-email','Maintainer','Maintainer-email'))
assert metadata['License-Expression']=='MIT'
assert metadata.get_all('License-File')==['LICENSE']
assert handle_action('/api/interpret', {'description':'Question: Synthetic installation check\\nClaim: A synthetic claim'})['draft']['fields']['claim']=='A synthetic claim'
assert paired_permutation([1.,2.,3.])['p_value']==0.25
assets = Path(controlomics.__file__).parent/'web'
assert all((assets/name).is_file() for name in ('index.html','app.js','style.css'))
project = parse_project_json(Path(sys.argv[1]).read_bytes())
assert open_review_bundle(create_review_bundle(project))[0]==project
print(json.dumps({'version':controlomics.__version__, 'dependency_version':importlib.metadata.version('pydantic'), 'imported_clean_install':True, 'browser_assets':True, 'local_drafting':True, 'paired_arithmetic':True, 'review_bundle_roundtrip':True}))
'''
        result = subprocess.run([str(python), '-I', '-c', smoke, str(root/'examples/transcriptomics.project.json')],
                                cwd=base, capture_output=True, text=True, check=True, timeout=30)
        cli = subprocess.run([str(python), '-I', '-m', 'controlomics', 'validate', str(root/'examples/transcriptomics.project.json')],
                             cwd=base, capture_output=True, check=True, timeout=20)
        record = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'artifact': artifact.name,
                  'artifact_sha256': hashlib.sha256(artifact.read_bytes()).hexdigest(),
                  'artifact_type': 'WHEEL' if args.wheel else 'SOURCE_DISTRIBUTION',
                  'clean_environment': True, 'cli_validation': cli.returncode == 0,
                  'dependency_installation': 'LOCAL_WHEELS' if args.wheelhouse else 'PUBLIC_PACKAGE_INDEX',
                  'smoke': json.loads(result.stdout), 'status': 'PASS',
                  'scope': 'Fresh virtual environment; isolated imports and CLI from outside the source checkout. No provider or research requests.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
