"""Audit our local wheel and source distribution for private contents and account metadata."""

import argparse
import hashlib
import json
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from check_release import path_problem, png_findings, text_findings


def check_text(name, raw):
    try:
        return text_findings(raw.decode('utf-8'))
    except UnicodeDecodeError:
        return png_findings(raw) if name.endswith('.png') else [{'rule': 'unreviewed_binary'}]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--sdist', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    findings = []
    files = []
    with zipfile.ZipFile(args.wheel) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            findings.append({'artifact': 'wheel', 'rule': 'duplicate_members'})
        for name in ('controlomics/hosted.py', 'controlomics/hosted_worker.py', 'controlomics/hosting_privacy.py'):
            if name not in names:
                findings.append({'artifact': 'wheel', 'path': name, 'rule': 'required_source_missing'})
        for name in names:
            if path_problem(name):
                findings.append({'artifact': 'wheel', 'path': name, 'rule': 'excluded_path'})
            if not name.startswith('controlomics/') and '.dist-info/' not in name:
                findings.append({'artifact': 'wheel', 'path': name, 'rule': 'unexpected_package'})
            raw = archive.read(name)
            findings.extend({'artifact': 'wheel', 'path': name, **item} for item in check_text(name, raw))
        files.append({'artifact': args.wheel.name, 'sha256': hashlib.sha256(args.wheel.read_bytes()).hexdigest(),
                      'members': len(names), 'bytes': args.wheel.stat().st_size})
    with tarfile.open(args.sdist, 'r:gz') as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        if len(names) != len(set(names)):
            findings.append({'artifact': 'sdist', 'rule': 'duplicate_members'})
        for member in members:
            if not (member.isfile() or member.isdir()):
                findings.append({'artifact': 'sdist', 'path': member.name, 'rule': 'nonregular_member'})
                continue
            if member.uname or member.gname or member.uid or member.gid:
                findings.append({'artifact': 'sdist', 'path': member.name, 'rule': 'build_account_metadata'})
            name = '/'.join(member.name.split('/')[1:])
            generated = name == 'src/controlomics.egg-info' or name.startswith('src/controlomics.egg-info/')
            if name and not generated and path_problem(name):
                findings.append({'artifact': 'sdist', 'path': name, 'rule': 'excluded_path'})
            if member.isfile():
                raw = archive.extractfile(member).read()
                findings.extend({'artifact': 'sdist', 'path': name, **item} for item in check_text(name, raw))
        required = {'README.md', 'LICENSE', 'pyproject.toml', 'MANIFEST.in', 'src/controlomics/web/index.html',
                    'scripts/scientific_reference.py', 'scripts/run_numerical_validation.py',
                    'docs/validation/numerical_protocol.json', 'requirements-validation.lock',
                    'tests/privacy/test_local_boundary.py', 'schemas/0.1.0/ControlomicsProject.schema.json'}
        required.update({'render.yaml', 'gunicorn.conf.py', '.python-version', 'requirements-cloud.lock',
                         'src/controlomics/hosted.py', 'src/controlomics/hosted_worker.py',
                         'src/controlomics/hosting_privacy.py', 'scripts/check_hosted_transport.py'})
        present = {'/'.join(name.split('/')[1:]) for name in names}
        for name in sorted(required-present):
            findings.append({'artifact': 'sdist', 'path': name, 'rule': 'required_source_missing'})
        files.append({'artifact': args.sdist.name, 'sha256': hashlib.sha256(args.sdist.read_bytes()).hexdigest(),
                      'members': len(names), 'bytes': args.sdist.stat().st_size})
    record = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'artifacts': files, 'findings': findings,
              'status': 'PASS' if not findings else 'FAIL', 'published': False,
              'scope': 'Our locally built distributions: member paths, scanned text, PNG metadata, required reproducibility files and tar ownership. No independent security certification.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(record, indent=2))
    return 0 if not findings else 1


if __name__ == '__main__':
    raise SystemExit(main())
