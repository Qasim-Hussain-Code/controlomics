"""Create a local ZIP from the reviewed source inventory, excluding Git and private artifacts."""

import argparse
import hashlib
import json
import tomllib
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from check_release import ROOT, path_problem, source_files, text_findings, png_findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--record', type=Path, required=True)
    args = parser.parse_args()
    names = source_files()
    inventory = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    metadata = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    prefix = 'controlomics-' + metadata['project']['version'] + '/'
    with zipfile.ZipFile(args.output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in names:
            path = ROOT/name
            if path_problem(name) or path.is_symlink() or not path.resolve().is_relative_to(ROOT):
                raise ValueError('public source inventory includes an excluded path')
            raw = path.read_bytes()
            try:
                findings = text_findings(raw.decode('utf-8'))
            except UnicodeDecodeError:
                findings = png_findings(raw) if path.suffix == '.png' else [{'rule': 'unreviewed_binary'}]
            if findings:
                raise ValueError('public source inventory failed privacy screening')
            item = zipfile.ZipInfo(prefix+name, (2026, 10, 7, 0, 0, 0))
            item.create_system = 3
            item.external_attr = 0o100644 << 16
            item.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(item, raw)
            inventory.append({'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    record = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'archive': args.output.name,
              'archive_sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(), 'archive_bytes': args.output.stat().st_size,
              'files': len(inventory), 'source_bytes': sum(item['bytes'] for item in inventory),
              'inventory_sha256': hashlib.sha256(json.dumps(inventory, sort_keys=True).encode()).hexdigest(),
              'git_metadata_included': False, 'ignored_local_artifacts_included': False,
              'license_present': 'LICENSE' in names, 'published': False,
              'scope': 'Reviewed current source snapshot with owner-approved MIT license. Actual GitHub publication and security settings remain separate owner steps.'}
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
