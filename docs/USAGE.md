# Using the research alpha

## Local interface

Run `Start_Controlomics.cmd` from the repository or use `.venv/Scripts/python.exe -m controlomics serve`. Open `http://127.0.0.1:8765`. The server binds only to this computer. Use the hypothetical transcriptomics or microscopy buttons to inspect an example, then create a control audit. A direct hypothetical demonstration is available at `http://127.0.0.1:8765/#demo=transcriptomics`.

Enter the research question, analysis description, methods, observed result, scientific claim, claim category, and computational support category. The category choices are researcher input, not automated causal inference. Biological context and independent sampling units improve interpretability. Raw primary-analysis datasets are not required.

The baseline specifies a positive known-signal reference and a negative signal-absent technical reference. Both remain methodological specifications with explicit assumptions and limitations. It abstains from naming experimentally validated biological entities. Their METHOD_BASED state is not empirical validation.

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

## Numeric execution

The Execution tab accepts reviewed controls and three fixed procedures: a prespecified reference calculation, a two-sided mean-difference permutation test, and a within-group percentile bootstrap interval. Inputs are small CSV files with `unit,label,value` columns, unique units, binary group labels, and at least two units per group. There is a 2 MiB and 2,000-row limit. Rows must represent independent units; unique names alone do not establish independence.

For a reference calculation, specify the expected group mean difference before execution. The difference is mean(label=1) minus mean(label=0). PASS or FAIL refers to this technical calculation only. A nonsignificant permutation p value is not proof of a valid biological negative. Bootstrap intervals require assumptions and may have poor small-sample coverage.

Run locally to use a fixed, hash-checked template in a temporary directory. Download an execution package to move computation to another environment. The package contains scripts, configuration, environment information, schemas, artifact hashes, and a planned project snapshot. Running it requires Python 3.11 or newer; schema verification requires the installed Controlomics package. It performs no external requests.

```powershell
.\.venv\Scripts\controlomics.exe analyze examples/transcriptomics.project.json --output local_projects/project.json
# Read the reviewed control ID from the output project.
.\.venv\Scripts\controlomics.exe package local_projects/project.json --control-id CONTROL_ID --config examples/reference_execution.json --directory local_projects/execution --output local_projects/planned.json
.\.venv\Scripts\python.exe local_projects/execution/run_control.py --input examples/positive_reference.csv --output local_projects/results.json
.\.venv\Scripts\python.exe local_projects/execution/verify_results.py local_projects/results.json
.\.venv\Scripts\controlomics.exe import-results local_projects/planned.json local_projects/results.json --output local_projects/completed.json
.\.venv\Scripts\controlomics.exe report local_projects/completed.json --output local_projects/report.html
```

Each control receives one execution plan per snapshot. Keep a separate original project for reruns. Paired, clustered, covariate-adjusted, GPU, and specialist primary-analysis workflows require other adapters or external execution.

## Optional hosted reasoning

The local baseline requires no key. Optional Messages-compatible HTTPS endpoints use a provider-independent protocol, including compatible institutional or hosted open-weight services. Model identity is configuration rather than a project dependency. No live hosted model was configured or evaluated during development.

Supply manually minimized public fields such as `question`, `analysis_summary`, `claim`, `method`, or `organism`. The interface displays the full request before approval. It never serializes the project into the model request. Credentials are entered separately, passed as authorization headers, and excluded from request previews, audit values, project files, and reports. Do not place credentials in endpoint URLs or context fields.

The CLI reads an optional credential from `CONTROLOMICS_MODEL_KEY` and accepts `--endpoint`, `--model`, and `--context` on `model-propose`. Preview and hash approval are required. Model output must conform to the proposal schema and cannot supply citation or verification fields. Hosted candidates remain AGENT_PROPOSED until a separate review. Policy separation and schema gates reduce consequences of malformed or injected output; they do not establish perfect model reliability.
