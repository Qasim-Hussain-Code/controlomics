"""Bounded local JSON parsing and machine-readable schema export."""

import json
from pathlib import Path

from controlomics import SCHEMA_VERSION
from controlomics.schemas import ControlomicsProject, PUBLIC_SCHEMAS

MAX_PROJECT_BYTES = 2 * 1024 * 1024


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON keys are not permitted")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("nonfinite JSON numbers are not permitted")


def parse_project_json(content: bytes | str) -> ControlomicsProject:
    """Validate local input. No evidence is retrieved or scientifically verified."""

    if isinstance(content, str):
        content = content.encode("utf-8")
    if len(content) > MAX_PROJECT_BYTES:
        raise ValueError("project exceeds the local size limit")
    json.loads(content, object_pairs_hook=_unique_keys, parse_constant=_reject_constant)
    return ControlomicsProject.model_validate_json(content)


def load_project(path: Path) -> ControlomicsProject:
    with path.open("rb") as stream:
        return parse_project_json(stream.read(MAX_PROJECT_BYTES + 1))


def export_json_schemas(directory: Path) -> tuple[Path, ...]:
    """Export structural schemas; Python validators also enforce record relationships."""

    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for schema in PUBLIC_SCHEMAS:
        document = schema.model_json_schema()
        document["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        document["$id"] = f"urn:controlomics:schema:{SCHEMA_VERSION}:{schema.__name__}"
        path = directory / f"{schema.__name__}.schema.json"
        path.write_text(json.dumps(document, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")
        paths.append(path)
    return tuple(paths)
