"""Regenerate schemas or check the committed exports for drift."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from controlomics.project import export_json_schemas


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    directory = Path(__file__).resolve().parents[1] / "schemas" / "0.1.0"
    if not args.check:
        export_json_schemas(directory)
        return 0
    with TemporaryDirectory() as temporary:
        paths = export_json_schemas(Path(temporary))
        if {path.name for path in paths} != {path.name for path in directory.glob("*.schema.json")}:
            print("Schema exports are missing or unexpected.")
            return 1
        if any(path.read_bytes() != (directory / path.name).read_bytes() for path in paths):
            print("Schema exports differ from the Python definitions.")
            return 1
    print("Schema exports match the Python definitions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
