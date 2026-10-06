# Validation

## Scope

Version 0.2.0.dev0 is an operational local research alpha. Validation covers software behavior, specified scientific consistency rules, a narrow numerical adapter, publication identities, and local interface operation. It does not establish biological control appropriateness, source entailment accuracy, hosted-model performance, or agent generalization.

Software and source-review fixtures are synthetic. Live publication checks and observed synthetic computations are separately labeled. No expert review or biological experiment was performed.

## Reproducible checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/export_schemas.py --check
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/run_demo.py
.\.venv\Scripts\python.exe -m controlomics benchmark --output local_projects/development_benchmark.json
.\.venv\Scripts\python.exe scripts/check_resources.py
```

Unit, integration, scientific invariant, privacy, and adversarial tests cover strict parsing, references, unknown states, exact approval, URL/body binding, private DNS rejection, credential exclusion, source review, context mismatch, malformed metadata, strict generation settings, numeric calculations, fixed-script integrity, result bindings, CLI use, and local Host/Origin/token checks.

## Observations, 2026-10-06

The final suite passed 74 tests with zero failures, errors, or skips on Windows, CPython 3.14.0, and Pydantic 2.12.4. The measured run took 4.683 seconds including discovery and runner setup. [The software record](docs/validation/software_checks.json) preserves those observations. Core schema exports matched definitions and `pip check` reported no broken requirements.

The editable install and standard wheel built without new runtime dependencies. The inspected wheel includes all three browser assets and version metadata. Fixed dispatched runners and their result verifier passed, and the verifier rejected a forged runner-hash binding. The two original hypothetical projects remain readable.

[The offline demo script](scripts/run_demo.py) executed positive and negative synthetic reference calculations for both transcriptomics and microscopy descriptions. The positive expected difference was 2 and the negative expected difference was 0, specified before execution. Four technical outcomes were PASS. These calculations test the mean-difference adapter, not either primary analysis or biological claim. Both final audits remain INSUFFICIENT_EVIDENCE.

Review identified two additional issues: numeric tail tolerance could change results at very small measurement scales, and invalid local projects could be parsed after an external request. The tail now uses relative tolerance with zero absolute tolerance; a regression checks p-value invariance at scales 1e-15, 1, and 1e15. Local projects are validated before sending, with a regression asserting no provider call on invalid input.

### Live publication identity

Explicitly selected public DOIs were resolved through Europe PMC and Crossref. Four checks succeeded for two unique publications:

| Public DOI | Publication | Providers |
| --- | --- | --- |
| 10.1186/s13059-014-0550-8 | DESeq2, Love and colleagues, 2014 | Europe PMC and Crossref |
| 10.1186/1471-2105-7-91 | Cross-validation bias, Varma and Simon, 2006 | Europe PMC and Crossref |

[The recorded metadata and network ledger](docs/validation/literature_identity_checks.json) preserve identities, aliases, timestamps, hashes, and transmission status. Title punctuation and spacing differences are retained as consolidation warnings. No abstracts or full texts are exported. Successful identity checks do not demonstrate statement entailment or biological applicability.

A repeat requires network access and explicit opt-in:

```powershell
.\.venv\Scripts\python.exe scripts/check_literature.py --run-public-checks --output local_projects/literature_checks.json
```

This script submits only its two fixed public identifiers and self-approves the previews after that explicit opt-in. It does not authorize private projects or arbitrary queries.

### Development benchmark and numerical observations

[The observed harness](docs/validation/development_benchmark.json) detected six of six predefined planted software findings across six manually specified method descriptions. This measures rule implementation rather than independent scientific precision, recall, domain generalization, or an agent.

The seeded experiment used 100 synthetic independent Gaussian trials with four units per group and exact enumeration of 70 group assignments. At alpha 0.05, null rejection occurred in 4/100 trials: rate 0.04, Wilson 95% interval approximately 0.016 to 0.098. An injected group shift of 3 produced rejection in 79/100: rate 0.79, interval approximately 0.700 to 0.858. The null and shifted cases share underlying draws within each trial.

These are narrow numerical observations, not a calibration guarantee, clinical performance estimate, biological evaluation, or model benchmark. The small exact tests have discrete rejection probabilities. Bootstrap checks cover known constant shifts and reproducibility; interval coverage was not evaluated.

### Interface and resources

The installed Chrome 154 headless browser rendered the hypothetical controls at exact 1440 x 1200 and 430 x 1100 viewports. Both layouts had two cards and no horizontal overflow. Screenshots were visually inspected: [desktop](docs/validation/ui_controls.png), [mobile](docs/validation/ui_mobile.png). Browser-driven synthetic positive and negative execution returned PASS, PASS, with LOCAL plans, an INSUFFICIENT_EVIDENCE audit, a report containing warnings and input hashes, zero external requests, and no recorded JavaScript exceptions. See [the interface record](docs/validation/ui_checks.json).

The optional [browser check script](scripts/check_ui.cjs) uses the machine's existing Node and an isolated headless Chrome with DevTools bound to 127.0.0.1:9227. Follow its setup instructions. These tools are development checks, not application dependencies. The computer-use connector could not initialize in this environment; existing headless Chrome and HTTP integration tests supplied the recorded checks.

The measured environment contains about 31.4 MB of files. Project files occupied approximately 0.62 MB at measurement. The parent Python process peaked at 43.9 MB while validating and reviewing two projects, executing fixed synthetic references, auditing, reporting, and exporting ten schemas. [The resource record](docs/validation/resources.json) defines exclusions. These are decimal units and one local observation. Browser and child-process peaks, total system RAM, and free disk were not measured. Task-owned Chrome profiles were removed.

## Initial milestone, 2026-10-05

Stage 0 and Stage 1 passed 37 tests in 0.378 seconds. The initial virtual environment occupied approximately 31.3 MB, project files 0.26 MB, and a two-validation/ten-schema workload peaked at 36.1 MB. No retrieval, numerical execution, model, benchmark, or human evaluation existed then. Those figures remain historical rather than describing the current workflow.

## Independent research evaluation pending

ControlomicsBench still requires independently sourced cases, expert control annotations, adjudication, negative examples, source and domain partitions, and potential training-contamination assessment. A model must not supply its own sole reference answers.

Predefine critical-control recall, precision, unsupported recommendations, citation identity, statement entailment, context compatibility, flaw detection, execution success, and uncertainty calibration with denominators and abstention handling. Compare method checklists, retrieval-only workflows, and configured model baselines. Ablations should isolate retrieval, representation, review, execution, and the complete workflow.

Sample sizes, independent experts, adjudication, comparisons, and confidence intervals must be designed before that evaluation. No hosted-model score, external review, biological validation, domain-general performance result, or manuscript Results claim exists.
