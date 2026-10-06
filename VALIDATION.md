# Validation

## Scope

Version 0.3.0.dev0 is an operational local research alpha. Validation covers software behavior, specified scientific consistency rules, a narrow numerical adapter, publication identities, design interpretation, supplied-annotation arithmetic, and local interface operation. It does not establish biological control appropriateness, source entailment accuracy, hosted-model performance, or agent generalization.

Software and source-review fixtures are synthetic. Live publication checks and observed synthetic computations are separately labeled. No expert review or biological experiment was performed.

## Reproducible checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
.\.venv\Scripts\python.exe scripts/export_schemas.py --check
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/run_demo.py
.\.venv\Scripts\python.exe -m controlomics benchmark --output local_projects/development_benchmark.json
.\.venv\Scripts\python.exe scripts/check_resources.py
.\.venv\Scripts\python.exe scripts/generate_benchmark_dataset.py
.\.venv\Scripts\controlomics.exe evaluate examples/benchmark.design.unassessed.json --output local_projects/evaluation.json
.\.venv\Scripts\python.exe -m pip wheel . --no-deps --no-build-isolation --no-index --wheel-dir dist
.\.venv\Scripts\python.exe scripts/check_package.py dist/controlomics-0.3.0.dev0-py3-none-any.whl --output local_projects/package_checks.json
```

Unit, integration, scientific invariant, privacy, and adversarial tests cover strict parsing, references, unknown states, exact approval, URL/body binding, private DNS rejection, credential exclusion, source review, context mismatch, malformed metadata, strict generation settings, numeric calculations, fixed-script integrity, result bindings, CLI use, and local Host/Origin/token checks.

## Observations, 2026-10-06

The final suite passed 99 tests with zero failures, errors, or skips on Windows, CPython 3.14.0, and Pydantic 2.12.4. The measured run took 5.71 seconds including discovery and runner setup. [The software record](docs/validation/software_checks.json) preserves those observations. Ten core and thirteen workflow schema exports matched definitions and `pip check` reported no broken requirements.

The editable install and standard wheel built without new runtime dependencies. The inspected wheel includes all three browser assets and version metadata. An extracted-wheel smoke check imported its own package, processed a local description draft, loaded evaluation contracts, and checked browser assets. [The package record](docs/validation/package_checks.json) retains the wheel hash and observed metadata. Fixed dispatched runners and their result verifier passed, and the verifier rejected a forged runner-hash binding. The two original hypothetical projects remain readable.

[The offline demo script](scripts/run_demo.py) executed positive and negative synthetic reference calculations for both transcriptomics and microscopy descriptions. The positive expected difference was 2 and the negative expected difference was 0, specified before execution. Four technical outcomes were PASS. These calculations test the mean-difference adapter, not either primary analysis or biological claim. Both final audits remain INSUFFICIENT_EVIDENCE.

The preceding milestone corrected numeric tail tolerance at very small measurement scales and validated local projects before external sending. Those regressions remain passing. Current checks additionally cover source re-review approval and conflicting evidence, earlier identity timing after repeat retrieval, candidate edits without state promotion, multi-claim target validation before hosted completion, duplicate-key rejection in browser imports, maximum-length evaluation case IDs, partition isolation, abstention, missing judgments, known denominator arithmetic, and degenerate annotation agreement.

Final review identified a mapping error: the generic numeric adapter could attach a mean-difference procedure to a method-reviewed design-control specification. The adapter now accepts only supported technical positive and negative references, rejects other levels and classes before package creation, and exposes only eligible references in the interface. Regression checks verify rejection and no package directory creation. An additional regression rejects oversized Unicode description files instead of accepting a truncated draft.

### Live publication identity

Explicitly selected public DOIs were resolved through Europe PMC and Crossref. Eight current checks succeeded for four unique publications:

| Public DOI | Publication | Providers |
| --- | --- | --- |
| 10.1186/s13059-014-0550-8 | DESeq2, Love and colleagues, 2014 | Europe PMC and Crossref |
| 10.1186/1471-2105-7-91 | Cross-validation bias, Varma and Simon, 2006 | Europe PMC and Crossref |
| 10.1038/s41467-021-21038-1 | Pseudoreplication in single-cell studies, Zimmerman and colleagues, 2021 | Europe PMC and Crossref |
| 10.1073/pnas.0506580102 | Gene set enrichment analysis, Subramanian and colleagues, 2005 | Europe PMC and Crossref |

[The current metadata and network ledger](docs/validation/literature_identity_checks_v0.3.json) preserve identities, aliases, timestamps, hashes, and transmission status. Title punctuation and spacing differences are retained as consolidation warnings. No abstracts or full texts are exported. Successful identity checks do not demonstrate statement entailment or biological applicability. The initial four-check record remains [separately preserved](docs/validation/literature_identity_checks.json).

The restricted execution attempt failed before payload transmission on all eight checks; its [NOT_STARTED records](docs/validation/literature_identity_checks_restricted_v0.3.json) are retained separately. The permitted public-only retry produced the eight successes. This distinguishes environment access failure from publication identity outcomes.

A repeat requires network access and explicit opt-in:

```powershell
.\.venv\Scripts\python.exe scripts/check_literature.py --run-public-checks --output local_projects/literature_checks.json
```

This script submits only its four fixed public identifiers and self-approves the previews after that explicit opt-in. It does not authorize private projects or arbitrary queries.

### Development benchmark and numerical observations

[The observed harness](docs/validation/development_benchmark.json) detected six of six predefined planted software findings across six manually specified method descriptions. This measures rule implementation rather than independent scientific precision, recall, domain generalization, or an agent.

[The current reference/design comparison](docs/validation/design_development_evaluation.json) uses six explicit development scenarios, with no held-out partition. Design rules reported 12 question codes, matching 10/10 expected codes; the reference ablation matched 2/10, reporting two codes. Two additional design questions were outside the supplied expected lists. The code-match precision is 10/12 for design and 2/2 for reference. These are development-label comparisons, not diagnoses or expert scientific precision. The 22 design recommendations and 12 reference recommendations have no assessed appropriateness judgments, so recommendation precision, control recall, unsupported rates, and evidence-layer accuracy remain unavailable. See [the evaluation protocol](docs/EVALUATION.md).

The seeded experiment used 100 synthetic independent Gaussian trials with four units per group and exact enumeration of 70 group assignments. At alpha 0.05, null rejection occurred in 4/100 trials: rate 0.04, Wilson 95% interval approximately 0.016 to 0.098. An injected group shift of 3 produced rejection in 79/100: rate 0.79, interval approximately 0.700 to 0.858. The null and shifted cases share underlying draws within each trial.

These are narrow numerical observations, not a calibration guarantee, clinical performance estimate, biological evaluation, or model benchmark. The small exact tests have discrete rejection probabilities. Bootstrap checks cover known constant shifts and reproducibility; interval coverage was not evaluated.

### Interface and resources

The installed Chrome 154 headless browser rendered the hypothetical controls at exact 1440 x 1200 and 430 x 1100 viewports. Both layouts had three cards and no horizontal overflow. Screenshots were visually inspected: [desktop](docs/validation/ui_controls.png), [mobile](docs/validation/ui_mobile.png), [evaluation](docs/validation/ui_evaluation.png), [mobile evaluation](docs/validation/ui_evaluation_mobile.png), and [stacked mobile metrics](docs/validation/ui_evaluation_metrics_mobile.png). Browser-driven synthetic positive and negative execution returned PASS, PASS, with LOCAL plans, an INSUFFICIENT_EVIDENCE audit, a report containing warnings and input hashes, zero external requests, and no recorded JavaScript exceptions. The browser also confirmed description drafts with unselected categories, two separately bound claims, unverified candidate edits, duplicate JSON rejection, unavailable quality scores, and a review form with empty researcher name and unchecked attestation. No human review was submitted. See [the interface record](docs/validation/ui_checks.json).

The optional [browser check script](scripts/check_ui.cjs) uses the machine's existing Node and an isolated headless Chrome with DevTools bound to 127.0.0.1:9227. Follow its setup instructions. These tools are development checks, not application dependencies. The computer-use connector could not initialize in this environment; existing headless Chrome and HTTP integration tests supplied the recorded checks.

The measured environment contains about 31.4 MB of files. Project files occupy approximately 1.2 MB. The parent Python process peaked at approximately 45 MB while validating and reviewing two projects, executing fixed synthetic references, auditing, reporting, exporting 23 schemas, and evaluating the six-case unassessed bundle. [The resource record](docs/validation/resources.json) defines exclusions. These are decimal units and one local observation. Browser and child-process peaks, total system RAM, and free disk were not measured. Task-owned Chrome profiles were removed.

Version 0.2.0.dev0 passed 74 tests in 4.683 seconds and measured 43.9 MB parent peak memory for its narrower workload. Its [software](docs/validation/software_checks_v0.2.json), [resource](docs/validation/resources_v0.2.json), and [browser](docs/validation/ui_checks_v0.2.json) records are retained as historical observations.

## Initial milestone, 2026-10-05

Stage 0 and Stage 1 passed 37 tests in 0.378 seconds. The initial virtual environment occupied approximately 31.3 MB, project files 0.26 MB, and a two-validation/ten-schema workload peaked at 36.1 MB. No retrieval, numerical execution, model, benchmark, or human evaluation existed then. Those figures remain historical rather than describing the current workflow.

## Independent research evaluation pending

ControlomicsBench still requires independently sourced cases, expert control annotations, adjudication, negative examples, source and domain partitions, and potential training-contamination assessment. A model must not supply its own sole reference answers.

The implemented metric tools expose critical-control recall, precision, unsupported recommendations, citation identity, statement entailment, context compatibility, finding-code detection, execution success, optional probability scores, and abstention with explicit denominators. Independent evaluation still requires predefined outcomes, coverage requirements, sampling, uncertainty analysis, and real annotations. Compare method checklists, retrieval-only workflows, and configured model baselines. Scientific ablations should isolate retrieval, representation, review, execution, and the complete workflow.

Sample sizes, independent experts, adjudication, comparisons, and confidence intervals must be designed before that evaluation. No hosted-model score, external review, biological validation, domain-general performance result, or manuscript Results claim exists.
