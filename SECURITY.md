# Security

The current trust boundary is local JSON input. Project content, source metadata, purported review receipts, and future model responses are untrusted. Schema acceptance is not authentication. A caller can construct a false but internally consistent verification receipt; independent retrieval and provenance authentication remain future work.

Validation rejects unknown fields, unsupported versions, invalid identifiers, dangling references, contradictory evidence states, duplicate JSON keys, nonfinite numbers, and files larger than 2 MiB through the local project loader. Timezone-aware timestamps are required. JSON parsing never executes text, code, URLs, or embedded instructions. The package does not use `eval`, shell execution, dynamic plugins, or network requests. It creates JSON Schema files only in an explicitly supplied directory.

The 2 MiB input limit bounds ordinary input size. It is not complete protection from CPU exhaustion, hostile nesting, or filesystem abuse. Use this experimental library with access controls appropriate to local research material. CLI errors redact input content and paths. Avoid logging raw validation exception details in other applications.

Future literature and uploaded documents must remain data rather than application instructions. Provider integrations require destination restrictions, response limits, timeouts, redirect policy, injection-resistant separation, secret handling, and an outbound privacy boundary. Generated computational code requires separate review and execution isolation. Validation must never execute it.

No credentials are required by Stage 1. Do not commit `.env` files, tokens, API keys, clinical identifiers, private sequences, or raw research data. Dependency versions are recorded in the development lock file; updates require tests and review. No claim of perfect security, completed dependency audit, or completed prompt-injection defense is made.

Until a public security contact is established, report suspected problems privately to the repository owner through an available private contact channel. Do not post sensitive data or exploit-bearing research material in a public issue. Public release requires a documented reporting channel and review of these boundaries.
