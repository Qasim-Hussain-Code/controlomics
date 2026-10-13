"""Create a local ZIP from the reviewed source inventory, excluding Git and private artifacts."""

import argparse
import hashlib
import json
import tomllib
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

if __package__:
    from .check_release import ROOT, path_problem, source_files, text_findings, png_findings
else:
    from check_release import ROOT, path_problem, source_files, text_findings, png_findings
from controlomics.storage import require_distinct_outputs, write_bytes_atomic, write_text_atomic


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--record', type=Path, required=True)
    args = parser.parse_args(argv)
    require_distinct_outputs(args.output, args.record)
    source_root = ROOT.resolve()
    names = source_files()
    for name in names:
        require_distinct_outputs(args.output, ROOT / name)
        require_distinct_outputs(args.record, ROOT / name)
    inventory = []
    metadata = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    prefix = 'controlomics-' + metadata['project']['version'] + '/'
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in names:
            path = ROOT/name
            if path_problem(name) or path.is_symlink() or not path.resolve().is_relative_to(source_root):
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
    archive_bytes = buffer.getvalue()
    write_bytes_atomic(args.output, archive_bytes)
    record = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'archive': args.output.name,
              'archive_sha256': hashlib.sha256(archive_bytes).hexdigest(), 'archive_bytes': len(archive_bytes),
              'files': len(inventory), 'source_bytes': sum(item['bytes'] for item in inventory),
              'inventory_sha256': hashlib.sha256(json.dumps(inventory, sort_keys=True).encode()).hexdigest(),
              'git_metadata_included': False, 'ignored_local_artifacts_included': False,
              'license_present': 'LICENSE' in names, 'published': False,
              'scope': 'Reviewed current source snapshot with owner-approved MIT license. Actual GitHub publication and security settings remain separate owner steps.'}
    write_text_atomic(args.record, json.dumps(record, indent=2)+'\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
