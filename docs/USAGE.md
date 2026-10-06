# Using the research alpha

## Local interface

Run `Start_Controlomics.cmd` from the repository or use `.venv/Scripts/python.exe -m controlomics serve`. Open `http://127.0.0.1:8765`. The server binds only to this computer. Use the hypothetical transcriptomics or microscopy buttons to inspect an example, then create a control audit. A direct hypothetical demonstration is available at `http://127.0.0.1:8765/#demo=transcriptomics`.

Enter the research question, analysis description, methods, observed result, scientific claim, claim category, and computational support category. The category choices are researcher input, not automated causal inference. Biological context and independent sampling units improve interpretability. Raw primary-analysis datasets are not required.

The local reasoner specifies positive known-signal and negative signal-absent technical references, then adds design-dependent challenges with inspectable cues. All remain provisional specifications with explicit assumptions and limitations. It abstains from naming experimentally validated biological entities. Their METHOD_BASED state is not empirical validation. Inspect Design interpretation in Audit and [DESIGN_RULES.md](DESIGN_RULES.md).

Use Draft fields from a local description to extract explicitly stated input, then confirm each field and choose the claim and support categories. Claims in this analysis adds a separately categorized claim and its own controls. Specify a control creates a researcher candidate; Edit specification revises an unreviewed candidate without promoting it. Reviewed specifications require a separate retained snapshot for content changes.

Inspect the Controls and Audit tabs. Projects remain in browser memory. Export a project, report, and network audit before closing the page. Opening a project performs structural checks and a new conservative audit. Receipts in imported files are not authenticated merely because parsing succeeds.

## Literature

In Evidence, enter a minimized public query and select Europe PMC or Crossref. Confirm that it contains public information, preview the exact request, and approve that request explicitly. The server receives no raw project data on behalf of a literature provider. The provider receives the selected public query and fixed API parameters. Credentials are not needed for these adapters.

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

The Execution tab accepts reviewed technical positive and negative reference specifications and three fixed procedures: a prespecified reference calculation, a two-sided mean-difference permutation test, and a within-group percentile bootstrap interval. Other classes and scientific levels require an applicable adapter and are excluded from this runner. Inputs are small CSV files with `unit,label,value` columns, unique units, binary group labels, and at least two units per group. There is a 2 MiB and 2,000-row limit. Rows must represent independent units; unique names alone do not establish independence.

For a reference calculation, specify the expected group mean difference before execution. The difference is mean(label=1) minus mean(label=0). PASS or FAIL refers to this technical calculation only. A nonsignificant permutation p value is not proof of a valid biological negative. Bootstrap intervals require assumptions and may have poor small-sample coverage.

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

Each control receives one execution plan per snapshot. Keep a separate original project for reruns. Paired, clustered, covariate-adjusted, GPU, and specialist primary-analysis workflows require other adapters or external execution.

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
