# Controlomics

Controlomics specifies and audits positive and negative controls around computational biology claims. Primary analyses and raw datasets remain in the researcher's environment. Private attribution removed is the project owner and primary author.

The research question is whether an evidence-grounded agent can derive scientifically appropriate controls across heterogeneous domains. Independent evaluation of that question remains pending.

Models reason. Sources provide evidence. Deterministic software calculates. Controlomics verifies. Researchers decide.

## Working research alpha

Version `0.6.0.dev0` includes local description drafting, multiple claims, inspectable design rules, editable unreviewed controls, Europe PMC and Crossref retrieval, human statement and context review, local CSV inspection, independent-group technical references, complete-pair statistical execution, reproducible packages, linked scientific reports, and a six-section local workspace. A judgment workbench records supplied annotations and revision hashes. Review archives save and restore the project, report, network ledger, and optional evaluation together. Optional hosted reasoning uses an interchangeable Messages interface. Project schema and ontology versions remain `0.1.0`.

The interface pairs a navy navigation rail with a light research canvas, restrained teal accents, and serif question headings. Project summaries show actual record counts. Search, class, and claim filters help inspect controls without changing them. Results and audits display the claim they challenge; execution details retain the control, assumptions, runner hash, and prespecified rule. Keyboard navigation, a mobile drawer, and reduced-motion support are included. See [the interface design](docs/INTERFACE.md) and [workspace preview](docs/validation/ui_workspace.png).

The default reasoner adds operation-specific null, specificity, robustness, confounder, and falsification specifications when stated design cues apply. These are provisional review questions, with inspectable triggers and limitations. The original two-reference baseline remains available. Both abstain from choosing biological entities without reviewed evidence. METHOD_BASED is specification review, not empirical validation. Hosted candidates cannot supply citations or promote their evidence status.

## Start locally

The existing Windows environment is ready. Double-click `Start_Controlomics.cmd` and open [the local workspace](http://127.0.0.1:8765). The [hypothetical transcriptomics demo](http://127.0.0.1:8765/#demo=transcriptomics) creates a local example without external requests.

```powershell
.\.venv\Scripts\python.exe -m controlomics serve
# In another terminal, create an executed synthetic demonstration:
.\.venv\Scripts\python.exe scripts/run_demo.py
```

Follow [the usage guide](docs/USAGE.md) for retrieval, human review, execution, and model configuration. Projects stay in browser memory until exported. The workspace distinguishes recorded changes, unrecorded form inputs, and a prepared bundle download. Retain the downloaded file before closing; raw inputs and unrecorded edits are excluded. Opening another project or starting an empty workspace asks before replacing work. The generated demonstration report is `local_projects/demo/report.html`.

Execution offers an explicit local CSV inspection before computation. It checks columns, finite values, unit or pair structure, and limits, then shows dimensions and the SHA-256 of the original bytes. It performs no control execution or external request. The same check is available through `controlomics inspect-input FILE --adapter INDEPENDENT_REFERENCE --output SUMMARY.json`. A valid file shape does not establish sampling assumptions.

Review [the design rules](docs/DESIGN_RULES.md) and [evaluation protocol](docs/EVALUATION.md). Included benchmark judgment sheets are UNASSESSED; they deliberately yield no scientific recommendation-quality score. Development expectations and source motivation are distinct from independent expert annotations.

For a new installation, use Python 3.11 or newer. Select a Python 3 executable explicitly if `python` or `py` resolves to an older scientific installation. Development was checked with CPython 3.14.0 on Windows.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
.\.venv\Scripts\python.exe -m controlomics validate examples/transcriptomics.project.json
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
.\.venv\Scripts\python.exe scripts/export_schemas.py --check
```

Pydantic is the sole runtime dependency. No weights, GPU, database, containers, provider SDKs, or frontend build tools are required. The lock file records the development environment rather than multi-platform qualification.

## Evidence, privacy, and limitations

Publication identity, statement support, context applicability, execution success, and claim validity are separate checks. Official metadata confirms recorded identities; human review supplies entailment attestations. Imported receipts and reviewer names are not authenticated proof. JSON Schema acceptance is structural; Python also checks relationships. See [the project format](docs/PROJECT_FORMAT.md) and [scientific specification](SCIENTIFIC_SPECIFICATION.md).

External requests require selected public fields and approval of the exact payload. Projects and raw inputs are never automatically serialized for providers. Credentials are excluded from previews, audit values, and reports. Pattern screening cannot identify every confidential fact. Review selected public fields and exports yourself. See [PRIVACY.md](PRIVACY.md) and [SECURITY.md](SECURITY.md).

Numeric execution supports reviewed technical positive and negative references using small independent-unit two-group calculations, permutation tests, and percentile bootstrap intervals. PASS and FAIL apply only to prespecified technical references. Inferential results receive no automatic scientific pass. A separate complete-pair mean-difference adapter requires an explicit specification and applicability rationale. It implements sign-flip permutation and whole-pair percentile bootstrap. Independence across pairs and sign invariance require justification. Other design challenges, biological controls, clustered and adjusted designs, and specialist primary analyses require applicable adapters.

Software tests, eight retained live identity checks, synthetic numerical observations, offline development comparisons, and interface review are recorded in [VALIDATION.md](VALIDATION.md). The six-case development fixtures test planted review-question codes. They are not an expert-grounded benchmark or evidence of agent generalization. No live hosted model or biological control was evaluated. See [METHODS.md](METHODS.md) and [ROADMAP.md](ROADMAP.md).

## Citation and license

[CITATION.cff](CITATION.cff) records human authorship without a DOI or publication claim. License selection and public release remain Private attribution removed's decisions. No license is granted and no repository has been published. MIT, BSD-3-Clause, and Apache-2.0 remain possible owner choices.
