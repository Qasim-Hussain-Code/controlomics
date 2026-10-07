# Contributing

Changes should identify the scientific problem, preserve explicit evidence states, minimize data transmission, and include meaningful checks. Keep examples small and clearly label hypothetical controls and synthetic outcomes. Do not add fabricated citations, claims of validation, raw private data, credentials, or unsupported performance values.

Follow the installation commands in README.md, then install with `python -m pip install --no-build-isolation --no-deps -e .` inside your virtual environment. Update affected documentation, Python models, exported schemas, and format versions together when a compatibility change requires it. Document consequential choices in `docs/adr/`. Do not invent human authorship or contribution records.

Run these commands with the environment's Python executable:

```sh
python -m unittest discover -s tests -t . -v
python scripts/export_schemas.py --check
python -m pip check
python scripts/check_release.py
python scripts/build_distributions.py
python scripts/check_package.py dist/controlomics-0.6.0.dev0-py3-none-any.whl --output local_projects/package_checks.json
python scripts/check_install.py --wheel dist/controlomics-0.6.0.dev0-py3-none-any.whl --output local_projects/install_checks.json
```

The installation check creates a temporary clean environment and may download public dependency packages. Tests use synthetic fixtures and mocked provider transports. Do not run live retrieval or hosted-model checks as part of ordinary CI. For optional static checks, install `requirements-quality.lock` and run `ruff check src tests scripts`. Browser QA is optional and requires a fresh task-owned Chrome profile; instructions are in `scripts/check_ui.cjs`. The application does not need Node or Chrome for installation.

Keep software fixtures, live publication identities, synthetic numerical observations, and independent scientific evaluations separate. Network checks require explicit public-field approval. Hosted model adapters and specialist statistical extensions need independently specified expected behavior. Review browser changes at desktop and mobile sizes; optional checks use existing tools without adding application dependencies. See VALIDATION.md for recorded methods and limitations.

Routine commit messages contain at most three concise words joined with underscores. Before committing, inspect status and the diff, check for secrets and private material, run relevant checks, and verify that documentation describes actual behavior. This repository uses the project label `Controlomics` with blank Git author and committer emails to omit personal ownership information. Check the final commit metadata and do not inherit a personal global identity. The label does not authenticate a human contributor. Do not publish or force-push without authorization.

Public issues and pull requests must contain synthetic or explicitly public information. Do not attach a real review bundle, project export, request ledger, raw CSV, private source excerpt, or screenshot showing a private project. Hashes and pseudonyms do not make confidential scientific material safe to disclose. Report vulnerabilities through the channel described in SECURITY.md.

The project uses the owner-selected MIT License. Contributions must be material you have the right to submit under those terms. Preserve any applicable third-party attribution and license notices. The GitHub workflow and issue templates are prepared locally; their presence does not mean hosted checks or repository security settings have been activated.
