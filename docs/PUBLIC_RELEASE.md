# Public release

Controlomics 0.6.11.dev0 is a research preview distributed under MIT. The application runs locally. Public source, documentation, and downloadable packages support inspection and reproduction without publishing research projects or raw inputs.

## Validation boundary

The separate AI-assisted prototype audit reported PASS for source revision `ae6dd2de43971d533b65f37e33b85ba22ff8d19d` on Windows, Python 3.14, Chrome 154, and Edge 155 with synthetic inputs and mocked services. The [public audit summary](validation/prototype_audit_v0.6.11.json) retains the target, scope, counts, and evidence fingerprints. Full audit logs, source copies, screenshots, and local environment details remain private.

Publication preparation retains the scientific implementation while updating documentation, CI, source-root canonicalization, malformed-HTTP compatibility, and bounded connection closure. The separate audit does not cover these later changes. Release checks identify the prepared source revision and actual package hashes separately. The earlier audited artifacts remain immutable; rebuilt packages have their own hashes and installation checks. See [VALIDATION.md](../VALIDATION.md) for the retained observations and limitations.

The PASS concerns implemented technical contracts. It does not establish biological efficacy, control suitability in real experiments, cross-domain generalization, clinical use, authentic reviewer expertise, or a complete security certification. Requested 95% bootstrap intervals retain the measured 74.1% to 93.9% synthetic coverage limitation.

## What belongs in the public repository

- Reviewed source, schemas, ontology, tests, documentation, and synthetic examples.
- Scoped aggregate validation records and source hashes.
- MIT license text, citation guidance, contribution guidance, and privacy-aware issue forms.
- Read-only CI with immutable action pins and explicit dependency versions.

Research projects, raw data, full audit evidence, credentials, `.venv`, local packages, caches, installation paths, and scientific environments remain excluded. Do not upload the workstation directory or a research review bundle. Ignore rules alone are not a privacy guarantee; review the actual public inventory and reachable history.

Synthetic review receipts can use HUMAN as a schema fixture without representing a human review. Published bibliographic attribution remains distinct from project ownership. Historical records retain their original versions, statuses, and limitations.

## Hosting

Use GitHub for the public source repository and GitHub Releases for reviewed package downloads. Mark this development version as a prerelease. A release should identify its source revision, package SHA-256 values, installation requirements, and measured scope.

GitHub Pages may host static project documentation. It cannot run the Python application. The scientific workspace continues to run on the researcher's computer at the loopback address described in [README.md](../README.md). It must not be exposed through a public tunnel or reverse proxy. See [HOSTING.md](HOSTING.md).

## Repository settings

Keep the repository private during preparation and owner review. For an owner-authorized public release, enable GitHub private vulnerability reporting and verify that the public Security page offers Report a vulnerability before announcing the release. This applies to an existing repository as well as a new one and does not authorize changing its visibility. SECURITY.md describes the channel but cannot enable the setting. Do not replace it with an invented email or public vulnerability issue.

Run the configured hosted CI after the first reviewed push. Its Python matrix covers Windows and Linux on Python 3.11 through 3.14, plus macOS on Python 3.14. Optional Node 24 checks validate frontend syntax and the QA lifecycle helper. Configured jobs are not passing results until they have actually run.

Protect the main branch using the actual CI check names once available. Use reviewed changes, restrict repository permissions, and enable available secret scanning and push protection. Publication settings and repository ownership are controlled through GitHub, not package authorship metadata.

## Package and source consistency

Build from a reviewed public inventory, check package metadata and archive contents, and test clean offline installations using the existing local dependency wheels. Compare every executable file against the audited source and record any later changes with their own checks. Source archives must exclude ignored material and Git configuration.

Preserve the prior checked wheel, source distribution, source ZIP, and their recorded hashes. Generate publication candidates in a separate staging directory. Record final candidate hashes after all preparation is complete; do not replace an already published asset with different bytes under the same version.

Keep a complete local publication manifest containing the reviewed source inventory, code comparison, checks, asset hashes, and external settings. Do not publish command logs, profile paths, credentials, or user identifiers from that manifest.
