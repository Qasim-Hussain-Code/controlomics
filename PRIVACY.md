# Privacy

Personal project ownership metadata is omitted from documentation, package attribution, interface footers, and newly generated reports. Review forms suggest pseudonymous reviewer identifiers. Imported descriptions, citations, annotations, and archives can still contain personal or confidential text; the software does not automatically anonymize free text. Published bibliographic attribution and third-party dependency notices remain intact for traceability. See [the cleanup scope](docs/PRIVACY_CLEANUP.md).

Projects, primary datasets, source text, and numeric inputs remain local. There is no telemetry, persistent project database, browser storage, or automatic upload. The browser holds work in memory and the local server processes transient snapshots. Exports may contain confidential descriptions; review them before sharing.

Description drafting, design profiles, additional claims, researcher specifications, source re-review, and evaluation use local processing. Evaluation bundles and annotations can themselves contain confidential research descriptions; they receive no implicit outbound authorization. Adding or selecting a claim does not serialize it into hosted context. Full source text entered in review forms is not retained in project or report exports.

Form edit detection keeps temporary signatures, including entered text and selected-file metadata, in browser memory only. Password inputs are excluded. There is no autosave. Replacing or clearing the workspace resets the previous project, review and evaluation forms, numeric selection, credential, request preview, and visible ledger. Closing the page discards unexported work; the browser's warning does not guarantee recovery.

Explicit local exports temporarily stage their content in a `.controlomics_*.tmp` file beside the selected destination, then replace it after a complete write and flush. Cleanup is attempted on ordinary errors; a process crash or denied cleanup can leave it on disk. New destinations use the platform's temporary-file permissions. Existing regular-file permission bits are retained; Windows discretionary ACLs are copied before writing staged content, including protected inheritance. POSIX owner and group are retained or the write fails. Replacement rejects symbolic links, detected POSIX extended access-control entries, and Windows encrypted, read-only, or reparse-point files. Encryption, other security attributes, and races are not qualified; use a separately protected destination when required. No automatic project saving is introduced.

## Classification and approval

Classes are SAFE, SENSITIVE_SCIENTIFIC, and RESTRICTED. Project and input defaults are RESTRICTED. Labels cannot understate declared input requirements. Project flags remain `network_enabled=false`, `external_transmission_allowed=false`, and `raw_data_must_remain_local=true`: they prohibit transmitting projects or raw data. Independently selected public fields use a separate approval boundary.

The outbound gate accepts named fields explicitly classified SAFE. Screening rejects recognized credentials, certain identifiers, local paths, emails, long DNA, RNA, or protein-like strings, and recognized service-token formats. Unrecognized text defaults to SENSITIVE_SCIENTIFIC until a caller explicitly classifies a selected field. Pattern screening cannot reliably recognize every confidential fact and may flag innocent text.

The exact destination, query or messages, and fields are previewed. A matching complete-request SHA-256 approval is required before DNS resolution or transmission. Literature parameters and the model policy are fixed. The project is never serialized for a provider. Receiving services apply their own data policies.

## Credentials and records

Optional model keys are passed in a separate authorization header and omitted from previews, audit values, project files, and reports. The browser clears the key on submission or cancellation. The CLI reads a dedicated environment variable. Keys exist transiently in process memory; other local software, extensions, and operating-system inspection are outside this boundary.

The ledger records purpose, destination, public fields, time, request and response hashes, status, size, credential presence, and transmission phase. Public queries may disclose research interests. Failed ATTEMPTED requests may already have transmitted content. NOT_STARTED, ATTEMPTED, and COMPLETED distinguish this explicitly. A completed response can be recorded even when later provider parsing rejects it. The ledger is a record of supplied events, not an authenticated or guaranteed-complete network history.

Numeric execution writes a bounded input snapshot in an owned temporary directory and removes it on normal completion. Crashes can leave local temporary files. Dispatched packages omit raw inputs. Human review retains statement records, locators, and source hashes, not full source text. Hashes reveal equality and can permit guesses of low-entropy content; they are not anonymization.

Package builds and review restores temporarily hold exportable records in an owned `.controlomics_directory_*` directory beside a new destination. They expose the final directory only after preparation succeeds and attempt cleanup on ordinary failures or interruption. A crash or denied cleanup can leave staging contents on disk; parent directories may remain. New directories inherit platform access rules, with restricted temporary-directory mode on POSIX. Select a protected parent for confidential records. Existing directories are never deliberately reused. Source and distribution builders also stage complete file replacements; separate artifact and record files are not a transaction.

Explicit CSV inspection reads only the selected local file and returns dimensions, adapter, original-byte hash, byte count, and limitations. It exports no unit identifiers or measurements, performs no execution, and sends nothing to an external service. Input summaries and their hashes can still reveal research information; inspect them before sharing. Raw inputs and unrecorded form edits are excluded from review bundles. The Bundle prepared label means a download was prepared for the recorded revision; retain it separately.

CLI and server errors redact values, credentials, and paths. Library users should not log raw validation structures. Store research files in ignored `local_projects/` or outside Git; ignore rules are convenience controls. Export projects and network records before closing the browser. Trusted local software can access the loopback service. See [SECURITY.md](SECURITY.md).

## Scientific validation records

The optional numerical reference environment lives in ignored `local_projects/validation/`. Its setup downloads public package wheels; its computation uses generated synthetic inputs locally and performs no network request. Retained public-method links and package metadata contain no private case data. No research record was uploaded for the numerical study.

Independent expert case data, identities, source text, blinding mappings, and original annotations belong in a protected local directory, not the tracked development examples. The local study-readiness script exports aggregate counts, checks, timestamps, and hashes, omitting names, descriptions, rationales, measurements, and input paths. Those hashes remain potentially sensitive fingerprints. A readiness result neither authorizes transmission nor authenticates independent expertise. See [the expert-study protocol](docs/INDEPENDENT_VALIDATION_PROTOCOL.md).

## Review archives

Local review bundles exclude raw CSV inputs, full supplied source texts, authorization credentials, and outbound bodies. They include potentially sensitive project descriptions and selected public query text, so inspect them before sharing. Network events are typed and screened. Saved hashes and empty ledgers do not authenticate completeness. See [review bundle limits](docs/REVIEW_BUNDLES.md).
