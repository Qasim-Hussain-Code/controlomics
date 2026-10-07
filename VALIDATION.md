# Validation

## Scope

Version 0.6.0.dev0 is an operational local research alpha with local input inspection, clearer scientific record bindings, and workspace continuity checks. Validation covers software behavior, specified scientific consistency rules, two explicitly mapped numerical adapters, publication identities, design interpretation, supplied-annotation arithmetic, and local interface operation. It does not establish biological control appropriateness, source entailment accuracy, hosted-model performance, or agent generalization.

Software and source-review fixtures are synthetic. Live publication checks, independent-software numerical comparisons, and observed synthetic computations are separately labeled. No expert review or biological experiment was performed.

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
.\.venv\Scripts\python.exe scripts/check_package.py dist/controlomics-0.6.0.dev0-py3-none-any.whl --output local_projects/package_checks.json
```

Unit, integration, scientific invariant, privacy, and adversarial tests cover strict parsing, references, unknown states, exact approval, URL/body binding, private DNS rejection, credential exclusion, source review, context mismatch, malformed metadata, strict generation settings, numeric calculations, fixed-script integrity, result bindings, CLI use, and local Host/Origin/token checks.

## Observations, 2026-10-06

The final suite passed 139 tests with zero failures, errors, or skips on Windows, CPython 3.14.0, and Pydantic 2.12.4. The measured run took 5.953 seconds including discovery and runner setup. [The software record](docs/validation/software_checks.json) preserves those observations. Ten core and nineteen workflow schema exports matched definitions and `pip check` reported no broken requirements.

The editable install and standard wheel built without new runtime dependencies. The inspected wheel includes all three browser assets and version metadata. An extracted-wheel smoke check imported its own package, processed a local description draft, loaded evaluation contracts, checked browser assets, computed a paired exact p value, inspected a local CSV, and restored a review archive. [The package record](docs/validation/package_checks.json) retains the wheel hash and observed metadata. Fixed dispatched runners and their result verifier passed, and the verifier rejected a forged runner-hash binding. The two original hypothetical projects remain readable. New archive checks cover duplicate/traversal/symlink members, expansion bounds, modified hashes, raw-body/header rejection, immutable prediction judgments, revision binding, and CLI round trips.

[The offline demo script](scripts/run_demo.py) executed positive and negative synthetic reference calculations for both transcriptomics and microscopy descriptions. The positive expected difference was 2 and the negative expected difference was 0, specified before execution. Four technical outcomes were PASS. These calculations test the mean-difference adapter, not either primary analysis or biological claim. Both final audits remain INSUFFICIENT_EVIDENCE.

The paired demonstration has three complete synthetic pairs with differences 1, 2, and 3. Exact enumeration of eight sign assignments returned p = 0.25 and an INDETERMINATE outcome. Whole-pair bootstrap fixtures test constant differences and seed reproducibility; those initial fixtures did not evaluate population coverage. The subsequent 2026-10-07 synthetic study reports coverage separately. Zero-mean, clustered, temporal, and adjusted designs are not silently mapped to this adapter. See [the methods record](METHODS.md).

Current checks cover finite group means with overflowing totals, exact preservation of small cancellation residuals, scaled null variances at 1e-200 and 1e200 measurement scales, opposite-sign extreme quantile interpolation, subnormal paired effects, rejected unrepresentable effects, UTF-8 byte-order marks with original-byte hashes, and ambiguous sampling identifiers. CSV inspection was checked to omit measurements and identifiers and perform no execution or external request. Standalone reports reject raw-body and authorization-header ledger entries and link recorded results to specifications, claims, runner hashes, and prespecified rules. Local HTTP checks reject non-ASCII tokens and unauthorized requests before waiting for a declared body.

Earlier work corrected numeric tail tolerance at very small measurement scales and validated local projects before external sending. Those regressions remain passing. Checks also cover source re-review approval and conflicting evidence, earlier identity timing after repeat retrieval, candidate edits without state promotion, multi-claim target validation before hosted completion, duplicate-key rejection in browser imports, maximum-length evaluation case IDs, partition isolation, abstention, missing judgments, known denominator arithmetic, and degenerate annotation agreement.

Earlier checks identified a mapping error: the generic numeric adapter could attach a mean-difference procedure to a method-reviewed design-control specification. The independent-group adapter accepts only supported technical positive and negative references, rejects other levels and classes before package creation, and exposes only eligible references in the interface. Regression checks verify rejection and no package directory creation. An additional regression rejects oversized Unicode description files instead of accepting a truncated draft.

### Live publication identity

Explicitly selected public DOIs were resolved through Europe PMC and Crossref. Eight retained checks from the preceding milestone succeeded for four unique publications:

| Public DOI | Publication | Providers |
| --- | --- | --- |
| 10.1186/s13059-014-0550-8 | DESeq2, Love and colleagues, 2014 | Europe PMC and Crossref |
| 10.1186/1471-2105-7-91 | Cross-validation bias, Varma and Simon, 2006 | Europe PMC and Crossref |
| 10.1038/s41467-021-21038-1 | Pseudoreplication in single-cell studies, Zimmerman and colleagues, 2021 | Europe PMC and Crossref |
| 10.1073/pnas.0506580102 | Gene set enrichment analysis, Subramanian and colleagues, 2005 | Europe PMC and Crossref |

[The retained metadata and network ledger](docs/validation/literature_identity_checks_v0.3.json) preserve identities, aliases, timestamps, hashes, and transmission status. Title punctuation and spacing differences are retained as consolidation warnings. No abstracts or full texts are exported. Successful identity checks do not demonstrate statement entailment or biological applicability. The initial four-check record remains [separately preserved](docs/validation/literature_identity_checks.json).

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

These are narrow numerical observations, not a calibration guarantee, clinical performance estimate, biological evaluation, or model benchmark. The small exact tests have discrete rejection probabilities. The initial bootstrap checks covered known constant shifts and reproducibility; interval coverage was subsequently measured in the separately frozen 2026-10-07 study.

### Interface and resources

The installed Chrome 154 headless browser rendered the redesigned hypothetical controls at exact 1440 x 1200 and 430 x 1100 viewports. Both layouts had three cards and no horizontal overflow. All six sections also fit 375, 768, 1024, and 1440 pixel widths at a 900 pixel height. Browser checks confirmed zero counts in the empty workspace, summaries matching actual project records before and after execution, name search, combined claim/class filtering, empty search results, and unchanged project data after filtering. The multi-claim toolbar also fit 375, 430, 768, 1024, and 1440 pixel widths. Result and audit panels retained their full scientific targets. Arrow keys, Home, End, mobile focus confinement, Escape and close-button dismissal, section selection, file menus, reduced motion, and text-only rendering passed. Review and metric headings remained below the fixed header. These checks do not establish full accessibility conformance or screen-reader compatibility.

Screenshots were visually inspected: [empty workspace](docs/validation/ui_workspace.png), [analysis](docs/validation/ui_analysis.png), [desktop controls](docs/validation/ui_controls.png), [mobile controls](docs/validation/ui_mobile.png), [mobile navigation](docs/validation/ui_navigation_mobile.png), [evaluation](docs/validation/ui_evaluation.png), [mobile evaluation](docs/validation/ui_evaluation_mobile.png), [stacked mobile metrics](docs/validation/ui_evaluation_metrics_mobile.png), [judgment workbench](docs/validation/ui_annotations.png), [mobile judgments](docs/validation/ui_annotations_mobile.png), [claim filtering](docs/validation/ui_claims.png), [local input inspection](docs/validation/ui_input_inspection.png), [desktop report](docs/validation/ui_report.png), and [mobile report](docs/validation/ui_report_mobile.png). See [the interface design](docs/INTERFACE.md).

Browser-driven synthetic positive and negative execution returned PASS, PASS, with LOCAL plans, an INSUFFICIENT_EVIDENCE audit, a report containing warnings and input hashes, zero external requests, and no recorded JavaScript exceptions. The browser also confirmed description drafts with unselected categories, two separately bound claims, unverified candidate edits, duplicate JSON rejection, unavailable quality scores, and a review form with empty researcher name and unchecked attestation. The paired browser fixture returned p = 0.25 with an INDETERMINATE outcome and a paired input hash. An additional paired bootstrap used seed 17, 199 draws, and requested coverage 0.90; the recorded method, seed, and coverage matched the submitted inputs and its outcome remained INDETERMINATE. This checks parameter binding, not interval coverage. A review archive restored the project and unassessed evaluation unchanged. The judgment workbench retained blank reviewer and origin fields, unchecked attestation, Unknown labels, and disabled reference matches. No human source review or benchmark judgment was submitted. Browser checks also verified form-edit reversion, unrecorded candidate and source protection, judgment protection across case switching and reversion, programmatically filled analysis tracking, a prepared bundle revision, cancelled import preservation, coherent project replacement, and complete clearing of prior previews, credentials, and ledger display when starting an empty workspace. Exact-byte CSV inspection accepted a UTF-8 byte-order mark and rejected invalid UTF-8. Reports fit desktop and mobile widths with resolved internal links, no scripts, and active print styles. Print pagination was not qualified. See [the interface record](docs/validation/ui_checks.json).

The optional [browser check script](scripts/check_ui.cjs) uses the machine's existing Node and an isolated headless Chrome with DevTools bound to 127.0.0.1:9227. Follow its setup instructions. These tools are development checks, not application dependencies. The computer-use connector could not initialize in this environment; existing headless Chrome and HTTP integration tests supplied the recorded checks.

The measured environment contains about 31.4 MB of files. Project files occupy approximately 2.3 MB. The parent Python process peaked at approximately 46.4 MB while validating and reviewing two projects, executing fixed synthetic references, auditing, reporting, exporting 29 schemas, evaluating the six-case unassessed bundle, executing paired sign flips, restoring a review archive, and inspecting a paired input. [The resource record](docs/validation/resources.json) defines exclusions. These are decimal units and one local observation. Browser and child-process peaks, total system RAM, and free disk were not measured. Task-owned Chrome profiles were removed.

Version 0.5.0.dev0 passed 121 tests in 5.230 seconds for the initial visual redesign. Its [software](docs/validation/software_checks_v0.5.json), [resources](docs/validation/resources_v0.5.json), [browser](docs/validation/ui_checks_v0.5.json), and [package](docs/validation/package_checks_v0.5.json) observations are retained separately.

Version 0.4.0.dev0 passed 121 tests in 4.942 seconds before the visual redesign. Its [software](docs/validation/software_checks_v0.4.json), [resources](docs/validation/resources_v0.4.json), [browser](docs/validation/ui_checks_v0.4.json), and [package](docs/validation/package_checks_v0.4.json) observations are retained separately.

Version 0.3.0.dev0 passed 99 tests in 5.71 seconds with a narrower workload. Its [software](docs/validation/software_checks_v0.3.json), [resources](docs/validation/resources_v0.3.json), [browser](docs/validation/ui_checks_v0.3.json), and [package](docs/validation/package_checks_v0.3.json) records are retained. The live identity records retain their original version and timestamps; no new publication identity request was made in version 0.4, 0.5, or 0.6 verification. The 2026-10-07 numerical phase separately downloaded public method documentation and optional package wheels.

Version 0.2.0.dev0 passed 74 tests in 4.683 seconds and measured 43.9 MB parent peak memory for its narrower workload. Its [software](docs/validation/software_checks_v0.2.json), [resource](docs/validation/resources_v0.2.json), and [browser](docs/validation/ui_checks_v0.2.json) records are retained as historical observations.

## Initial milestone, 2026-10-05

Stage 0 and Stage 1 passed 37 tests in 0.378 seconds. The initial virtual environment occupied approximately 31.3 MB, project files 0.26 MB, and a two-validation/ten-schema workload peaked at 36.1 MB. No retrieval, numerical execution, model, benchmark, or human evaluation existed then. Those figures remain historical rather than describing the current workflow.

## Numerical validation phase, 2026-10-07

The expanded suite passed 146 tests with zero failures, errors, or skips in 27.79 seconds including discovery. New checks protect frozen numerical source bindings and local study-readiness/privacy behavior. [The scientific-phase software record](docs/validation/software_checks_scientific_phase.json) preserves this run separately from the earlier 139-test record. After the requested-coverage display correction, [the final suite](docs/validation/software_checks_scientific_phase_final.json) passed the same 146 tests in 8.408 seconds including discovery. All 29 schema exports still match. Both application and isolated reference environments passed `pip check`.

A protocol frozen before calculation compared 128 synthetic cases with NumPy 2.4.6 and SciPy 1.18.1 in an isolated optional environment. All 896 scalar comparisons matched at the predefined tolerances. Native SciPy two-sided probabilities differ in 36 cases because its convention differs from the declared absolute-tail procedure; aligned probabilities all match. Percentile bootstrap comparisons use the same explicit indices, so they assess calculation rather than RNG-stream equivalence. [The retained protocol](docs/validation/numerical_protocol.json) and [full numeric observations](docs/validation/numerical_checks.json) preserve these distinctions.

Seven prespecified scenarios used 1,000 trials each. Null rejection rates ranged from 0.0% to 5.5%, shifted rejection rates from 0.0% to 98.6%, and requested 95% percentile interval coverage from 74.1% to 93.9%. The three-pair exact procedure cannot reject at 0.05 because its minimum p is 0.25. The four-per-group exact procedure has theoretical null rejection probability 2/70 for continuous exchangeable inputs. A labeled post-hoc analytical count reproduced both observed four-per-group rejection counts, including the unusually low Laplace result, without using the permutation implementation. No seed or scenario was removed or retuned.

These measurements reveal small-sample interval undercoverage and discrete-test limits. They do not establish general calibration, real-data assumptions, biological appropriateness, or an independently conducted expert study. The findings, all scenario counts and uncertainty, environment size, and local repetition instructions are in [NUMERICAL_VALIDATION.md](docs/NUMERICAL_VALIDATION.md). Inferential outputs remain INDETERMINATE.

The interface and standalone report now label bootstrap coverage as requested coverage. A [targeted Chrome 154 check](docs/validation/coverage_labels_ui_checks.json) verified the actual synthetic bootstrap parameter, retained poor-coverage warning, INDETERMINATE outcome, and corrected form/result/report text. The execution view fit 375, 768, and 1440 pixel widths; the standalone report fit 375 and 1440. There were no recorded JavaScript exceptions or external page requests. This supplements the earlier interface checks without replacing their retained records.

The wheel was rebuilt offline after these documentation and display changes. [The scientific-phase package record](docs/validation/package_checks_scientific_phase.json) retains its SHA-256 and successful extracted-package smoke observations. The earlier wheel record remains a historical observation of the preceding interface phase.

## Privacy and architecture phase, 2026-10-07

Personal project attribution was removed from current source, package metadata, interface/report footers, citation material, and local demonstration reports. Historical package observations explicitly identify removal of the author field. The owner authorized local history sanitization separately; [the cleanup record](docs/validation/privacy_cleanup_checks.json) distinguishes current-file observations from the history-rewrite result. Published bibliographic attribution and dependency notices remain intact.

[The completed local-history check](docs/validation/git_history_cleanup_checks.json) preserves eight commits and the current tree while minimizing 31 historical text blobs and omitting obsolete citation/screenshot copies. All 423 remaining Git objects and non-object Git metadata files were checked for the former private identities with no matches. Old reflogs and objects were pruned. This changes historical commit IDs without changing the frozen numerical sources or their observations.

[The privacy-phase software suite](docs/validation/software_checks_privacy_phase.json) passed 146 tests with zero failures, errors, or skips in 8.751 seconds. All 29 schema exports match and `pip check` passed. [The rebuilt wheel](docs/validation/package_checks_privacy_phase.json) contains no personal attribution metadata and passed the extracted-package smoke checks. Older generated wheels containing that attribution were removed locally.

The complete Chrome 154 interface check passed again with no recorded JavaScript exceptions or external requests. [Current browser observations](docs/validation/ui_checks.json) label this as the privacy phase. All fourteen current screenshots were re-rendered from the attribution-free interface/report; identical captures remain byte-identical. [The preceding browser observations](docs/validation/ui_checks_v0.6_before_privacy.json) are preserved separately. The frozen numerical source files and their hashes are unchanged.

[The complete architecture walkthrough](docs/AGENT_ARCHITECTURE.md) now documents every implemented component, data flow, human/automatic decision boundary, local memory, optional model interface, privacy transport, fixed execution, provenance, artifacts, evaluation, and scientific limitations.

## Independent expert and biological evaluation pending

ControlomicsBench still requires independently sourced cases, expert control annotations, adjudication, negative examples, source and domain partitions, and potential training-contamination assessment. A model must not supply its own sole reference answers.

The implemented metric tools expose critical-control recall, precision, unsupported recommendations, citation identity, statement entailment, context compatibility, finding-code detection, execution success, optional probability scores, and abstention with explicit denominators. Independent evaluation still requires predefined outcomes, coverage requirements, sampling, uncertainty analysis, and real annotations. Compare method checklists, retrieval-only workflows, and configured model baselines. Scientific ablations should isolate retrieval, representation, review, execution, and the complete workflow.

The [proposed expert-study protocol](docs/INDEPENDENT_VALIDATION_PROTOCOL.md) now specifies the primary case outcome, a planning target, blinded independent review, frozen references/predictions, source independence, adjudication, uncertainty, and private local storage. Its planning target is not a completed power analysis or an adopted study design. [The local record-readiness observation](docs/validation/study_readiness.json) finds six DEVELOPMENT cases, no TEST cases, and no independent expert judgment sheets. Actual real cases, expertise/independence declarations, annotations, retained adjudication, and an adopted sampling/analysis plan are still required. No hosted-model score, external review, biological validation, domain-general performance result, or manuscript Results claim exists.
