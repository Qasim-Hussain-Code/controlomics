# Security

Projects, literature metadata, human attestations, model output, and results are untrusted. Parsing does not authenticate a receipt, reviewer, execution event, or scientific conclusion. Hashes detect changes relative to a retained reference, but cannot authenticate a maliciously replaced manifest or fabricated consistent result.

## Input and interface

Bounded JSON rejects duplicate keys, nonfinite values, extra fields, unsupported versions, dangling references, and inconsistent states. Files and HTTP bodies are limited to 2 MiB. Numeric input also limits rows and resampling. These bounds are not complete protection from CPU exhaustion, hostile nesting, concurrency exhaustion, or filesystem abuse.

The local server limits connection workers to 16 and applies a 10-second read-inactivity timeout from handler setup, including headers. Excess connections attempt 503 without allocating a worker. After response half-close, at most 64 KiB of arriving bytes are discarded for at most 50 milliseconds to reduce response-hiding resets; rejected contents are never parsed or stored. Clients can still observe interruption. This is not a total request deadline; clients that keep sending can occupy slots. Duplicate authorization or framing headers, unsupported transfer encoding, and non-object action bodies are rejected. Unexpected operation failures use a fixed redacted response; handler tracebacks and request logs are omitted. These measures bound ordinary resources without establishing availability against hostile local software.

The server binds only to `127.0.0.1`. Mutating requests require exact local Host, Origin, and an unpredictable session token. Fixed asset routes prevent arbitrary file serving. Responses disable caching, external scripts and assets, framing, and referrer leakage. UI content uses text nodes and reports escape HTML. Request logging, persistent browser storage, and project databases are absent. Remote multiuser deployment is not qualified.

Interface availability messages and disabled execution buttons supplement server validation; they cannot establish adapter applicability, sampling assumptions, or authentic review. Selecting a reviewed control is explicit, and a completed or packaged control does not cause another control to be selected automatically. The named outbound-request dialog initially focuses Cancel. This does not replace the exact-request approval check or establish complete accessibility or security assurance.

POST authorization is checked before waiting for the body; non-ASCII tokens are rejected and truncated bodies cannot be parsed. Browser imports reject invalid UTF-8 instead of silently replacing bytes. CSV decoding accepts an optional UTF-8 byte-order mark while hashes retain the original bytes. The local JSON request budget includes formatting and the project snapshot, so files near the 2 MiB limit may require CLI use.

## External transport

HTTPS URLs cannot include credentials, fragments, or nonstandard ports. Provider preparation binds selected public fields to URLs or messages, and exact approval is checked before connection. DNS addresses must be globally routable; TLS uses a checked address and the original hostname. Redirects are rejected. Responses are bounded to 2 MiB with socket timeouts. Errors omit private input and response content.

Model policy and context remain separate. Strict proposals cannot supply citations, verification, or executable fields. These gates reduce malformed-output and injection consequences; they do not establish correct or harmless model reasoning. Hosted models remain unevaluated.

Browser JSON imports and context entries use the same duplicate-key-aware local parser before subsequent validation. Model completion requires one known target claim before sending. Editing cannot erase a reviewed specification, and re-review requires the current snapshot hash. These consistency boundaries do not authenticate the caller, source text, or researcher name. Evaluation origin labels are also unauthenticated caller attestations.

Whole-project parsing checks fixed-runner hashes when the plan supplies one and rejects multiple result records for one execution, matching individual-result import. Evaluation reports hash their source bundle; changed bundles or partition selections invalidate displayed metrics. These bindings establish internal consistency, not genuine execution or independent scientific judgment.

Explicit local exports use staged replacement to preserve existing files on ordinary failures. They reject nonregular destinations and conflicting CLI sidecar paths before writing or sending. Existing mode bits and Windows discretionary ACLs are retained; ACL-copy failures abort before writing staged content. POSIX owner/group changes must succeed before writing. Detected extended POSIX access controls and encrypted, read-only, or reparse-point Windows files require a new ordinary destination. Other security attributes, power-loss durability, filesystem races, and coordinated multi-file changes remain outside this guarantee. A process crash or denied cleanup can leave a staging file. Windows ACL handling uses [GetNamedSecurityInfo](https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-getnamedsecurityinfow) and [SetNamedSecurityInfo](https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-setnamedsecurityinfow) with protected-inheritance flags. An interrupted browser response is never automatically replayed; approved external transmission may already have occurred without a returned ledger.

## Execution

Parsing never executes imported or generated code. Local computation invokes only a fixed template with explicit arguments and no shell. Artifact hashes are checked before importing the copied helper. The same bounded input bytes supply computation and hashing. Execution has a timeout and uses an owned temporary directory.

This is local fixed execution under the user's account, not an operating-system sandbox for arbitrary code. Review dispatched scripts before running them. A replaced runner or manifest cannot be secured by its own self-check. Arbitrary scripts, dynamic plugins, and primary-analysis orchestration are outside scope.

New package builds include a hashed standard-library export helper and reject result destinations that alias the input or known package files. CLI exports also protect auxiliary inputs. Package and review-restore destinations must be absent; complete directory contents are staged before rename. Ordinary write failures and interruption attempt staging cleanup. Historical packages remain bound to their original runner hashes and do not acquire these new write protections. Filesystem races, crash cleanup, power-loss guarantees, and coordinated artifact/record updates remain outside the boundary.

Do not commit keys, clinical identifiers, private sequences, raw datasets, or research projects. Development dependencies are recorded in `requirements-dev.lock`. No independent security audit or vulnerability-free claim is made.

## Vulnerability reporting and supported versions

Only the current `0.6.9.dev0` research preview is maintained. Older development snapshots receive no separate security fixes. There is no response-time guarantee or independent security certification.

Before uploading source, the repository owner must enable GitHub private vulnerability reporting in an empty public repository and verify that its Security page offers **Report a vulnerability**. Use that private channel for suspected vulnerabilities, with a minimal synthetic reproduction and affected version. Do not include credentials, identifying information, or real research data. Do not open a public issue for an undisclosed vulnerability.

The repository has not yet been published, so this private channel is not currently available. SECURITY.md cannot activate it. If the eventual repository lacks the button, its reporting setup is incomplete; do not assume an unlisted email address or invented contact. The owner should keep publication blocked until the channel is configured. See [GitHub's reporting instructions](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/report-privately) and [owner configuration instructions](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository).

## Review archive boundary

Review ZIP imports use a fixed member allowlist and bounded in-memory reads. Duplicate names, traversal, symbolic links, encryption, unsupported compression, oversize contents, hash mismatches, and inconsistent records are rejected. Imported HTML is never executed or opened; reports are regenerated. Archive manifests and reviewer names remain unauthenticated. These checks apply to review archives, not arbitrary ZIP files.

Standalone report generation applies the same typed network-ledger checks as review archives. Raw request bodies, authorization headers, and inconsistent public-field bindings cannot enter a report through that parameter. Escaping, structural validation, and retained hashes do not establish the truth of a consistent imported record.
