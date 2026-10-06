# ADR 0005: Local inspection and workspace continuity

Status: Accepted for the local research alpha, 2026-10-06.

## Context

Researchers need to identify malformed numeric inputs before running a control, understand which claim a result challenges, and avoid mixing unrecorded edits or earlier reviews into a replacement project. The application has no persistent project database or browser storage. Scientific appropriateness and independent evaluation remain separate from software operation.

## Decision

Add an explicit CSV inspection action that uses the existing bounded adapter parsers. Return a typed summary of dimensions, original-byte SHA-256, byte count, adapter, and limitations. Omit measurements and identifiers. Inspection performs no control execution or external request and does not judge sampling assumptions.

Track form signatures and recorded revisions in browser memory. Distinguish unrecorded inputs, export-needed records, and a prepared complete-bundle download. Retaining the file is the researcher's action. Ask before replacement, validate incoming records first, and clear prior forms, inputs, reviews, evaluations, credentials, previews, and ledger displays together.

Show the scientific target in control details, result panels, audits, and reports. Claim filters affect display only. Reports link claims, specifications, and results internally, validate the supplied network ledger, and remain escaped and self-contained. Print styles are supplied; pagination has not been qualified.

Correct floating-point intermediate overflow and extreme-scale variance without broadening the statistical adapters. Use ordinary precise summation where possible and exact rational accumulation only for overflowing totals. Reject unrepresentable effects. The fixed runner copies these functions and retains its own hash.

## Alternatives and consequences

Automatic persistence could retain confidential drafts on the device and needs a separately specified storage and recovery policy. It is not introduced. Automatic execution during file selection would blur inspection and computation; inspection stays an explicit action. An added numeric or frontend dependency is unnecessary for this bounded scope.

The extra workflow schema leaves core project format 0.1.0 unchanged. Existing archives remain readable, while regenerated reports use the current renderer. Input hashes are neither anonymization nor authenticated provenance. Draft warnings and download preparation do not guarantee durable storage. Independent scientific evaluation and external researcher usability review remain pending.
