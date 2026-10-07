# Public repository preparation

This is a local preparation of the `0.6.0.dev0` research preview. It does not authorize or perform a GitHub push, public repository creation, package publication, release upload, or research-data disclosure.

## Owner decisions and external settings

The owner explicitly selected MIT. Its complete text is in [LICENSE](../LICENSE), and package metadata identifies MIT with that license file. The notice identifies the copyright holders collectively without disclosing personal names. Public bibliography and third-party dependencies retain their own attribution and terms; the project's license does not relicense them.

The owner selected GitHub private vulnerability reporting. Before uploading source, enable it in an empty public repository and verify its reporting button. This requires repository settings after creation; the local SECURITY.md does not enable it. Creation and source upload still require the owner's publication decision. Choose a repository slug and account without disclosing a private personal identity. No remote URL has been invented or configured.

Protect the default branch with required software checks and reviewed changes once actual check names exist. Enable available secret scanning and push protection, and review repository permissions. These are owner settings, not features activated by a source file. Confirm that hosted CI passes before claiming cross-platform support. [GitHub's private reporting configuration](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository) explains the reporting setting.

## Source and history boundary

Only reviewed source files belong in the public repository. `.venv`, `local_projects`, research `data`, provider credentials, downloaded scientific environments, local execution packages, installation paths, and build caches remain excluded. Three small CSV examples are synthetic fixtures. Literature identities are public bibliography; human evidence-review and judgment fixtures are hypothetical or UNASSESSED. Existing validation records explicitly distinguish software observations, public identity checks, synthetic arithmetic, and pending independent scientific evaluation.

The authorized privacy cleanup rewrote local history to project-only author and committer labels with blank emails, redacted matched private attribution, and removed obsolete personal screenshots and citation records. See [the privacy cleanup record](PRIVACY_CLEANUP.md). A new public release check also screens current source, document links, package attribution, exact frozen numerical source hashes, CI action pins, and optionally reachable Git history. Screening does not establish that every possible identifying or confidential fact has been recognized. Review screenshots and scientific text as well.

Do not publish this machine's entire directory or upload a project bundle. A clean Git source export excludes ignored local artifacts and Git configuration. Preserve the full validation evidence, including negative numerical findings; do not market this preview as independently scientifically validated. Pseudonymous reviewer labels and consistent receipts cannot authenticate expertise, independence, source entailment, or real execution.

## Reproduce local release checks

The observed local environment is Windows, CPython 3.14.0, Pydantic 2.12.4, and setuptools 83.0.0. [The software record](validation/software_checks_release_phase.json) reports 149 tests with zero failures, errors, or skips. Ruff 0.14.14 reported no static Python findings; [actionlint 1.7.12](validation/workflow_checks_release_phase.json) reported no workflow findings. All 29 exported schemas match their definitions and `pip check` found no inconsistent requirements.

[The extracted package check](validation/package_checks_release_phase.json), [clean wheel installation](validation/install_checks_release_phase.json), [clean source installation](validation/sdist_install_checks_release_phase.json), and [distribution contents check](validation/distribution_checks_release_phase.json) retain artifact hashes and actual results. Installation tests use isolated imports outside the checkout and local dependency wheels. Archive ownership metadata is normalized and personal package author fields are absent. These records identify particular build snapshots; a development-version rebuild can have a different artifact hash.

[The initial advisory lookup](validation/dependency_advisory_checks_before_update.json) identified GHSA-h35f-9h28-mq5c in setuptools 80.9.0. The build dependency was updated to its patched version 83.0.0; [the final lookup](validation/dependency_advisory_checks.json) returned no matched advisories for nine exact package versions, including optional numerical and lint dependencies. This is a point-in-time lookup, not a vulnerability-free claim. The [maintainer advisory](https://github.com/pypa/setuptools/security/advisories/GHSA-h35f-9h28-mq5c) describes the source-distribution exclusion issue. Only public dependency names and versions were sent to OSV; no source, research data, or personal information was uploaded.

One early Windows server test encountered an aborted localhost connection; the same server tests then passed separately and the full 149-test suite passed. A clean source installation first failed because pip attempted to write into the restricted machine's global wheel cache; the checker now uses `--no-cache-dir`, and the subsequent clean source install passed. These were retained as software preparation observations rather than scientific findings.

Use the environment's Python executable, `.venv/Scripts/python.exe` on Windows or `.venv/bin/python` elsewhere:

```sh
python -m unittest discover -s tests -t . -v
python scripts/export_schemas.py --check
python -m pip check
python scripts/check_release.py --history --output local_projects/release/source_checks.json
python scripts/build_distributions.py
python scripts/check_package.py dist/controlomics-0.6.0.dev0-py3-none-any.whl --output local_projects/release/package_checks.json
python scripts/check_install.py --wheel dist/controlomics-0.6.0.dev0-py3-none-any.whl --output local_projects/release/install_checks.json
python scripts/check_install.py --sdist dist/controlomics-0.6.0.dev0.tar.gz --output local_projects/release/sdist_install_checks.json
python scripts/check_distribution_contents.py --wheel dist/controlomics-0.6.0.dev0-py3-none-any.whl --sdist dist/controlomics-0.6.0.dev0.tar.gz --output local_projects/release/distribution_checks.json
python scripts/export_public_source.py --output dist/controlomics-0.6.0.dev0-source.zip --record local_projects/release/source_export.json
```

Run the source check with `--require-license` for the owner-approved MIT release. A PASS for source hygiene does not activate external settings. The installation check uses a fresh temporary virtual environment and isolated imports outside the checkout; it may download public pinned dependencies. `--wheelhouse DIRECTORY` makes it offline using reviewed dependency wheels. Wheel smoke checks do not authenticate untrusted external wheels.

The GitHub workflow uses read-only repository permissions, immutable action commit pins, credential-free checkout, bounded job times, and `pull_request` for untrusted changes. It contains no publishing job or provider credentials. Its software jobs cover Windows and Linux on Python 3.11 to 3.14 and macOS on Python 3.14. These jobs are configured, not observed passing until the repository exists and GitHub runs them. Dependency-update proposals require ordinary review; updates to frozen numerical source require a new versioned protocol rather than silently rewriting recorded outcomes. See [GitHub's secure workflow guidance](https://docs.github.com/en/actions/reference/security/secure-use).

## Scientific release description

Describe the release as an operational local research alpha for structured controls and evidence review. The default reasoner is deterministic and inspectable. Hosted models are optional and unevaluated. Execution covers narrowly specified independent technical references and complete-pair mean differences. Small-sample bootstrap undercoverage is a measured limitation: 95% requested intervals covered the synthetic truth in 74.1% to 93.9% of trials. No expert-grounded recommendation-quality score, validated biological domain, clinical qualification, or demonstrated agent generalization is available.

The architecture is documented in [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md), numerical methods and findings in [NUMERICAL_VALIDATION.md](NUMERICAL_VALIDATION.md), and the outstanding expert study in [INDEPENDENT_VALIDATION_PROTOCOL.md](INDEPENDENT_VALIDATION_PROTOCOL.md). A public source release can support review and reproduction; it does not complete that study.
