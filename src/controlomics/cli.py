"""Local validation commands with redacted failure messages."""

import argparse
from pathlib import Path

from controlomics import __version__
from controlomics.project import export_json_schemas, load_project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="controlomics")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Validate a local project without network access")
    validate.add_argument("project", type=Path)
    schemas = commands.add_parser("export-schemas", help="Export versioned JSON Schemas")
    schemas.add_argument("directory", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            project = load_project(args.project)
            warning_count = sum(len(claim.interpretation_warnings) for claim in project.claims)
            print("Project structure and references are valid. Scientific validity has not been established.")
            if warning_count:
                print(f"Claim interpretation warnings: {warning_count}. Computational support does not establish causation.")
        else:
            paths = export_json_schemas(args.directory)
            print(f"Exported {len(paths)} structural schemas. Use the Python validator for relational checks.")
    except (ValueError, OSError, RecursionError):
        print("Validation or file operation failed. Input content and local paths are omitted.")
        return 1
    return 0
