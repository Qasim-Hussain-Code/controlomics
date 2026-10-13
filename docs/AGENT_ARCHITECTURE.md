# Complete agent architecture

This describes the implemented local research alpha, version 0.6.11.dev0. Controlomics is a human-supervised scientific workflow with structured proposals, evidence review, restricted numerical tools, and conservative audits. Its default reasoning engine uses inspectable rules. An optional hosted language model can propose controls through the same record contracts. Prototype checks cover implemented contracts and synthetic workflows; they do not demonstrate empirical scientific appropriateness or cross-domain generalization.

## Overall flow

```mermaid
flowchart TD
    R[Researcher: question, analysis, claim and context] --> UI[Local browser or CLI]
    UI --> CORE[Validated project records and provenance]
    CORE --> THINK[Local design reasoner or reference baseline]
    THINK --> CAND[Unreviewed control candidates]
    CORE --> GATE[Minimized public fields and exact request approval]
    GATE --> LLM[Optional chat-completion JSON endpoint]
    LLM --> CAND
    GATE --> PUB[Europe PMC or Crossref]
    PUB --> EVID[Publication identity records]
    CAND --> REVIEW[Method review or human statement and context review]
    EVID --> REVIEW
    REVIEW --> SPEC[Reviewed control specifications]
    SPEC --> CHECK[Local input inspection and adapter compatibility]
    CHECK --> EXEC[Fixed local or dispatched execution package]
    EXEC --> RESULT[Validated control results]
    CORE --> AUDIT[Conservative claim audit]
    SPEC --> AUDIT
    RESULT --> AUDIT
    AUDIT --> OUT[Linked report and local review archive]
    CORE --> BENCH[Separate benchmark and supplied-annotation evaluation]
```

The diagram shows available operations, not an automatic sequence that sends requests. The researcher chooses actions. External steps require their own exact-payload authorization; local work can run entirely offline.

## Components and responsibilities

