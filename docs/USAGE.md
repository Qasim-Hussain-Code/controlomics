# Using the research alpha

## Local interface

Run `Start_Controlomics.cmd` from the repository or use `.venv/Scripts/python.exe -m controlomics serve`. Open `http://127.0.0.1:8765`. The server binds only to this computer. Use the hypothetical transcriptomics or microscopy buttons to inspect an example, then create a control audit. A direct hypothetical demonstration is available at `http://127.0.0.1:8765/#demo=transcriptomics`.

Choose a section in the left navigation or select a project summary card. The summaries count claims, all control specifications, publication records, and completed executions; they are not scientific performance scores. In Controls, search by name, rationale, expected behavior, identifier, or linked claim, and narrow the collection by control class, scientific claim, or recorded evidence state. Clear filters restores the complete collection. Filtering changes the display only. The evidence-state guide explains review limitations; the source-review prerequisite links to the evidence library when an identity-checked publication is missing. Result and audit panels show their scientific target. Open project JSON and review bundles through Open; Export offers project JSON and a scientific report. Save review bundle captures the current review records together.

Use Tab to reach the selected navigation section, arrow keys to change sections, and Home or End to select the first or last section. On a narrow screen, the menu button opens navigation; the close button, Escape, or the shaded backdrop closes it. Selecting a section returns focus to the workspace. Escape also closes file menus. Motion follows the system's reduced-motion preference. See [the interface guide](INTERFACE.md).

Enter the research question, analysis description, methods, observed result, scientific claim, claim category, and computational support category. The category choices are researcher input, not automated causal inference. Biological context and independent sampling units improve interpretability. Raw primary-analysis datasets are not required.

The local reasoner specifies positive known-signal and negative signal-absent technical references, then adds design-dependent challenges with inspectable cues. All remain provisional specifications with explicit assumptions and limitations. It abstains from naming experimentally validated biological entities. Their METHOD_BASED state is not empirical validation. Inspect Design interpretation in Audit and [DESIGN_RULES.md](DESIGN_RULES.md).

Use Draft fields from a local description to extract explicitly stated input, then confirm each field and choose the claim and support categories. Claims in this analysis adds a separately categorized claim and its own controls. Specify a control creates a researcher candidate; Edit specification revises an unreviewed candidate without promoting it. Reviewed specifications require a separate retained snapshot for content changes.

Inspect Controls and Scientific audit. Projects remain in browser memory. Save a review bundle or export the project, report, and network audit before closing the page. Opening a project performs structural checks and a new conservative audit. Receipts in imported files are not authenticated merely because parsing succeeds.

The workspace shows Export needed for recorded changes, Unrecorded inputs for edited form values, and Bundle prepared after preparing a complete review download. Reverting a form removes its draft indicator. Retain the actual downloaded file; preparation does not verify disk storage. Unrecorded edits, full source text, and raw CSV files are excluded from bundles. A browser close warning helps protect work but supplies no recovery mechanism.

Open > Start empty workspace clears the project and its inputs after confirmation. Opening another project, restoring a review bundle, or creating a replacement analysis also asks before discarding current work. Incoming records are validated first. Accepted replacement clears earlier review and judgment forms, evaluations, raw input selection, credentials, request previews, and ledger displays. Opening another candidate or source-review control asks before discarding that form's unrecorded edits. Applying an example or description draft also protects edited analysis fields. Judgment edits remain tracked across case switches; navigating cases alone does not change a judgment.

## Literature

In Evidence, enter a minimized public query and select Europe PMC or Crossref. Confirm that it contains public information, preview the exact request, and approve that request explicitly. The named preview dialog initially focuses Cancel; review its destination and public fields before choosing Send this exact request. The server receives no raw project data on behalf of a literature provider. The provider receives the selected public query and fixed API parameters. Credentials are not needed for these adapters.

Retrieved records provide publication identity and aliases. They do not prove that a publication supports a recommendation. The network ledger records destinations, public fields, payload hashes, credential presence, and transmission status. An attempted request can fail after some content was transmitted; failure does not imply that nothing left the device.

The equivalent CLI procedure first prints the exact payload and approval hash:

```powershell
.\.venv\Scripts\controlomics.exe retrieve local_projects/project.json --provider europepmc --query "public method query" --output local_projects/retrieved.json --audit-output local_projects/network_audit.json
```

After inspecting it, repeat the same command with `--approve-hash` and the displayed hash. Exit code 2 means a preview was shown and no request was sent. Use `--doi` or `--pmid` for exact identifier resolution; Crossref resolves DOI only. Limit searches to at most twenty records.

## Human statement review

See [EVIDENCE_REVIEW.md](EVIDENCE_REVIEW.md) for the review record. A researcher must inspect source text, exact statements, study context, and conflicting findings. The software verifies identifier references, excerpt presence in locally supplied text, context comparisons, and evidence-state prerequisites. Excerpt presence is not entailment. Imported reviewer names are attestations, not verified identities.

