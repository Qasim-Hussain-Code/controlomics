# Controlomics

Controlomics is a local research workspace for specifying, reviewing, executing, and auditing controls around computational biology claims. Primary analyses and raw datasets remain in the researcher's environment.

The research question is whether an evidence-grounded agent can derive scientifically appropriate controls across heterogeneous domains. Independent evaluation of that question remains pending.

[The complete architecture walkthrough](docs/AGENT_ARCHITECTURE.md) maps the implemented components and their scientific and privacy boundaries. The default reasoner uses inspectable rules; an optional hosted model proposes candidates. Researchers review source support and decide what conclusions are justified.

## Working research alpha

Version `0.6.6.dev0` includes local description drafting, multiple claims, inspectable design rules, editable unreviewed controls, Europe PMC and Crossref retrieval, human statement and context review, local CSV inspection, independent-group technical references, complete-pair statistical execution, reproducible packages, linked scientific reports, and a six-section local workspace. A judgment workbench records supplied annotations and revision hashes. Review archives save and restore the project, report, network ledger, and optional evaluation together. Optional hosted reasoning uses an interchangeable Messages interface. Project schema and ontology versions remain `0.1.0`.

Local exports preserve the previous file when an ordinary write or replacement fails. Evaluation reports identify their recorded source bundle by hash; replacing that bundle or selecting another partition clears stale metrics. Pending operations protect form inputs, and local session renewal retains the open workspace without automatically repeating a request.

Execution packages and restored review bundles prepare their complete contents before exposing a new directory. Choose a destination that does not already exist, including an empty directory. Fixed runners protect inputs and package files from conflicting output paths and stage result writes. The local server bounds connection workers and inactive reads; these controls do not qualify it for remote deployment.

The interface restores the earlier six-section layout with a warm ivory navigation rail and terracotta selected sections, scientific overview, four record-count cards, and a responsive two-column control collection. Terracotta actions, brown navigation text, slate record text, white surfaces, and restrained blue, ochre, and burgundy scientific states distinguish the interface elements. The overview retains the complete question and actual project and analysis identifiers; its conceptual scientific SVG is an illustration. Control specifications retain named fields for rationale, expected behavior, failure meaning, assumptions, and limitations. Search, class, claim, and evidence-state filters inspect the collection without changing it; Clear filters restores the complete collection. Results and audits retain the claim they challenge; execution details retain the control, assumptions, runner hash, and prespecified rule. Keyboard navigation, a mobile drawer, and reduced-motion support are included. See [the interface design](docs/INTERFACE.md).

Execution requires an explicit reviewed-control selection and explains missing prerequisites. Procedure inputs remain available while changing the control or refreshing the same project snapshot, so review them before another action. Editor, source-review, and judgment workbench actions focus their destination. The named external-request dialog initially focuses Cancel. Save-state announcements remain available at narrow widths. The [current software rerun](docs/validation/software_checks_warm_phase.json) passed 175 tests, and [isolated browser observations](docs/validation/ui_checks_warm_phase.json) cover 42 section/width combinations, warm navigation and actions, long control names, and the retained scientific/privacy workflows. Extracted-package, distribution, and offline clean wheel/source installation checks passed for the artifact hashes retained in [VALIDATION.md](VALIDATION.md). The [preceding software record](docs/validation/software_checks_palette_phase.json) reports 175 passing tests for version 0.6.5.dev0, and its [isolated browser observations](docs/validation/ui_checks_palette_phase.json) cover 42 section/width combinations at that earlier navy/slate snapshot. Those observations do not attest the changed colors. The [validation account](VALIDATION.md) retains earlier records and the Windows connection interruption with an unconfirmed cause. Independent usability, accessibility conformance, and scientific validation remain pending.

![Controlomics local workspace with no project open](docs/validation/ui_workspace.png)

The default reasoner adds operation-specific null, specificity, robustness, confounder, and falsification specifications when stated design cues apply. These are provisional review questions, with inspectable triggers and limitations. The original two-reference baseline remains available. Both abstain from choosing biological entities without reviewed evidence. METHOD_BASED is specification review, not empirical validation. Hosted candidates cannot supply citations or promote their evidence status.

## Start locally

Download or clone the source, open a terminal in its root, and use Python 3.11 or newer. No GitHub account, model subscription, API credential, or raw dataset is needed for the local synthetic demonstration. Select a Python 3 executable explicitly if your machine also has an older scientific installation.

On Windows:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps .
.\.venv\Scripts\python.exe -m controlomics serve
```

On Linux or macOS:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install --no-build-isolation --no-deps .
.venv/bin/python -m controlomics serve
```

