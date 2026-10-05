# Project format 0.1.0

The initial format is one UTF-8 JSON document. The `manifest.format` is `controlomics.project`; schema and ontology versions are `0.1.0`. Package version is recorded separately and may include a development suffix. Unsupported schema or ontology versions are rejected. There is no migration implementation yet.

Required top-level records are `manifest`, `analysis`, `claims`, and `privacy`. Optional arrays are `claim_relations`, `evidence`, `candidates`, `controls`, `execution_plans`, `results`, `audits`, and `provenance`. Empty arrays mean no records were supplied, not that a review found no problems. Unknown keys are rejected. Required scientific text must contain a nonwhitespace character. JSON timestamps must include a timezone.

All project, analysis, claim, evidence, control, execution, result, audit, and provenance IDs must be globally unique. References must resolve locally. A reviewed control replaces the corresponding candidate record in a project snapshot rather than duplicating its control ID in both arrays. Preserve the candidate snapshot separately when needed. Claim relations may describe scientific dependencies, but there is no causal inference algorithm or graph-cycle interpretation.

Evidence identifiers are typed by namespace and issuing authority. DOI comparison is case-insensitive. Identical DOI, PMID, PMCID, or authority-scoped accession keys across records require consolidation. Disjoint aliases cannot yet be recognized as the same publication. Identity checks are distinct from statement-specific evidence links. A review receipt is an attestation, not authenticated proof.

Checked identities must follow retrieval, entailment checks must follow recorded identity checks, and control review must follow its entailment checks. Control input IDs must be unique. Privacy classification cannot understate declared input or control requirements. Timestamp and classification consistency do not establish the underlying scientific facts.

Execution inputs must match the control specification. Completed results must record hashes for all and only the specified inputs. Result seed and control ID must match the execution plan. PASS or FAIL requires a matching decision rule specified before execution began. Recorded software versions describe the actual execution and may differ from planned versions; scientific review must assess such deviations. ROBUST assessments cannot reference nonpassing results, and CONTROL_FAILURE requires a failed scientific outcome, distinct from software execution failure.

Provenance refers to existing record IDs and records no raw research data by default. Raw query and prompt storage is excluded from the initial provenance model; query and template hashes can be recorded. Users must still review free-text fields for private content. A project can contain confidential scientific descriptions even when it is structurally valid.

The local loader limits input to 2 MiB and rejects duplicate JSON keys, nonfinite JSON constants, malformed records, and unresolved references. The CLI emits redacted failures. Direct use of Pydantic's JSON parser bypasses the duplicate-key and file-size checks, so untrusted projects should enter through `parse_project_json` or `load_project`.

The checked-in `schemas/0.1.0/*.schema.json` files describe structure using JSON Schema draft 2020-12. Python post-validation additionally checks evidence gates, context summaries, ID uniqueness, relationships, and timing. Third-party JSON Schema acceptance alone does not establish these invariants. The ontology is a separate versioned vocabulary file under `ontology/`.

Future formats may split a project into manifest, claim, evidence, control, execution, results, audit, provenance, and report files. That layout is not implemented here. Any change requires an explicit migration policy and security review.
