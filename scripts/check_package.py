"""Inspect a locally built wheel and smoke-test its extracted package offline."""

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from email.parser import Parser
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory

from controlomics import __version__


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assets = ["controlomics/web/" + name for name in ("index.html", "app.js", "style.css")]
    with zipfile.ZipFile(args.wheel) as archive, TemporaryDirectory(prefix="controlomics_wheel_check_") as temporary:
        names = archive.namelist()
        if any(PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts or "\\" in name or ":" in name for name in names):
            raise ValueError("wheel contains an unsafe extraction path")
        metadata = Parser().parsestr(archive.read(next(name for name in names if name.endswith(".dist-info/METADATA"))).decode())
        if metadata["Name"] != "controlomics" or metadata["Version"] != __version__ or metadata["Author"] != "Private attribution removed":
            raise ValueError("package identity differs from the development metadata")
        if not all(name in names for name in assets):
            raise ValueError("wheel is missing local browser assets")
        archive.extractall(temporary)
        script = """import json, sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import controlomics
from controlomics.server import handle_action
from controlomics.evaluation import EvaluationBundle, evaluate
from controlomics.statistics import paired_permutation
from controlomics.artifacts import create_review_bundle, open_review_bundle
from controlomics.project import parse_project_json
assert Path(controlomics.__file__).is_relative_to(Path(sys.argv[1]))
draft=handle_action('/api/interpret',{'description':'Question: A synthetic wheel check\\nClaim: A stated claim'})['draft']
assert draft['fields']['claim']=='A stated claim'
assert 'observed_result' in draft['missing_fields']
assets=Path(controlomics.__file__).parent/'web'
assert all((assets/name).is_file() for name in ('index.html','app.js','style.css'))
assert 'evaluation-form' in (assets/'index.html').read_text(encoding='utf-8')
assert 'annotation-form' in (assets/'index.html').read_text(encoding='utf-8')
assert paired_permutation([1.0,2.0,3.0])['p_value']==0.25
project=parse_project_json(Path(sys.argv[2]).read_bytes())
assert open_review_bundle(create_review_bundle(project))[0]==project
print(json.dumps({'version':controlomics.__version__,'imported_extracted_wheel':True,'local_draft':True,'browser_assets':True,'evaluation_import':True,'paired_arithmetic':True,'review_archive_roundtrip':True}))
"""
        example = Path(__file__).resolve().parents[1] / "examples" / "transcriptomics.project.json"
        result = subprocess.run([sys.executable, "-I", "-c", script, temporary, str(example)], capture_output=True, text=True, timeout=20, check=True)
        smoke = json.loads(result.stdout)
    record = {"recorded_at": datetime.now(timezone.utc).isoformat(), "wheel": args.wheel.name,
        "wheel_sha256": hashlib.sha256(args.wheel.read_bytes()).hexdigest(), "wheel_bytes": args.wheel.stat().st_size,
        "metadata": {"name": metadata["Name"], "version": metadata["Version"], "author": metadata["Author"]},
        "assets": assets, "smoke": smoke,
        "scope": "Extracted package import and local interface smoke check using the existing Python/Pydantic environment. No external request, new dependency, or scientific validation."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
