"""Check public source hygiene locally; no network requests or uploads."""

import argparse
import hashlib
import json
import re
import subprocess
import tomllib
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {'.git', '.venv', 'local_projects', 'data', 'cache', 'dist', 'build',
            '__pycache__', '.private', '.aws', '.ssh'}
SYNTHETIC_CSV = {'examples/positive_reference.csv', 'examples/negative_reference.csv',
                 'examples/paired_reference.csv'}
SECRET_PATTERNS = {
    'private_key': r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
    'aws_access_key': r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
    'github_token': r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b',
    'provider_key': r'\b(?:sk-(?:proj-)?[A-Za-z0-9_-]{32,}|hf_[A-Za-z0-9]{30,}|AIza[A-Za-z0-9_-]{35})\b',
    'personal_home_path': r'(?:[A-Za-z]:[\\/]+Users[\\/]+[A-Za-z0-9_.-]+[\\/][^\s"\'<>]*|/(?:Users|home)/[A-Za-z0-9_.-]+/[^\s"\'<>]*)',
}


def text_findings(content):
    """Return rule and line only. Never echo a matched secret."""
    findings = []
    for rule, pattern in SECRET_PATTERNS.items():
        for match in re.finditer(pattern, content):
            findings.append({'rule': rule, 'line': content.count('\n', 0, match.start()) + 1})
    for match in re.finditer(r'[\w.%+-]+@([\w.-]+\.[A-Za-z]{2,})', content):
        domain = match.group(1).lower()
        if domain not in {'example.com', 'example.org', 'example.invalid', 'test.invalid'}:
            findings.append({'rule': 'email_address', 'line': content.count('\n', 0, match.start()) + 1})
    return findings


