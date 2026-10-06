# ADR 0003: Inspectable design reasoning and annotation-dependent evaluation

Date: 2026-10-06. Status: implemented for the local research alpha.

## Problem

Two generic technical references did not expose operation-specific assumptions. A six-case software harness could not represent independently annotated control quality or distinguish absent judgments from measured performance. JSON-only review entry also made exact statement review harder to inspect.

## Alternatives considered

Hardcoded biological control lists would require context-specific evidence and independent validation. A large locally hosted model would add unsupported resource demands. Assigning expert labels or scientific performance numbers during implementation would fabricate evaluation. Depending entirely on hosted reasoning would prevent a free offline workflow.

## Decision

Add transparent local operation rules, a literal description draft, researcher candidate editing, per-claim proposals, and direct source-review forms. Maintain the two-reference baseline as an explicit simpler alternative. Add typed datasets, prediction runs, unassessed annotation templates, partition checks, metric arithmetic, and paired agreement comparison. Keep biological and hosted-model validation pending.

## Scientific rationale

Rules expose the assumptions being challenged and their textual basis. They do not identify validated biological controls. Review gates remain separate from proposal and computation. Evaluation depends on supplied reference annotations; incomplete judgments cannot silently become successes. Development finding-code agreement is qualified as implementation behavior.

## Technical rationale

The changes use the existing Python package, Pydantic, standard library, and static browser assets. The project and ontology stay at 0.1.0; separate workflow schemas describe auxiliary inputs. Existing examples remain readable. Local baseline comparisons require no model key, database, or additional runtime dependency.

## Privacy implications

Description interpretation, evaluation, and source review process local snapshots. Full source text is discarded after the transient review and omitted from project/report output. Outbound fields remain explicitly minimized and approved. Additional claims do not implicitly enter model requests.

## Security implications

Untrusted browser JSON passes the duplicate-key-aware parser before use. Hosted completion requires one known target claim before network activity. Candidate edits cannot erase reviewed specifications. Re-review requires the current snapshot hash and retains the superseded hash in provenance. These are consistency checks, not authenticated identities or cryptographic attestation.

## Limitations

Lexical rules can miss wording, negation, dependencies, and scientific context. Method review does not establish applicability. Scientific labels and names can be falsely supplied. Hash-only revision provenance cannot reconstruct old content without retained snapshots. Normalized identifiers do not resolve all cross-partition scientific overlap. Numerical execution remains limited to the installed adapter.

## Conditions for reconsideration

Revisit rules and prioritization after independent expert evaluation; add authenticated review only with a defined identity and access model. Introduce specialist execution adapters only with independent scientific specifications and validation. Evaluate hosted providers when configured public context, models, independent annotations, and research resources are available. Revise formats through explicit versioning if those changes require new project records.
