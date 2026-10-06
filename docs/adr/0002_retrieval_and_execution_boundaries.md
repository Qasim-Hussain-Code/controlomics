# ADR 0002: Explicit retrieval and fixed execution boundaries

Status: accepted for the research alpha.

Problem: the scientific schemas need an operational workflow without making generated prose an authority, transmitting private projects, or executing arbitrary model code.

Alternatives considered: automatic full-project model calls, a single literature provider, automated lexical entailment acceptance, specialist execution environments, and a bounded local workflow with separate review and execution adapters.

Decision: use an offline method baseline and an optional Messages-compatible provider. Retrieve literature through Europe PMC and Crossref. Require exact-request approval and SAFE selected fields before external calls. Connect to checked public IPs with hostname-verified TLS and disable redirects. Separate publication identity from human-attested entailment and context. Execute only fixed independent-unit numeric templates locally or through exported packages.

Scientific rationale: citation existence does not imply support or applicability. Generic technical reference specifications cannot substitute for biological controls. Prespecified technical reference decisions are distinct from open-ended statistical interpretation. Conservative audit outcomes preserve abstention.

Technical rationale: retain Pydantic as the sole runtime dependency. Use the standard library for HTTP, statistics, temporary packages, bounded subprocess execution, and loopback serving. Source hashes, input snapshots, seeds, and software versions make the narrow adapters inspectable.

Privacy implications: projects remain local; only reviewed public query or reasoning fields leave. Credentials are ephemeral authorization headers and are excluded from exports. Local numeric execution creates temporary files; a crash can leave remnants. Dispatch is preferable when institutional data policy requires it.

Security implications: pin the connection to checked public addresses, retain TLS host verification, bound input and response size, reject redirects, enforce fixed model policy, and reject unsupported model fields. The local interface requires host, origin, and token checks and serves fixed assets only. Package manifests and review receipts are unauthenticated, and no execution sandbox for arbitrary code is claimed.

Limitations: the local baseline is a template baseline rather than generalized biological reasoning. Hosted inference is unconfigured and unvalidated. Human entailment is an attestation. Numeric adapters support only independent two-group scalar observations. Development cases are not expert-grounded benchmark truth.

Conditions for reconsideration: independent expert review, new scientific execution requirements, validated model and entailment evaluations, institutional deployment, authenticated provenance, or a concrete need for additional providers or persistence.
