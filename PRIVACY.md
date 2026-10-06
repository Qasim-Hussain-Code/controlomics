# Privacy

Projects, primary datasets, source text, and numeric inputs remain local. There is no telemetry, persistent project database, browser storage, or automatic upload. The browser holds work in memory and the local server processes transient snapshots. Exports may contain confidential descriptions; review them before sharing.

Description drafting, design profiles, additional claims, researcher specifications, source re-review, and evaluation use local processing. Evaluation bundles and annotations can themselves contain confidential research descriptions; they receive no implicit outbound authorization. Adding or selecting a claim does not serialize it into hosted context. Full source text entered in review forms is not retained in project or report exports.

## Classification and approval

Classes are SAFE, SENSITIVE_SCIENTIFIC, and RESTRICTED. Project and input defaults are RESTRICTED. Labels cannot understate declared input requirements. Project flags remain `network_enabled=false`, `external_transmission_allowed=false`, and `raw_data_must_remain_local=true`: they prohibit transmitting projects or raw data. Independently selected public fields use a separate approval boundary.

The outbound gate accepts named fields explicitly classified SAFE. Screening rejects recognized credentials, certain identifiers, local paths, emails, and long sequence-like strings. Unrecognized text defaults to SENSITIVE_SCIENTIFIC until a caller explicitly classifies a selected field. Pattern screening cannot reliably recognize every confidential fact.

The exact destination, query or messages, and fields are previewed. A matching complete-request SHA-256 approval is required before DNS resolution or transmission. Literature parameters and the model policy are fixed. The project is never serialized for a provider. Receiving services apply their own data policies.

## Credentials and records

Optional model keys are passed in a separate authorization header and omitted from previews, audit values, project files, and reports. The browser clears the key on submission or cancellation. The CLI reads a dedicated environment variable. Keys exist transiently in process memory; other local software, extensions, and operating-system inspection are outside this boundary.

The ledger records purpose, destination, public fields, time, request and response hashes, status, size, credential presence, and transmission phase. Public queries may disclose research interests. Failed ATTEMPTED requests may already have transmitted content. NOT_STARTED, ATTEMPTED, and COMPLETED distinguish this explicitly.

Numeric execution writes a bounded input snapshot in an owned temporary directory and removes it on normal completion. Crashes can leave local temporary files. Dispatched packages omit raw inputs. Human review retains statement records, locators, and source hashes, not full source text. Hashes reveal equality and can permit guesses of low-entropy content; they are not anonymization.

CLI and server errors redact values, credentials, and paths. Library users should not log raw validation structures. Store research files in ignored `local_projects/` or outside Git; ignore rules are convenience controls. Export projects and network records before closing the browser. Trusted local software can access the loopback service. See [SECURITY.md](SECURITY.md).
