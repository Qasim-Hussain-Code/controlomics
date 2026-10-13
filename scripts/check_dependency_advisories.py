"""Query OSV using only public package names and exact versions from the lock files."""

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-public-version-query', action='store_true', required=True,
                        help='Authorize sending only public dependency names and versions to api.osv.dev.')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    packages = {}
    for name in ('requirements-dev.lock', 'requirements-validation.lock', 'requirements-quality.lock',
                 'requirements-cloud.lock'):
        for line in (root/name).read_text(encoding='utf-8').splitlines():
            match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)', line.strip())
            if match:
                packages[match[1]] = match[2]
    selected = sorted(packages.items())
    payload = {'queries': [{'package': {'name': name, 'ecosystem': 'PyPI'}, 'version': version}
                           for name, version in selected]}
    request = Request('https://api.osv.dev/v1/querybatch', data=json.dumps(payload).encode(),
                      headers={'Content-Type': 'application/json', 'User-Agent': 'Controlomics-release-check'}, method='POST')
    with urlopen(request, timeout=25) as response:
        raw = response.read(2*1024*1024+1)
    if len(raw) > 2*1024*1024:
        raise ValueError('advisory response exceeds the check limit')
    results = json.loads(raw)['results']
    if len(results) != len(selected):
        raise ValueError('advisory response differs from the public package inventory')
    findings = [{'name': name, 'version': version, 'advisory_ids': sorted(item['id'] for item in result.get('vulns', []))}
                for (name, version), result in zip(selected, results)]
    record = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'service': 'https://api.osv.dev/v1/querybatch',
              'sent_fields': ['public package name', 'PyPI ecosystem', 'public package version'],
              'packages': findings, 'response_sha256': hashlib.sha256(raw).hexdigest(),
              'status': 'NO_MATCHED_ADVISORIES' if not any(item['advisory_ids'] for item in findings) else 'ADVISORIES_REQUIRE_REVIEW',
              'limitations': ['A point-in-time advisory lookup is not a security audit or proof of absence of vulnerabilities.',
                              'Only exact versions in the development, optional validation, lint and cloud locks were queried; Python, browsers, CI actions, operating systems and future dependency resolutions are outside this check.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(record, indent=2))
    return 0 if record['status']=='NO_MATCHED_ADVISORIES' else 1


if __name__ == '__main__':
    raise SystemExit(main())