def path_problem(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
        return 'unsafe_path'
    if any(part in EXCLUDED or part.endswith('.egg-info') for part in path.parts):
        return 'private_or_generated_directory'
    if path.name.startswith('.env') and path.name != '.env.example':
        return 'environment_file'
    if path.suffix.lower() in {'.key', '.pem', '.p12', '.pfx', '.jks', '.log', '.pyc',
                               '.xlsx', '.xls', '.fastq', '.fq', '.fasta', '.bam', '.h5', '.h5ad'}:
        return 'private_or_generated_file_type'
    if path.suffix.lower() == '.csv' and name not in SYNTHETIC_CSV:
        return 'unreviewed_dataset'
    return None


def png_findings(raw):
    """Reject identifying PNG metadata rather than trying to recognize its text."""
    if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
        return [{'rule': 'invalid_png'}]
    findings = []
    cursor = 8
    while cursor < len(raw):
        if cursor+12 > len(raw):
            return [{'rule': 'invalid_png'}]
        size = int.from_bytes(raw[cursor:cursor+4], 'big')
        kind = raw[cursor+4:cursor+8]
        if cursor+size+12 > len(raw):
            return [{'rule': 'invalid_png'}]
        if kind in {b'tEXt', b'zTXt', b'iTXt', b'eXIf'}:
            findings.append({'rule': 'image_metadata'})
        cursor += size+12
    return findings


def git(*args):
    return subprocess.run(['git', '-c', f'safe.directory={ROOT.as_posix()}', *args],
                          cwd=ROOT, check=True, capture_output=True, timeout=60).stdout


def source_files():
    if (ROOT / '.git').exists():
        names = git('ls-files', '--cached', '--others', '--exclude-standard', '-z').decode().split('\0')
        return sorted({name for name in names if name and (ROOT / name).exists()})
    # Also usable in an extracted source distribution, without local Git metadata.
    return sorted(path.relative_to(ROOT).as_posix() for path in ROOT.rglob('*')
                  if path.is_file() and not any(part in EXCLUDED or part.endswith('.egg-info')
                                               for part in path.relative_to(ROOT).parts)
                  and path.name != 'PKG-INFO')


def link_findings(name, content):
    findings = []
    for match in re.finditer(r'!?\[[^\]]*\]\(([^)]+)\)', content):
        target = match.group(1).strip('<>')
        if urlsplit(target).scheme or target.startswith('#'):
            continue
        target = unquote(target.split('#', 1)[0])
        if target and not (ROOT / name).parent.joinpath(target).exists():
            findings.append({'path': name, 'rule': 'missing_document_link', 'target': target})
    return findings


def check_history():
    findings = []
    commits = git('log', '--all', '--format=%H%x00%an%x00%ae%x00%cn%x00%ce').decode().splitlines()
    for line in commits:
        sha, author, email, committer, committer_email = line.split('\0')
        if (author, email, committer, committer_email) != ('Controlomics', '', 'Controlomics', ''):
            findings.append({'object': sha, 'rule': 'personal_git_attribution'})
    objects = git('rev-list', '--objects', '--all').splitlines()
    ids = [line.split(b' ', 1)[0] for line in objects]
    # One batch process, bounded by this small repository's object inventory.
    output = subprocess.run(['git', '-c', f'safe.directory={ROOT.as_posix()}', 'cat-file', '--batch'],
                            input=b'\n'.join(ids)+b'\n', cwd=ROOT, capture_output=True,
                            check=True, timeout=60).stdout
    cursor = 0
    for expected in ids:
        end = output.index(b'\n', cursor)
        sha, kind, length = output[cursor:end].split()
        size = int(length)
        content = output[end+1:end+1+size]
        cursor = end+size+2
        if sha != expected:
            raise ValueError('Git object batch differs from the requested inventory')
        if kind in {b'blob', b'commit', b'tag'}:
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                continue
            findings.extend({'object': sha.decode(), **item} for item in text_findings(text))
    git('fsck', '--full', '--strict', '--no-reflogs')
    return {'commits_checked': len(commits), 'reachable_objects_checked': len(ids),
            'fsck': 'PASS', 'findings': findings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', action='store_true')
    parser.add_argument('--require-license', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    names = source_files()
    findings = []
    inventory = []
    for name in names:
        path = ROOT / name
        problem = path_problem(name)
        if problem or path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            findings.append({'path': name, 'rule': problem or 'symbolic_link'})
            continue
        raw = path.read_bytes()
        inventory.append({'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
        try:
            content = raw.decode('utf-8')
        except UnicodeDecodeError:
            if path.suffix.lower() != '.png':
                findings.append({'path': name, 'rule': 'unreviewed_binary'})
            else:
                findings.extend({'path': name, **item} for item in png_findings(raw))
            continue
        findings.extend({'path': name, **item} for item in text_findings(content))
        if path.suffix == '.md':
            findings.extend(link_findings(name, content))
    metadata = tomllib.loads((ROOT/'pyproject.toml').read_text(encoding='utf-8'))['project']
    if any(metadata.get(field) for field in ('authors', 'maintainers')):
        findings.append({'rule': 'personal_package_attribution'})
    protocol = json.loads((ROOT/'docs/validation/numerical_protocol.json').read_bytes())
    for name, expected in protocol['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
            findings.append({'path': name, 'rule': 'frozen_numerical_source_changed'})
    workflow = (ROOT/'.github/workflows/ci.yml')
    if workflow.exists():
        text = workflow.read_text(encoding='utf-8')
        if 'pull_request_target' in text or 'contents: write' in text or '${{ secrets.' in text:
            findings.append({'rule': 'privileged_ci_configuration'})
        for action in re.findall(r'uses:\s*([^\s#]+)', text):
            if not re.fullmatch(r'[^@]+@[0-9a-f]{40}', action):
                findings.append({'rule': 'unpinned_ci_action'})
    license_present = (ROOT/'LICENSE').is_file()
    if args.require_license and not license_present:
        findings.append({'rule': 'owner_license_decision_pending'})
    if license_present and (metadata.get('license') != 'MIT' or metadata.get('license-files') != ['LICENSE']):
        findings.append({'rule': 'license_metadata_mismatch'})
    history = check_history() if args.history else {'status': 'NOT_RUN'}
    findings.extend(history.get('findings', []))
    record = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'source_files_checked': len(names),
              'source_bytes': sum(item['bytes'] for item in inventory),
              'inventory_sha256': hashlib.sha256(json.dumps(inventory, sort_keys=True).encode()).hexdigest(),
              'checks': {'frozen_numerical_sources': 'PASS' if not any(item['rule']=='frozen_numerical_source_changed' for item in findings) else 'FAIL',
                         'license_file_present': license_present, 'history': history},
              'findings': findings, 'status': 'PASS' if not findings else 'FAIL',
              'publication_authorized': False,
              'limitations': ['Pattern screening cannot recognize every secret, identity, confidential fact, or licensing problem.',
                              'Public bibliography and declared synthetic fixtures require human provenance review.',
                              'No hosted CI, repository security setting, external publication, expert scientific review, or independent security audit is performed.']}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(record, indent=2))
    return 0 if not findings else 1


if __name__ == '__main__':
    raise SystemExit(main())
