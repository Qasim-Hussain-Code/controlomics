# Architecture

[The complete agent walkthrough](docs/AGENT_ARCHITECTURE.md) explains each implemented component, its inputs and outputs, the workflow diagram, scientific state gates, memory, privacy boundaries, and validation limits.

## Local scientific pipeline

One lightweight Python package represents a scientific claim attached to an analysis and biological context. Methods are descriptive fields rather than fixed domain dispatch. Researchers supply claimed category and computational support; software flags overstatement without inferring causality.

| Module | Responsibility |
| --- | --- |
| `schemas.py`, `project.py` | Strict immutable records, bounded JSON, relational checks, ten core schema exports |
| `storage.py` | Complete staged exports, replacement after flush, and conflicting-output checks |
| `workflow.py` | Claim intake, transitions, human review, context comparison, conservative audit |
| `models.py`, `reasoning.py` | Inspectable operation rules, literal description draft, reference baseline, and interchangeable proposals |
| `evaluation.py`, `formats.py` | Supplied annotations, partition checks, denominator-aware metrics, agreement, and workflow schemas |
| `privacy.py` | Explicit public fields, exact approval, HTTPS transport, network ledger |
| `evidence.py` | Europe PMC and Crossref metadata, resolution, connected alias consolidation |
| `statistics.py`, `execution.py` | Fixed numeric procedures, packages, local execution, result import |
| `inputs.py` | Local CSV structure, dimensions, original-byte hashes; no retained measurements or execution |
| `reports.py` | Escaped self-contained HTML, linked scientific records, typed ledger, print styles |
| `artifacts.py` | Bounded review archives, typed ledger, integrity checks, safe in-memory restore |
| `server.py`, `web/` | Loopback interface, session authorization, browser-memory projects |
| `benchmark.py` | Labeled development cases and synthetic permutation checks |

The workflow is intake, proposal, separate identity and statement review, context assessment, reviewed specification, execution, import, and audit. Each stage can retain uncertainty. Providers never receive entire projects implicitly. Parsing never executes imported text or code.

Claims share an analysis but retain individual proposals and audits. Hosted completion targets one known claim. Candidate edits retain an earlier snapshot hash and cannot overwrite reviewed specifications. Source re-review requires the current reviewed snapshot hash. A repeat retrieval retains the earlier verified identity snapshot that existing statement reviews depend on; later response hashes remain in the separate network ledger. Nineteen auxiliary workflow schemas cover intake, review, proposals, reasoning, execution configuration, evaluation, annotation revisions, review manifests, and numeric input summaries.

## Evidence and execution

Reviewed controls retain METHOD_BASED, EVIDENCE_BACKED, INSUFFICIENT_EVIDENCE, or CONFLICTING_EVIDENCE. `VerifiedControl` means a completed review record, including unsuccessful reviews. Identity does not imply entailment. Human review checks excerpt presence and records entailment attestations and source hashes without retaining full supplied text. Names and receipts are not authenticated.

The human workflow requires support for both exact statements, matching supplied context, and no contradiction. Missing values stay unknown; normalized text comparison does not resolve synonyms. The core representation also allows explicitly justified partial context, which this workflow does not automatically promote. Method review concerns technical or statistical specifications with a method basis, not biological empirical validation. Audits never automatically declare a claim ROBUST.

Outbound objects bind selected SAFE fields to fixed literature URLs or a structured model body. Complete-request hashes govern approval. HTTPS connects to checked public addresses with hostname validation, no redirects, and bounded responses. Private institutional addresses need a separately assessed transport.

Execution packages record plans, configuration, seeds, environment, artifact hashes, fixed scripts, and result schemas. Local execution uses an owned temporary directory. The independent-group adapter supports technical positive and negative references. A separate adapter accepts only the explicit complete-pair statistical null specification and a supplied applicability rationale. Unsupported mappings are rejected before package creation; general generated code and specialist primary-analysis designs are outside its scope.

Package construction and review restoration use an owned staging directory beside an absent destination, then rename it after all preparation succeeds. Existing directories, including empty ones, are rejected. The fixed runner checks the copied export helper hash before import, rejects input/package output conflicts, and stages single-file results. Its recorded code hash includes the runner, unchanged numerical module, and export helper. These changes preserve the numeric procedure; historical runner hashes remain bound to their original plans.

