# Roadmap

| Stage | Deliverable | Current state |
| --- | --- | --- |
| 0 | Scientific specification, architecture, privacy and validation plans | Initial documents implemented |
| 1 | Typed records, claim representation, ontology and local validation | Initial implementation; checks recorded in VALIDATION.md |
| 2 | Modular evidence retrieval, identifier resolution, verification receipts | Planned |
| 3 | Provider-independent structured candidate reasoning | Planned |
| 4 | Evidence-reviewed positive and negative control specifications | Planned |
| 5 | Reproducible local and dispatched execution packages | Planned |
| 6 | Provenance ledger and human-readable scientific reporting | Planned |
| 7 | ControlomicsBench design and independently grounded cases | Planned |
| 8 | Predefined cross-domain evaluation and ablations | Planned |
| 9 | Privacy-hardened web application | Planned; requires a demonstrated core |
| 10 | Reviewed open-source public release | Planned; license selection required |

## First vertical slice

Start with the two development contexts represented by the schema examples: a transcriptomic comparison and a microscopy classification analysis. They are fixtures rather than the boundaries of the framework. Record a researcher-confirmed claim, then obtain typed positive and negative candidates through a provider-independent interface. Retain a manual candidate baseline so retrieval and evidence review can be evaluated independently of model reasoning.

Add a literature-provider protocol and one official API adapter, followed by a second adapter or independent identifier resolver to avoid a permanent single-provider dependency. Only a reviewed, minimized query may leave the machine. Preserve retrieved identifiers, timestamps, permitted content hashes, source context, and source licensing. Verify identity separately from statement support. Handle missing full text, ambiguity, conflict, and failed retrieval explicitly.

A deterministic gate should reject unsupported promotion and flag context mismatches. A human-reviewed entailment path should be available initially; model entailment may later assist and must itself be evaluated. The result should contain at least one reviewed positive candidate and one reviewed negative candidate, or explicit abstentions with reasons. Generate a local report exposing evidence, expected behavior, failure meaning, uncertainty, and provenance without executing primary analyses.

Acceptance requires traceable evidence, failure cases for nonexistent or irrelevant citations, context mismatch cases, privacy tests on exact outbound payloads, offline reproducibility, and successful representation of both contexts. Representation across two examples does not demonstrate scientific generalization. Execution, benchmark experiments, and frontend expansion remain separate milestones.