| Component | Implementation | Input and output |
| --- | --- | --- |
| Browser workspace | `web/index.html`, `web/style.css`, `web/app.js` | Six views for analysis, controls, evidence, execution, assessment, and evaluation. Holds the current project, drafts, session token, request previews, and annotation work in memory. Sends explicit operations to the local server. |
| CLI and application entry | `cli.py`, `__main__.py`, `__init__.py` | Scriptable counterparts to intake, reasoning, review, execution, reporting, evaluation, archives, and local serving. Identifies the software version. |
| Loopback API | `server.py` | Binds to 127.0.0.1, serves fixed assets, validates bounded JSON, dispatches actions, and returns validated records. Mutating requests require the local Host, Origin, and session token. |
| Scientific record model | `schemas.py` | Strict, frozen Pydantic records for analyses, claims, context, candidates, reviewed controls, evidence, plans, results, audits, privacy, and provenance. Checks supported states and cross-record relationships. |
| Project parser and persistence | `project.py` | Rejects duplicate JSON keys, nonfinite numbers, unsupported fields, and oversized inputs. Loads and exports explicit local project snapshots and ten core JSON Schemas. |
| Auxiliary format contracts | `formats.py` | Exports nineteen workflow schemas, including proposals, reviews, execution configuration, annotation records, archives, and input summaries. Python also enforces relationships that structural schemas do not express. |
| Workflow coordinator | `workflow.py` | Creates projects and claims, records proposals and edits, applies review gates, imports evidence/results, and runs the claim audit. Returns replacement validated snapshots with provenance events. |
| Description drafting and design diagnosis | `reasoning.py` | Extracts explicitly labeled or stated phrases for researcher confirmation. Detects provisional analytical cues and emits inspectable review questions. Missing design information remains missing. |
| Local proposal engines | `MethodBaseline` and `DesignReasoner` in `models.py` | The reference baseline supplies known-signal and absent-signal technical specifications. The default design reasoner adds applicable null, specificity, robustness, confounder, and falsification specifications from stated operation cues. |
| Optional language-model adapter | `ModelProvider`, `MessagesProvider`, `DraftControl`, `Proposal` in `models.py` | Accepts selected public question, analysis summary, claim, method, and organism fields. Sends a constrained chat-completion JSON request and validates JSON proposals. A proposal cannot supply verified evidence, citations, or runnable code. |
| Outbound privacy and transport | `privacy.py` | Screens and classifies selected fields, builds an exact request preview, checks its approval hash, restricts HTTPS/DNS/redirect behavior, bounds responses, separates credentials, and records request outcomes. |
| Literature identity layer | `evidence.py` | Europe PMC and Crossref search or identifier resolution. Preserves publication metadata, identifier aliases, response hashes, licensing notes, and identity receipts. Consolidates connected aliases while retaining warnings. |
| Local input inspection | `inputs.py` | Checks independent-group or complete-pair CSV structure, finite values, identifiers, dimensions, and original-byte SHA-256. Returns summaries without retained measurements or unit identifiers. Does not execute the control. |
| Execution planner and adapter gates | `execution.py` | Requires an eligible reviewed specification, assumptions, parameters, and applicability rationale where needed. Builds a fixed package with scripts, configuration, schema, hashes, project snapshot, and optional prespecified decision rule. |
| Numerical procedures | `statistics.py` | Independent-group mean differences, absolute-tail permutation tests, and percentile bootstrap; complete-pair mean differences, sign flips, and whole-pair bootstrap. Handles supported finite numeric scales and rejects unrepresentable effects. |
| Result verifier and importer | `execution.py` and packaged fixed scripts | Checks input/artifact integrity and result relationships to the planned control, execution identifier, rule, and runner hash. Imports results without treating a consistent record as authenticated external execution. |
| Scientific report | `reports.py` | Produces escaped standalone HTML with linked claims, specifications, evidence, results, rules, provenance, network ledger, and limitations. Labels interval coverage as requested coverage. Uses local styles and no scripts. |
| Review archive | `artifacts.py` | Packages project, generated report, minimized ledger, and optional evaluation/revision records with a hash manifest. Restores bounded archives in memory and rejects unsafe, duplicate, unsupported, or inconsistent members. |
| Benchmark and evaluation | `benchmark.py`, `evaluation.py` | Development findings, offline reasoner runs, partition/source checks, blank annotations, immutable prediction judgments, explicit metric denominators, uncertainty, abstention, and reviewer agreement. Unassessed judgments produce unavailable quality scores. |
| Scientific validation tools | `scripts/run_numerical_validation.py`, `scientific_reference.py`, `check_study_readiness.py` | Separately frozen synthetic experiments, optional SciPy comparisons, and local record-readiness checks. They provide evidence about calculations and record completeness, not independent expert truth. |
| Software verification and distribution | `tests/`, `scripts/export_schemas.py`, `check_package.py`, `check_ui.cjs`, lock files, `pyproject.toml` | Scientific consistency, privacy, adversarial, unit, CLI/HTTP, artifact, browser, schema, and wheel checks. These support software reliability within their stated scope. |

## The project is the agent's working memory

An `AnalysisContext` contains the scientific question, method description, observed result, biological context, and sampling/design assumptions. One analysis can have multiple `ScientificClaim` records. Every proposed control identifies the particular claim it challenges. Shared publication records do not erase that binding.

Control class and scientific level are separate. Classes are POSITIVE, NEGATIVE, NULL, SPECIFICITY, ROBUSTNESS, CONFOUNDER, and FALSIFICATION. Levels are TECHNICAL, STATISTICAL, BIOLOGICAL, and MECHANISTIC. A statistical null is not automatically an inactive biological entity.

The project stores candidates, reviewed controls, evidence, execution plans, results, audits, privacy policy, and timestamped provenance. Each action records relevant identifiers and, where applicable, versions, hashes, seeds, and limitations. IDs and hashes establish recorded relationships; they do not prove that a scientific statement is true.

The browser has no automatic persistent memory or project database. The CLI saves only when explicitly instructed. Researchers retain exports to continue work. Form signatures detect temporary edits; revision counters track whether a download was prepared. Neither feature proves that a downloaded file was actually saved.