Open [the local workspace](http://127.0.0.1:8765). The [hypothetical transcriptomics demo](http://127.0.0.1:8765/#demo=transcriptomics) creates an example without provider requests. Windows users can subsequently start the installed environment with `Start_Controlomics.cmd`. Stop the server with Ctrl+C. Use `--port PORT` if the default port is occupied. Do not expose the server through a reverse proxy or public tunnel.

Follow [the usage guide](docs/USAGE.md) for retrieval, human review, execution, and model configuration. Projects stay in browser memory until exported. The workspace distinguishes recorded changes, unrecorded form inputs, and a prepared bundle download. Retain the downloaded file before closing; raw inputs and unrecorded edits are excluded. Opening another project or starting an empty workspace asks before replacing work. The generated demonstration report is `local_projects/demo/report.html`.

Execution offers an explicit local CSV inspection before computation. It checks columns, finite values, unit or pair structure, and limits, then shows dimensions and the SHA-256 of the original bytes. It performs no control execution or external request. The same check is available through `controlomics inspect-input FILE --adapter INDEPENDENT_REFERENCE --output SUMMARY.json`. A valid file shape does not establish sampling assumptions.

Review [the design rules](docs/DESIGN_RULES.md) and [evaluation protocol](docs/EVALUATION.md). Included benchmark judgment sheets are UNASSESSED; they deliberately yield no scientific recommendation-quality score. Development expectations and source motivation are distinct from independent expert annotations.

For development, install the package in editable mode and run the checks below. Use `.venv/bin/python` instead of the Windows executable path on Linux or macOS. Recorded local checks use CPython 3.14.0 on Windows; the configured GitHub matrix covers Python 3.11 to 3.14 on Windows and Linux, plus 3.14 on macOS. Those hosted jobs have not run before repository publication.

```powershell
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
.\.venv\Scripts\python.exe -m controlomics validate examples/transcriptomics.project.json
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
.\.venv\Scripts\python.exe scripts/export_schemas.py --check
.\.venv\Scripts\python.exe scripts/check_release.py
```

Pydantic is the sole direct runtime dependency. No weights, GPU, database, containers, provider SDKs, or frontend build tools are required. Installation downloads public Python dependencies; ordinary local use and tests do not contact literature or model providers. The lock file records exact development versions without wheel hashes, rather than multi-platform qualification. See [CONTRIBUTING.md](CONTRIBUTING.md) for package checks and [the public release checklist](docs/PUBLIC_RELEASE.md) for the remaining release gates.

## Evidence, privacy, and limitations

Publication identity, statement support, context applicability, execution success, and claim validity are separate checks. Official metadata confirms recorded identities; human review supplies entailment attestations. Imported receipts and reviewer names are not authenticated proof. JSON Schema acceptance is structural; Python also checks relationships. See [the project format](docs/PROJECT_FORMAT.md) and [scientific specification](SCIENTIFIC_SPECIFICATION.md).

External requests require selected public fields and approval of the exact payload. Projects and raw inputs are never automatically serialized for providers. Credentials are excluded from previews, audit values, and reports. Pattern screening cannot identify every confidential fact. Review selected public fields and exports yourself. See [PRIVACY.md](PRIVACY.md) and [SECURITY.md](SECURITY.md).

Numeric execution supports reviewed technical positive and negative references using small independent-unit two-group calculations, permutation tests, and percentile bootstrap intervals. PASS and FAIL apply only to prespecified technical references. Inferential results receive no automatic scientific pass. A separate complete-pair mean-difference adapter requires an explicit specification and applicability rationale. It implements sign-flip permutation and whole-pair percentile bootstrap. Independence across pairs and sign invariance require justification. Other design challenges, biological controls, clustered and adjusted designs, and specialist primary analyses require applicable adapters.

Software tests, eight retained live identity checks, synthetic numerical observations, offline development comparisons, and interface review are recorded in [VALIDATION.md](VALIDATION.md). The six-case development fixtures test planted review-question codes. They are not an expert-grounded benchmark or evidence of agent generalization. A frozen [numerical validation study](docs/NUMERICAL_VALIDATION.md) matched 896 scalar comparisons against independently maintained SciPy across 128 cases. Its 7,000 synthetic trials revealed small-sample undercoverage: intervals requested at 95% covered the truth in 74.1% to 93.9% of trials. The [independent expert-study protocol](docs/INDEPENDENT_VALIDATION_PROTOCOL.md) defines the real data and reviewer work still required. No live hosted model or biological control was evaluated. See [METHODS.md](METHODS.md) and [ROADMAP.md](ROADMAP.md).

## Citation and license

[The citation note](docs/CITATION.md) identifies the software without personal authorship metadata, a DOI, or a publication claim. The source is available under the owner-selected [MIT License](LICENSE). Its notice identifies the copyright holders collectively without disclosing personal names. Public bibliography and third-party dependencies retain their own attribution and terms. This local preparation does not publish a repository, release, package, or research artifact.