The evidence gate requires support for both the exact rationale and expected-behavior statement. A known mismatch, incomplete context, missing support, or contradiction prevents automatic evidence-backed acceptance. Exact context text comparisons are conservative and do not resolve biological synonyms. No expert review has been performed for the included development examples.

After retrieving a publication identity, choose Review evidence on a control. The form displays both exact statements and accepts separate source text, excerpt, locator, relationship, context, and explanation. A researcher must complete the attestation. Re-review displays an explicit replacement choice bound to the previous reviewed snapshot; preserve earlier exports first. JSON import remains available.

## Numeric execution

Select a compatible reviewed specification explicitly. The availability message explains missing review, unsupported mappings, existing execution plans, or a missing CSV and offers the relevant local next action. A valid selection is required to download a package; local execution also requires a selected CSV. Procedure settings and assumptions remain entered when selecting another control or refreshing the same project, so check their applicability before continuing. When the selected control receives a plan, the interface returns to the selection prompt instead of choosing another control. Retain a separate original snapshot for another run.

The Execution tab accepts reviewed technical positive and negative reference specifications and three fixed procedures: a prespecified reference calculation, a two-sided mean-difference permutation test, and a within-group percentile bootstrap interval. Other classes and scientific levels require an applicable adapter and are excluded from this runner. Inputs are small CSV files with `unit,label,value` columns, unique units without outer whitespace, binary group labels, and at least two units per group. UTF-8 with an optional byte-order mark is accepted. There is a 2 MiB and 2,000-row limit. Rows must represent independent units; unique names alone do not establish independence.

For a reference calculation, specify the expected group mean difference and absolute tolerance before execution. The difference is mean(label=1) minus mean(label=0). PASS or FAIL refers to this technical calculation only. Permutation and bootstrap procedures display seed and draw fields; bootstrap also displays the requested interval coverage. A nonsignificant permutation p value is not proof of a valid biological negative. Bootstrap intervals require assumptions and may have poor small-sample coverage.

Select a CSV and choose Inspect local CSV to check structure, finite values, dimensions, and limits before running. The summary records the original byte count and SHA-256, including any byte-order mark and line endings. It contains no identifiers or measurements, and performs no control execution or external request. Sampling assumptions still need justification. Changing the file or adapter clears the earlier summary. Export input summary downloads its JSON separately; it is not included in a review bundle.

The same inspection is available without a project:

```powershell
.\.venv\Scripts\controlomics.exe inspect-input examples/positive_reference.csv --adapter INDEPENDENT_REFERENCE --output local_projects/input_summary.json
.\.venv\Scripts\controlomics.exe inspect-input examples/paired_reference.csv --adapter PAIRED_DIFFERENCE --output local_projects/paired_summary.json
```

Browser imports reject invalid UTF-8. The local request limit includes JSON formatting and the project snapshot, so a file near the size limit may require CLI use. Summary hashes are neither anonymization nor authenticated provenance.

Run locally to use a fixed, hash-checked template in a temporary directory. Download an execution package to move computation to another environment. The package contains scripts, configuration, environment information, schemas, artifact hashes, and a planned project snapshot. Running it requires Python 3.11 or newer; schema verification requires the installed Controlomics package. It performs no external requests.

```powershell
.\.venv\Scripts\controlomics.exe new examples/hypothetical_intake.json --output local_projects/intake.project.json
.\.venv\Scripts\controlomics.exe analyze local_projects/intake.project.json --output local_projects/project.json
# Read the reviewed control ID from the output project.
.\.venv\Scripts\controlomics.exe package local_projects/project.json --control-id CONTROL_ID --config examples/reference_execution.json --directory local_projects/execution --output local_projects/planned.json
.\.venv\Scripts\python.exe local_projects/execution/run_control.py --input examples/positive_reference.csv --output local_projects/results.json
.\.venv\Scripts\python.exe local_projects/execution/verify_results.py local_projects/results.json
.\.venv\Scripts\controlomics.exe import-results local_projects/planned.json local_projects/results.json --output local_projects/completed.json
.\.venv\Scripts\controlomics.exe report local_projects/completed.json --output local_projects/report.html
```

Each control receives one execution plan per snapshot. Keep a separate original project for reruns. Clustered, temporal, covariate-adjusted, GPU, and specialist primary-analysis workflows require other adapters or external execution.

The package destination must not already exist, even as an empty directory. Construction prepares all files in an owned staging directory before exposing it. Result outputs must differ from the input and package files; the fixed runner rejects path aliases and hard links. Result writes preserve an earlier file during ordinary export failure. Interrupted CLI or runner operations return 130; inspect requested outputs before retrying. A package and separately saved project are not one transaction.

The original project examples contain hypothetical statistical specifications that remain readable but are not mapped to this runner. The explicit intake example above creates supported technical references. Preserve the distinction between a count-model or predictive-pipeline challenge and a generic mean-difference reference.

## Optional hosted reasoning

