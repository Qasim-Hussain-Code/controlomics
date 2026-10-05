# Privacy

The initial package operates on local files and includes no external model, network client, telemetry, upload, or persistent server storage. Schema fields require `network_enabled=false`, `external_transmission_allowed=false`, and `raw_data_must_remain_local=true`. This is a local application boundary, not a host-level network sandbox.

Information is classified as SAFE, SENSITIVE_SCIENTIFIC, or RESTRICTED. Input requirements and project privacy default to RESTRICTED. SAFE classification is a caller-supplied label, not automated detection. The software does not guarantee removal of identifiers, sequences, secrets, or patient information from free text.

Privacy flags require actual JSON booleans. A control's declared privacy class cannot understate its required inputs, and a project's class cannot understate a control requirement. These checks prevent inconsistent labels; they do not inspect the content of research text.

Local projects may themselves contain confidential text. Store them outside Git or in ignored `local_projects/`. The ignore patterns are convenience controls, not data-loss prevention. Review exports before sharing. Input hashes can disclose equality and may permit guessing of low-entropy inputs; they are not anonymization. Provenance should record necessary hashes and record identifiers rather than raw data, prompts, credentials, or private paths.

The CLI catches validation, parsing, and ordinary file failures and emits a generic message without rejected values or local paths. It does not log project contents. Callers using the library must avoid printing exception structures that include raw inputs. Operating-system errors, debug tools, backups, and other applications remain outside this boundary.

Before external integrations, implement an allowlisted, minimized outbound context, a classification review, explicit transmission authorization, and a network audit recording destination, purpose, time, and payload classification without secrets. Sensitive information must not leave implicitly. Restricted information must be rejected by the outbound boundary. No full project serialization may be passed directly to a provider. These are planned requirements, not an implemented privacy firewall.