The browser restores its earlier six-section vertical navigation layout and mobile drawer with a Cinnabar navigation surface, warm ivory labels, and burnt orange selected sections and actions. Slate scientific text and separately labeled blue, ochre, and burgundy scientific states remain. Analysis & claims contains the scientific overview, complete question and actual identifiers, and four record-count cards. The other sections open at their own heading and content. Scientific audit assesses project claims; Evaluation records supplied benchmark judgments and calculates their bundle metrics. A local conceptual illustration represents the review framework without depicting measurements. The responsive control collection uses two desktop columns and exposes named scientific fields. Search, class, claim, and recorded evidence-state filters combine with an explicit reset. Execution preserves entered procedure settings and an explicitly chosen control while the same project and eligibility remain valid; it never substitutes the next control after the earlier one acquires a plan. Availability guidance reflects record and input prerequisites, rather than assessing scientific validity. The mobile drawer closes before the destination is scrolled into view. Workbench destination focus is deferred until pending form protection ends. The outbound dialog names the exact-request review and initially focuses Cancel. A visible header export-state label remains available at narrow widths alongside the save-state live announcement; the local-memory boundary is unchanged. [The validation account](../VALIDATION.md) distinguishes current verification from earlier snapshot observations; none establishes independent usability or full accessibility.

## How reasoning works

The local description parser drafts fields from supplied text. Suggested claim categories still need confirmation; causal language does not establish causal support. The design rules inspect methods, analysis and claim assumptions, descriptions, and design fields for prediction, comparison, association, ranking, overlap/enrichment, similarity, dependent units, temporal structure, batch structure, and causal interpretation. Rank-test phrases are distinguished from entity ranking; genetically predicted quantities alone do not imply predictive-model evaluation.

These cues trigger questions about selection leakage, independent replication, exchangeability, background choice, confounding, matched reference selection, and alternative explanations. Recommendations retain their trigger, rationale, expected behavior, failure interpretation, method basis, priority, and uncertainty. The rules do not select empirically validated biological entities from text alone.

The optional model interface shares these constrained output records. Despite the `MessagesProvider` class name, its concrete contract is a chat-completion JSON object containing `model` and `messages`, with response text at `choices[0].message.content`. A provider or gateway must support that exact contract; the generic name does not establish native-provider compatibility. Its fixed request uses temperature zero, a token budget of 3,000, and no streaming; these settings do not establish determinism or correct reasoning. Model health is recorded as configured and untested. A completed live model benchmark has not been performed. The implementation does not contain an autonomous tool-selection/replanning loop, multiple collaborating agents, a vector database, or a trained local model.

The reference reasoner changes proposal generation and the finding codes emitted by dataset runs. Project audits keep the full conservative design diagnostics whichever proposal reasoner was selected. This preserves warnings while allowing a separately labeled development ablation of proposals and dataset findings.

## Evidence gates and scientific states

Publication identity, statement entailment, and context applicability are separate decisions. Retrieval confirms recorded identifiers and metadata; it does not establish that a paper supports a control.

Human review addresses the candidate's exact rationale and expected behavior using local source text, excerpts, locators, relationship labels, and context. Software checks excerpt presence and record relationships. Human attestations supply the scientific support judgment. The implemented evidence gate requires support for both exact statements, a context MATCH, and no contradiction to record EVIDENCE_BACKED. Mixed support and contradiction can yield CONFLICTING_EVIDENCE. Incomplete support or context yields INSUFFICIENT_EVIDENCE.

Method review can record METHOD_BASED technical or statistical specifications without claiming empirical biological validation. Only newly created built-in local candidates receive automatic method review during their proposal action. Existing hosted or researcher-drafted candidates remain unreviewed when adding claims, repeating analysis, or opening projects; their method review is an explicit action. `VerifiedControl` means a review record exists, including unsuccessful reviews. Imported reviewed records must have a supported reviewed state, and EVIDENCE_BACKED requires the recorded human-kind statement support. Candidate edits cannot overwrite reviewed specifications; source re-review must identify the current reviewed snapshot. Reviewer identifiers and attestations do not authenticate identity, expertise, or independence.

## Execution and interpretation

The independent-group adapter accepts supported technical positive/negative references. The complete-pair adapter accepts its explicitly specified statistical null and an applicability rationale. General design questions, clustered or adjusted designs, and biological controls require suitable additional adapters.

Local execution first validates the selected bytes and checks a four-million numeric-unit-by-draw resampling budget, then runs the fixed hash-checked template in an owned temporary directory with explicit arguments and a 35-second timeout. Independent rows and complete pairs are the respective counted units. Budget and timeout failures explain how to reduce the workload or use a dispatched package; no result is imported. A dispatched package can retain larger valid configurations for execution in the researcher's environment and later result import. Model-generated prose never becomes executable code.

