"""Run the ordinary software suite and record counts without local paths or private values."""

import argparse
import json
import platform
import time
import unittest
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from controlomics import __version__


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    started = time.perf_counter()
    suite = unittest.defaultTestLoader.discover(str(root/'tests'), top_level_dir=str(root))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    record = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'controlomics_version': __version__, 'python': platform.python_version(),
              'operating_system': platform.system(), 'pydantic': version('pydantic'), 'setuptools': version('setuptools'),
              'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'skips': len(result.skipped), 'seconds': round(time.perf_counter()-started, 3),
              'status': 'PASS' if result.wasSuccessful() else 'FAIL',
              'scope': 'Software behavior using synthetic fixtures and mocked provider transports; no independent scientific validation.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(record, indent=2))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
