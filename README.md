# Controlomics

Controlomics specifies and audits positive and negative controls around computational biology claims. Primary analyses and raw datasets remain in the researcher's environment. Private attribution removed is the project owner and primary author.

The research question is whether an evidence-grounded agent can derive scientifically appropriate controls across heterogeneous domains. Independent evaluation of that question remains pending.

Models reason. Sources provide evidence. Deterministic software calculates. Controlomics verifies. Researchers decide.

## Working research alpha

Version `0.2.0.dev0` includes explicit claim intake, methodological control specifications, Europe PMC and Crossref retrieval, identifier consolidation, human statement review, conservative context comparison, three fixed numerical procedures, execution packages, result import, provenance, scientific reports, and a local browser workspace. Optional hosted reasoning uses an interchangeable Messages interface. Schema and ontology versions remain `0.1.0`.

The local baseline specifies positive known-signal and negative signal-absent technical references. It abstains from choosing biological entities without reviewed evidence. METHOD_BASED is a justified specification, not empirical validation. Hosted candidates cannot supply citations or promote their evidence status.

## Start locally

The existing Windows environment is ready. Double-click `Start_Controlomics.cmd` and open [the local workspace](http://127.0.0.1:8765). The [hypothetical transcriptomics demo](http://127.0.0.1:8765/#demo=transcriptomics) creates a local example without external requests.

```powershell
.\.venv\Scripts\python.exe -m controlomics serve
# In another terminal, create an executed synthetic demonstration:
.\.venv\Scripts\python.exe scripts/run_demo.py
```

Follow [the usage guide](docs/USAGE.md) for retrieval, human review, execution, and model configuration. Projects stay in browser memory until exported. Export your project and network ledger before closing the page. The generated demonstration report is `local_projects/demo/report.html`.

For a new installation, use Python 3.11 or newer. Select a Python 3 executable explicitly if `python` or `py` resolves to an older scientific installation. Development was checked with CPython 3.14.0 on Windows.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
.\.venv\Scripts\python.exe -m controlomics validate examples/transcriptomics.project.json
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/export_schemas.py --check
```

Pydantic is the sole runtime dependency. No weights, GPU, database, containers, provider SDKs, or frontend build tools are required. The lock file records the development environment rather than multi-platform qualification.

## Evidence, privacy, and limitations

Publication identity, statement support, context applicability, execution success, and claim validity are separate checks. Official metadata confirms recorded identities; human review supplies entailment attestations. Imported receipts and reviewer names are not authenticated proof. JSON Schema acceptance is structural; Python also checks relationships. See [the project format](docs/PROJECT_FORMAT.md) and [scientific specification](SCIENTIFIC_SPECIFICATION.md).

External requests require selected public fields and approval of the exact payload. Projects and raw inputs are never automatically serialized for providers. Credentials are excluded from previews, audit values, and reports. Pattern screening cannot identify every confidential fact. Review selected public fields and exports yourself. See [PRIVACY.md](PRIVACY.md) and [SECURITY.md](SECURITY.md).

Numeric execution supports small independent-unit two-group reference calculations, permutation tests, and percentile bootstrap intervals. PASS and FAIL apply only to prespecified technical references. Inferential results receive no automatic scientific pass. Specialist primary analyses, paired and clustered designs require other adapters.

Software tests, four live identity checks, synthetic numerical observations, and interface review are recorded in [VALIDATION.md](VALIDATION.md). The six-case development harness tests planted software findings. It is not an expert-grounded benchmark or evidence of agent generalization. No live hosted model or biological control was evaluated. See [METHODS.md](METHODS.md) and [ROADMAP.md](ROADMAP.md).

## Citation and license

[CITATION.cff](CITATION.cff) records human authorship without a DOI or publication claim. License selection and public release remain Private attribution removed's decisions. No license is granted and no repository has been published. MIT, BSD-3-Clause, and Apache-2.0 remain possible owner choices.