## Resources and deployment

Pydantic is the sole runtime dependency, supplying [strict validation](https://docs.pydantic.dev/latest/concepts/strict_mode/) and [JSON Schema generation](https://docs.pydantic.dev/latest/concepts/json_schema/). Application modules and ordinary tests otherwise use the standard library. Optional numerical reference comparisons use pinned NumPy and SciPy in a separate ignored validation environment; they do not alter application dependencies. The browser uses plain HTML, CSS, and JavaScript.

The server binds to `127.0.0.1`, logs no requests, and stores no project database. It processes transient request snapshots; the browser retains work until export. Input and numerical budgets constrain ordinary operations. This is a local application rather than an internet-facing service.

At most 16 connection workers run concurrently; excess connections attempt a prompt 503 response without another worker. A brief bounded drain after response half-close reduces resets before the client receives it; rejected input bytes are discarded without parsing or storage. A client can still observe a connection interruption. A 10-second inactivity timeout applies during header and body reads, rather than a total request deadline. Slots are released when handlers finish. Host, Origin, token, Content-Length, and Content-Type must be unambiguous; transfer encoding is unsupported. Local actions require a JSON object. Unexpected operation failures omit internal details.

The interface uses one responsive navigation shell around the six existing workflow sections. Summary counts derive from the current validated project. Control search, class, claim, and evidence-state filters affect rendering only; an explicit reset clears them. Project text is inserted through text nodes. Icons and the conceptual review motif are local inline SVG; system fonts avoid font downloads. A mobile modal navigation boundary uses inert content, keyboard focus handling, and explicit selected-tab semantics. Workbench actions retain a destination focus until pending input protection ends. The outbound dialog has a name and description and initially focuses Cancel. Save-state announcements remain available at every responsive width. Design details and the limits of accessibility checks appear in [INTERFACE.md](docs/INTERFACE.md).

Execution rendering preserves an explicit eligible-control selection for the same project and retains entered procedure settings. New projects and changes that remove eligibility require a fresh selection. Local availability messages distinguish missing project, unsupported or unreviewed specifications, existing plans, and missing CSV input; they do not establish scientific applicability. The server continues to validate adapter compatibility and configuration independently of disabled interface buttons.

In-memory form signatures detect edits and reversions; record revisions track whether a complete bundle download was prepared. Passwords are excluded from signatures. No automatic persistence is introduced. Replacement validates the incoming records before asking to discard the current workspace, then resets prior forms, evidence reviews, evaluations, inputs, credentials, and previews. A prepared download is not proof that a file was retained on disk.

Forms and file selectors are inert during pending operations, so responses cannot silently consume later user edits. Interrupted responses retain the browser workspace and do not trigger an automatic retry. A stale session token can be renewed locally without reloading; the rejected operation remains unsubmitted until the researcher retries it. An interrupted approved external request may already have transmitted content and may lack a returned ledger.

Evaluation reports hash the complete recorded bundle, including supplied judgments. Loading another validated bundle or changing the selected partition clears the prior metric view and disables its export. CLI project, JSON, HTML, and review-archive exports stage a complete file beside the destination before replacement. This protects earlier files during ordinary write failures, but does not coordinate concurrent writers or make a multi-file transaction.

The application design respects the supplied 16 GB RAM and approximately 10 GB free-storage limits. No model weights, containers, large datasets, or GPU software were installed. The optional isolated NumPy/SciPy comparison environment uses about 200.7 MB of files and is separate from application dependencies. Measurements appear in [VALIDATION.md](VALIDATION.md). See [ADR 0001](docs/adr/0001_local_scientific_core.md), [ADR 0002](docs/adr/0002_retrieval_and_execution_boundaries.md), [ADR 0003](docs/adr/0003_design_reasoning_and_evaluation.md), [ADR 0004](docs/adr/0004_paired_and_review_artifacts.md), and [ADR 0005](docs/adr/0005_local_inspection_and_workspace.md).