New packages hash the fixed runner, numerical module, and standard-library export helper together. The runner protects its input and known package files from output conflicts and stages complete result files. Package construction and review restoration prepare owned directories before rename to an absent destination. Existing empty directories are rejected. Ordinary preparation failure attempts cleanup; races, process crashes, power loss, and coordinated project/package writes remain outside that guarantee. The local HTTP boundary limits connection workers to 16 and applies a 10-second read-inactivity timeout, including headers. It rejects ambiguous headers and returns redacted unexpected-operation errors without logging internal details.

Technical PASS or FAIL requires an expected result and tolerance specified before execution. Permutation and bootstrap results remain INDETERMINATE for scientific pass/fail. Seeds, draw counts, input hashes, environment, method, effect, uncertainty, and warnings remain visible. Sampling independence, exchangeability, and sign invariance require scientific justification beyond file shape.

The current audit emits CONTROL_FAILURE if a relevant recorded technical control failed; otherwise it emits INSUFFICIENT_EVIDENCE. It also reports missing control classes, design concerns, causal overstatement, and context limitations. Evidence availability is determined from the assessed claim's linked control evidence; an unrelated publication elsewhere in the project does not fill that gap. The schema offers richer future assessment categories, but the implemented audit does not automatically certify a claim as ROBUST.

## Privacy, artifacts, and trust boundaries

Projects and raw primary data remain local. Selected external fields must be explicitly SAFE, pass screening, and match the approved whole-request hash before transmission. Literature destinations are fixed provider routes; a model endpoint must pass the configured transport boundary. Credentials travel separately and do not enter previews, project exports, or reports. The ledger distinguishes NOT_STARTED, ATTEMPTED, and COMPLETED.

The loopback server serves fixed assets, uses bounded requests, disables request logging/caching, and checks Host/Origin/token on mutations. Browser text nodes and report escaping reduce imported-content execution. Local OS software and browser extensions remain outside the application's trust boundary.

`storage.py` stages explicit local exports beside their destination, flushes complete bytes, retains supported access restrictions, and replaces one file. Ordinary failures preserve earlier exports. CLI sidecars cannot alias each other or their protected inputs. See [security limits](../SECURITY.md) for supported permissions, rejected destinations, races, and the absence of a multi-file transaction. No automatic persistence is introduced.

Pending browser operations make form inputs inert. A rejected stale session can be renewed without a reload, while interrupted responses are never automatically replayed. Evaluation reports identify the complete recorded source bundle by hash, and replacing a bundle or selecting another partition invalidates displayed metrics. Whole-project parsing enforces the same single-result and runner-hash bindings as individual-result import. These checks preserve record consistency rather than authenticating execution or judgment.

Review archives exclude raw CSVs, full supplied source texts, authorization credentials, and outbound bodies. They can still contain confidential descriptions, excerpts, selected public queries, or reviewer identifiers. ZIP bounds and hashes check consistency, not authentic scientific provenance or anonymization. Researcher IDs can be pseudonymous; any real-identity mapping belongs in separately protected private records when the scientific study requires it.

## Evaluation and current validation

Evaluation keeps reference annotations, predictions, recommendation judgments, and evidence decisions separate. Per-dimension assessed flags preserve the difference between skipped and explicitly uncertain judgments. Agreement excludes missing units. It checks declared partitions and source overlap, reports coverage, and computes conditional precision, critical/reference recall, unsupported rates, evidence-layer decisions, abstention, execution success, optional probability scores, and annotation agreement. Source semantics, contamination, and actual reviewer independence are properties of the supplied study records rather than authenticated software outputs.

The completed numerical phase matched 896 scalar comparisons across 128 synthetic cases against SciPy after explicit definition alignment. Seven scenarios used 7,000 total trials and revealed small-sample percentile undercoverage. See [numerical findings](NUMERICAL_VALIDATION.md). The existing six development cases remain unassessed. [The proposed study protocol](INDEPENDENT_VALIDATION_PROTOCOL.md) separately describes empirical control-selection research. It is outside technical prototype acceptance.

The application requires Python and Pydantic. The browser uses plain HTML, CSS, and JavaScript with local assets. Optional isolated NumPy/SciPy and existing Node/Chrome support development validation. Public hosting, remote multiuser operation, and hosted-model performance are not qualified by these local checks.