The local baseline requires no key. Optional Messages-compatible HTTPS endpoints use a provider-independent protocol, including compatible institutional or hosted open-weight services. Model identity is configuration rather than a project dependency. No live hosted model was configured or evaluated during development.

Supply manually minimized public fields such as `question`, `analysis_summary`, `claim`, `method`, or `organism`. The interface displays the full request before approval. It never serializes the project into the model request. Credentials are entered separately, passed as authorization headers, and excluded from request previews, audit values, project files, and reports. Do not place credentials in endpoint URLs or context fields.

The CLI reads an optional credential from `CONTROLOMICS_MODEL_KEY` and accepts `--endpoint`, `--model`, and `--context` on `model-propose`. Preview and hash approval are required. Model output must conform to the proposal schema and cannot supply citation or verification fields. Hosted candidates remain AGENT_PROPOSED until a separate review. Policy separation and schema gates reduce consequences of malformed or injected output; they do not establish perfect model reliability.

For multiple claims, choose the target in the interface or pass `--claim-id` in the CLI. Model public context remains a manually selected description; selecting a claim does not authorize its automatic upload.

## Evaluation and auxiliary commands

The Evaluation tab calculates a locally supplied evaluation bundle, showing origins, coverage, denominators, unavailable values, and limitations. Start with `examples/benchmark.design.unassessed.json` to inspect an unassessed development run. See [EVALUATION.md](EVALUATION.md) for annotation, partitioning, agreement, and the offline comparison protocol.

```powershell
.\.venv\Scripts\controlomics.exe interpret local_projects/description.txt --output local_projects/draft.json
.\.venv\Scripts\controlomics.exe design local_projects/project.json --output local_projects/design.json
.\.venv\Scripts\controlomics.exe add-claim local_projects/project.json local_projects/claim.json --output local_projects/multiple_claims.json
.\.venv\Scripts\controlomics.exe specify-control local_projects/project.json local_projects/candidate.json --output local_projects/candidates.json
.\.venv\Scripts\controlomics.exe analyze examples/transcriptomics.project.json --reasoner reference --output local_projects/reference.json
```

Claim submissions contain statement, category, computational_support, and optional assumptions. Candidate submissions contain claim_id, a DraftControl, and control_id only when editing an existing unreviewed candidate. The workflow JSON schemas define exact required fields. Untrusted JSON uses bounded duplicate-key-aware parsing; an imported record is not authenticated merely because it parses.

The CLI description limit is 12,000 UTF-8 bytes and rejects larger files without truncation. The browser limits description text to 12,000 characters inside the normal local request budget. CLI model-context and network-ledger files use bounded 2 MiB JSON reads.

## Complete-pair execution

In Execution, expand Specify a complete-pair statistical control. Choose its claim and provide the applicability rationale and assumptions. Select the Complete-pair mean difference adapter, choose permutation or bootstrap, and provide a separate adapter rationale. The method review checks the specification; it does not establish assumptions.

Inputs have `pair,condition,value` columns, pair identifiers without outer whitespace, exactly one finite value for condition 0 and 1 in every pair, 2 to 1,000 complete pairs, and a 2 MiB limit. UTF-8 with an optional byte-order mark is accepted. No incomplete-pair deletion is performed. The effect is the mean of condition 1 minus condition 0 within pairs. Under an independently justified sign-invariant null, sign flips preserve each pair. Bootstrap resampling preserves complete pairs. Neither procedure produces an automatic scientific PASS or FAIL. `examples/paired_reference.csv` and `examples/paired_execution.json` are hypothetical software examples.

The CLI `specify-paired PROJECT SUBMISSION --output OUTPUT` accepts a JSON submission with `claim_id`, `rationale`, and nonempty `assumptions`. It creates the explicit paired specification. Then use its control ID with `execute` or `package` and the paired execution configuration. The independent-reference adapter does not accept that control; the paired adapter does not accept unrelated reviewed statistical challenges.

## Judgment workbench and review archives

Choose an evaluation file and Open judgment workbench in Evaluation. Inspect case descriptions, reference definitions, recommendations, and any imported evidence predictions. Unknown is the default. Select appropriate and unsupported judgments independently, explain them, and match reference controls only when appropriate. Case switching retains draft edits. Recording judgments requires the actual reviewer's name, declared origin, and explicit attestation. The recorded snapshot preserves dataset references and predictions. Calculate metrics again after editing. Development fixture labels are not independent expert validation.

Export annotated bundle and Export annotation revisions retain the recorded snapshot and revision hash chain. Earlier snapshot content must be saved separately. CLI `annotate BUNDLE SUBMISSION --output OUTPUT --revision-output REVISION` applies the same binding and validation. AnnotationSubmission requires the exact canonical bundle hash; the `/api/annotation-template` local action returns it. Python `bundle_hash` provides the equivalent for scripts. Predictions and reference definitions cannot be changed through annotation submission.

Save review bundle captures the current project, regenerated report, network ledger, and any loaded recorded evaluation. Open review bundle restores validated local records. See [review bundle format and limits](REVIEW_BUNDLES.md). Save before closing the workspace.
