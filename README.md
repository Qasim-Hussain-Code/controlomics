# Controlomics

Controlomics is a research software project for specifying and auditing positive and negative controls around computational biology analyses. The primary analysis remains in the researcher's environment. The project owner and primary author is Private attribution removed.

The research question is whether an evidence-grounded agent can derive scientifically appropriate controls from analysis descriptions and claims across heterogeneous computational biology domains. This question has not yet been evaluated.

The working principle is: Models reason. Sources provide evidence. Deterministic software calculates. Controlomics verifies. Researchers decide.

## Current status

Stage 0 and Stage 1 establish the scientific specification and a local Python schema package. Implemented capabilities are typed records, explicit evidence states, claim categories, consistency checks, a versioned ontology, local project validation, and JSON Schema export. The command line interface performs no network requests.

The two examples contain manually specified, hypothetical controls for transcriptomic analysis and microscopy classification. They exercise the representation. They are not agent output, experimental results, biological validation, or evidence of cross-domain generalization.

Control generation, claim extraction, literature retrieval, independent citation verification, automated context matching, execution packages, scientific reports, model providers, and ControlomicsBench remain planned. No domain is scientifically validated.

## Installation and use

Use Python 3.11 or newer. On Windows, select a Python 3 interpreter explicitly if `python` points to an older scientific installation. If `py -3` cannot find that interpreter, use its executable to create the environment instead. The project was initially checked with CPython 3.14.0.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
.\.venv\Scripts\controlomics.exe validate examples/transcriptomics.project.json
.\.venv\Scripts\controlomics.exe validate examples/microscopy_ml.project.json
.\.venv\Scripts\controlomics.exe export-schemas schemas/0.1.0
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The editable install uses setuptools already installed by the lock file. A normal `pip install .` resolves the compatible dependency ranges in `pyproject.toml`; the lock file records the initial development environment and is not a claim of multi-platform testing. Python module invocation, `python -m controlomics`, exposes the same commands.

`validate` checks structure, identifiers, references, evidence-state prerequisites, and specified result consistency. Success does not establish that a publication exists, that its text supports a statement, that a reviewer is authentic, or that a control is appropriate. Validation failures omit input content and paths from the CLI output. Library exceptions should also be handled without logging raw records.

JSON Schema files describe structure. Python validators additionally enforce relational checks that JSON Schema does not express. See [the project format](docs/PROJECT_FORMAT.md).

## Privacy, evidence, and limitations

Projects are local files. This version has no network clients, model integration, server storage, or data upload. Privacy flags reject network-enabled projects. This does not classify free text automatically or prevent other software from reading local files. Keep confidential projects outside the repository or in the ignored `local_projects/` directory. See [PRIVACY.md](PRIVACY.md) and [SECURITY.md](SECURITY.md).

A candidate cannot declare itself evidence-backed. Reviewed records distinguish publication existence, statement-specific entailment, and context compatibility. Review receipts are attestations supplied by callers; they are not independent verification. Software cannot infer scientific truth from a well-formed record. Known publication aliases sharing an identifier are rejected as duplicates; resolving disjoint PMID, PMCID, and DOI records remains future work.

No benchmark, statistical evaluation, expert review, public release, or empirical generalization result exists. See [VALIDATION.md](VALIDATION.md) for the scope of checks and [ROADMAP.md](ROADMAP.md) for subsequent stages.

## Citation and license

[CITATION.cff](CITATION.cff) contains project authorship without a DOI or publication claim. The software license has not yet been selected. Public release is deferred until Private attribution removed selects a license and the publication readiness checks are complete. MIT, BSD-3-Clause, and Apache-2.0 are candidates for that decision; no license is granted by this list.
