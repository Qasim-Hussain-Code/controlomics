import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import ValidationError

from controlomics.project import export_json_schemas, parse_project_json
from controlomics.schemas import PUBLIC_SCHEMAS
from tests.fixtures import ROOT, executed_project, payload, reviewed_project


class RecordTests(unittest.TestCase):
    def test_distinct_contexts_round_trip(self):
        for name in ("transcriptomics.project.json", "microscopy_ml.project.json"):
            with self.subTest(name=name):
                project = parse_project_json(json.dumps(payload(name)))
                self.assertEqual(parse_project_json(project.model_dump_json()), project)
                self.assertEqual({item.control_class for item in project.candidates}, {"POSITIVE", "NEGATIVE"})
                self.assertEqual(project.analysis.coverage_status, "UNVALIDATED")

    def test_reviewed_and_executed_records_round_trip(self):
        for data in (reviewed_project(), reviewed_project("METHOD_BASED"), executed_project()):
            with self.subTest(kind=data["controls"][0]["evidence_status"]):
                project = parse_project_json(json.dumps(data))
                self.assertEqual(parse_project_json(project.model_dump_json()), project)

    def test_unknown_fields_and_versions_rejected(self):
        for mutate in (
            lambda data: data["analysis"].update(unexpected="text"),
            lambda data: data["manifest"].update(schema_version="99.0.0"),
            lambda data: data["manifest"].update(ontology_version="99.0.0"),
            lambda data: data["analysis"].update(scientific_question="  \t"),
            lambda data: data["manifest"].update(created_at="2026-10-05T00:00:00"),
        ):
            data = payload()
            mutate(data)
            with self.assertRaises(ValidationError):
                parse_project_json(json.dumps(data))

    def test_strict_scalars_and_frozen_records(self):
        data = payload()
        data["candidates"][0]["evidence_required"] = "false"
        with self.assertRaises(ValidationError):
            parse_project_json(json.dumps(data))
        project = parse_project_json(json.dumps(payload()))
        with self.assertRaises(ValidationError):
            project.analysis.analysis_id = "changed"
        self.assertIsInstance(project.claims, tuple)
        self.assertIsInstance(project.analysis.methods, tuple)

    def test_references_and_duplicate_ids_rejected(self):
        for mutate in (
            lambda data: data["claims"][0].update(analysis_id="missing"),
            lambda data: data["candidates"][0].update(claim_tested="missing"),
            lambda data: data["candidates"][0].update(control_id=data["claims"][0]["claim_id"]),
            lambda data: data["provenance"].append({
                "provenance_id": "provenance.test", "action": "SCHEMA_VALIDATION",
                "recorded_at": "2026-10-05T01:00:00Z", "controlomics_version": "0.1.0.dev0",
                "record_ids": ["missing"],
            }),
        ):
            data = payload()
            mutate(data)
            with self.assertRaises(ValidationError):
                parse_project_json(json.dumps(data))

    def test_execution_input_and_seed_consistency(self):
        for mutate in (
            lambda data: data["results"][0].update(random_seed=8),
            lambda data: data["results"][0].update(random_seed=True),
            lambda data: data["results"][0].update(input_hashes=[]),
            lambda data: data["execution_plans"][0].update(required_inputs=[]),
            lambda data: data["results"][0].update(execution_id="missing"),
        ):
            data = executed_project()
            mutate(data)
            with self.assertRaises(ValidationError):
                parse_project_json(json.dumps(data))

    def test_required_input_ids_cannot_repeat(self):
        data = payload()
        inputs = data["candidates"][0]["required_inputs"]
        inputs.append(dict(inputs[0]))
        with self.assertRaises(ValidationError):
            parse_project_json(json.dumps(data))

    def test_schema_exports_and_checked_in_drift(self):
        with TemporaryDirectory() as directory:
            paths = export_json_schemas(Path(directory))
            self.assertEqual(len(paths), len(PUBLIC_SCHEMAS))
            for path in paths:
                schema = json.loads(path.read_text(encoding="utf-8"))
                self.assertFalse(schema["additionalProperties"])
                self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertEqual(path.read_bytes(), (ROOT / "schemas" / "0.1.0" / path.name).read_bytes())

    def test_ontology_matches_schema_vocabulary(self):
        ontology = json.loads((ROOT / "ontology" / "control_ontology.v0.1.0.json").read_text())
        from typing import get_args
        from controlomics.schemas import ControlClass, EvidenceStatus, ScientificLevel

        self.assertEqual(set(ontology["control_classes"]), set(get_args(ControlClass)))
        self.assertEqual(set(ontology["scientific_levels"]), set(get_args(ScientificLevel)))
        self.assertEqual(set(ontology["evidence_states"]), set(get_args(EvidenceStatus)))
