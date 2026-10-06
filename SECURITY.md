# Security

Projects, literature metadata, human attestations, model output, and results are untrusted. Parsing does not authenticate a receipt, reviewer, execution event, or scientific conclusion. Hashes detect changes relative to a retained reference, but cannot authenticate a maliciously replaced manifest or fabricated consistent result.

## Input and interface

Bounded JSON rejects duplicate keys, nonfinite values, extra fields, unsupported versions, dangling references, and inconsistent states. Files and HTTP bodies are limited to 2 MiB. Numeric input also limits rows and resampling. These bounds are not complete protection from CPU exhaustion, hostile nesting, concurrency exhaustion, or filesystem abuse.

The server binds only to `127.0.0.1`. Mutating requests require exact local Host, Origin, and an unpredictable session token. Fixed asset routes prevent arbitrary file serving. Responses disable caching, external scripts and assets, framing, and referrer leakage. UI content uses text nodes and reports escape HTML. Request logging, persistent browser storage, and project databases are absent. Remote multiuser deployment is not qualified.

## External transport

HTTPS URLs cannot include credentials, fragments, or nonstandard ports. Provider preparation binds selected public fields to URLs or messages, and exact approval is checked before connection. DNS addresses must be globally routable; TLS uses a checked address and the original hostname. Redirects are rejected. Responses are bounded to 2 MiB with socket timeouts. Errors omit private input and response content.

Model policy and context remain separate. Strict proposals cannot supply citations, verification, or executable fields. These gates reduce malformed-output and injection consequences; they do not establish correct or harmless model reasoning. Hosted models remain unevaluated.

## Execution

Parsing never executes imported or generated code. Local computation invokes only a fixed template with explicit arguments and no shell. Artifact hashes are checked before importing the copied helper. The same bounded input bytes supply computation and hashing. Execution has a timeout and uses an owned temporary directory.

This is local fixed execution under the user's account, not an operating-system sandbox for arbitrary code. Review dispatched scripts before running them. A replaced runner or manifest cannot be secured by its own self-check. Arbitrary scripts, dynamic plugins, and primary-analysis orchestration are outside scope.

Do not commit keys, clinical identifiers, private sequences, raw datasets, or research projects. Development dependencies are recorded in `requirements-dev.lock`. No independent security audit or vulnerability-free claim is made. Public release requires an owner-selected license and private reporting channel. Until then, report concerns privately to the owner through an available private channel.
