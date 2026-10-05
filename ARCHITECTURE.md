# Architecture

## Implemented boundary

The initial implementation is a single `src/controlomics` Python package. `schemas.py` defines the scientific records and consistency rules. `project.py` parses bounded local JSON and exports JSON Schemas. `cli.py` exposes validation and export. `ontology/` contains the scientific vocabulary. `examples/` contains two hypothetical local projects. `tests/` separates software, scientific invariants, privacy, and adversarial input checks.

The fundamental object is a scientific claim attached to an analysis and context. Analysis methods are free descriptive fields, not a fixed dispatch list. Claim relationships describe proposed dependencies and associations; a proposed causal relationship does not establish causation. Computational support and claimed category remain separate.

Collections are immutable tuples in frozen models. Fields reject unknown keys, implicit scalar coercion, nonfinite numerical results, and unsupported schema versions. JSON input represents tuples as arrays and timestamps as timezone-aware strings. Library calls with Python objects use strict Python types. Nested records are revalidated.

## Planned scientific pipeline

1. Receive a minimized analysis description and researcher claim locally.
2. Interpret the claim into validated records and retain uncertainties.
3. Obtain candidate controls through a provider-independent reasoning interface.
4. Retrieve entities and publications through interchangeable evidence providers.
5. Check publication identity, statement entailment, conflicting findings, and context compatibility separately.
6. Record a reviewed control with an inspectable evidence state and prioritization rationale.
7. Construct a local or dispatched execution package when feasible.
8. Import structured results, critique interpretations, and write provenance and a report.

Stages after structured input are design commitments, not working capabilities. Future model and evidence interfaces must receive a minimized outbound request object created by a privacy boundary. Providers must not receive an entire project implicitly. Statistical calculations belong to deterministic execution adapters. Imported or generated code must never execute during validation.

## Evidence boundary

`ControlCandidate` accepts proposed or unverified states. `VerifiedControl` adds an explicit review receipt, including reviews that find insufficient or conflicting evidence. The type name denotes a completed review record, not unconditional scientific support.

Evidence-backed records require checked support for both the exact rationale statement and expected-behavior statement, a compatible or explicitly partial context assessment, and no recorded contradiction. Each assessed evidence link must reference an evidence item with a recorded identity check. These requirements block inconsistent declarations. They do not establish that the supplied checks are authentic or scientifically correct.

METHOD_BASED is reserved for controls whose specified justification does not require biological evidence. A method basis remains a documented argument with assumptions. It is not empirical biological validation. Biological negative controls and statistical null procedures have distinct class and level fields.

Context summaries must agree with dimension comparisons. A MATCH applies only to the listed assessed dimensions. Relevance and completeness of those dimensions require scientific review. Automatic matching of comparison values to source context is deferred.

## Resource and dependency plan

Pydantic is the sole runtime dependency. It supplies [strict validation](https://docs.pydantic.dev/latest/concepts/strict_mode/) and [JSON Schema export](https://docs.pydantic.dev/latest/concepts/json_schema/). Standard-library `unittest` provides the initial checks. Setuptools builds and installs the package. No provider SDK, scientific numerical stack, database, vector store, agent framework, container, model weights, GPU, or raw research dataset is required.

The initial target was less than 150 MB of additional local disk space and comfortably below 1 GB of RAM for routine development checks. The observed local environment occupied approximately 31.3 MB, with about 0.26 MB of project files and a 36.1 MB Python process peak for the measured local workload. Measurement scope and limitations are recorded in VALIDATION.md. Total machine RAM and free disk could not be inspected through the restricted system interfaces; the supplied 16 GB RAM and approximately 10 GB free-storage constraints govern the design.

No persistent server architecture is introduced. Any later persistence, model runtime, statistical dependency, or execution sandbox requires a specific scientific need and an architectural decision record. See [ADR 0001](docs/adr/0001_local_scientific_core.md).
