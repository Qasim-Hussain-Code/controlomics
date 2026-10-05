# Validation

## Scope

Stage 0 and Stage 1 tests concern software behavior and specified scientific consistency rules. They do not validate biological appropriateness, source truth, automated reasoning, numerical procedures, or cross-domain generalization. All test evidence receipts and execution outcomes are explicitly synthetic fixtures.

Four test categories are maintained:

- Software: strict parsing, serialization, versions, IDs, references, schema exports, and CLI operation.
- Scientific invariants: separate existence and entailment states, context summaries, causal interpretation warnings, null assumptions, finite results, and prespecified decision rules.
- Privacy: disabled outbound flags, local-only operation, restricted defaults, and redacted CLI failure messages.
- Adversarial inputs: forged promotions, fabricated citation attempts, duplicate records, malformed JSON, embedded instructions, unexpected fields, and bounded input.

No statistical procedure is implemented yet, so recovery of signals, type I error calibration, confidence-interval coverage, and benchmark performance have not been tested. Before execution adapters are accepted, add simulation-based tests with independently specified expectations. Before retrieval is accepted, add reproducible response fixtures and separately authorized live source checks.

## Reproducible checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\controlomics.exe validate examples/transcriptomics.project.json
.\.venv\Scripts\controlomics.exe validate examples/microscopy_ml.project.json
.\.venv\Scripts\python.exe scripts/export_schemas.py --check
.\.venv\Scripts\python.exe -m pip check
```

## Observed software checks, 2026-10-05

The final initial suite passed 37 tests in 0.378 seconds on Windows with CPython 3.14.0, Pydantic 2.12.4, and pydantic-core 2.41.5. The two example projects passed local CLI validation. Schema exports matched the Python definitions. `pip check` reported no broken requirements. The editable install and CLI version command completed successfully.

The isolated virtual environment occupied approximately 31.3 MB of file content. Project source, documentation, examples, ontology, and schemas occupied approximately 0.26 MB before this results entry. `scripts/check_resources.py` measured a peak Python working set of 36.1 MB while validating two examples, exporting ten schemas, and sizing files. These are decimal units and one local observation; file sizes exclude Git and bytecode, and the process peak is not a system-wide memory measurement. Routine operations meet the supplied resource constraints in this environment.

The first 33-test run passed, after which review identified numeric coercion of boolean literal privacy flags. A focused reproduction confirmed the behavior. Explicit boolean validation, conservative privacy-class consistency, unique control input IDs, and review timestamp ordering were then added, with regression checks included in the 37-test suite.

These results concern software checks only. There were no literature retrievals, biological control experiments, statistical procedure evaluations, benchmark runs, or expert annotations. Other Python versions and operating systems have not been tested.

## Planned empirical evaluation

ControlomicsBench should use published evidence, curated databases, independently annotated controls, and planted analytical failures. A language model must not be the sole source of reference answers. Reserve development and evaluation cases by scientific problem and source, with domain-held-out evaluation where feasible. Document access restrictions and any potential training contamination.

Predefine critical-control recall, control precision, unsupported recommendation rate, citation identity accuracy, statement entailment accuracy, context compatibility, flaw detection, execution success, and uncertainty calibration with explicit denominators and handling of abstentions. Measure uncertainty and expert agreement. Compare simpler method checklists, retrieval-only workflows, and appropriate model baselines. Ablations should isolate retrieval, structured representation, evidence review, deterministic execution, and the full workflow.

Sample sizes, expert recruitment, adjudication, statistical comparisons, and confidence intervals remain to be designed before benchmark evaluation. There are no benchmark scores, external reviews, or manuscript Results to report.
