# ADR 0001: A local scientific core

Status: accepted for Stage 0 and Stage 1.

Problem: Controlomics needs inspectable scientific records before retrieval, inference, execution, or a frontend can be evaluated. Development must fit approximately 16 GB RAM and 10 GB free disk.

Alternatives considered: multiple packages and services, a web-first application with persistent storage, standard-library dataclasses with custom validation and schema generation, and one typed Python package.

Decision: implement one local package using Pydantic and standard-library tests. Keep the ontology and JSON Schemas as versioned files. Use local project snapshots. Defer inference, scientific APIs, calculations, server storage, and user-interface expansion.

Scientific rationale: strict records preserve evidence, assumptions, context, and claim categories while preventing some invalid transitions. Biological validity still requires independent evidence and empirical evaluation.

Technical rationale: one runtime dependency supplies maintained validation and schema export. Avoid duplicating a validation framework or installing numerical stacks without a computation requirement. Use bounded, nonexecuting JSON input.

Privacy implications: the initial package has no outbound data pathway. Free text remains potentially sensitive, and local files require user-controlled storage and review.

Security implications: reject unknown fields and references, keep embedded instructions inert, and redact CLI failures. Caller-supplied verification receipts are unauthenticated. JSON Schema cannot encode every Python consistency rule.

Limitations: schema acceptance cannot establish source truth, reviewer authenticity, scientific appropriateness, causal validity, or benchmark performance. The examples are hypothetical. Package compatibility beyond the observed test environment remains unevaluated.

Conditions for reconsideration: a concrete retrieval integration, a validated execution adapter, collaboration needs requiring persistence, multi-provider interfaces, or demonstrated packaging limitations. Record the evidence and resource impact before expanding infrastructure.
