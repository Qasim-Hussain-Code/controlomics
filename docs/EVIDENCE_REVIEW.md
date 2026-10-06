# Evidence review record

Use a `HumanReview` record only after a real researcher has inspected the relevant publication and source text. Do not turn model judgment into a human attestation. Retain appropriate access and licensing rights for locally processed source text. No review record for an actual biological recommendation is supplied by the development examples.

The record contains `control_id`, `reviewer`, `statements`, and `limitations`. Each statement review includes `evidence_id`, the exact `statement`, `relationship` (SUPPORTS, CONTRADICTS, or UNCERTAIN), locally supplied `source_text`, a short `excerpt` occurring in that text, a `locator`, a scientific `rationale`, and a structured `source_context`.

Copy the exact `scientific_rationale` and `expected_behavior` strings from the candidate into separate statement entries. Identify the retrieved publication record by its existing evidence ID. The statement-support assessment is a human judgment. The software checks excerpt presence and record consistency, then records the source-text hash; it does not establish entailment automatically or export the source text into the report.

Context fields follow `BiologicalContext`: organism, strain, cell type, tissue, disease state, experimental condition, target, assay, computational method, modality, scale, intervention, time point, reference database, and software assumptions. Populate what the source actually establishes. Do not infer missing tissue or species from title keywords. Exact normalized comparison is used initially; semantic mismatches and applicability need scientific review.

Apply with `controlomics review PROJECT REVIEW.json --output UPDATED.json`, or import the JSON in the Evidence tab. Full support and matching supplied context can yield EVIDENCE_BACKED. Both support and contradiction yield CONFLICTING_EVIDENCE. Incomplete, mismatched, or unsupported submissions yield INSUFFICIENT_EVIDENCE. A missing identity, unrelated statement, or excerpt absent from supplied text is rejected.

This is an attestation workflow. Source text and reviewer identity supplied by a caller can be false. Stored receipts and hashes are not signatures, verified human identities, evidence-quality scores, or proof that independent review occurred. Expert annotation and authentication requirements remain unresolved for public scientific deployment.

The interface also offers Review evidence on each control when verified publication identities are available. It displays the exact statements and leaves the researcher name and attestation empty. Enter separate assessments for rationale and expected behavior; the form does not invent source context or select SUPPORTS automatically.

To replace an existing reviewed record, supply `supersedes_review_sha256` equal to the current reviewed snapshot hash. The interface obtains this hash locally and requires an explicit replacement choice. The previous hash is recorded in provenance. Retain old project exports to inspect prior content, including contradictory evidence; the hash alone cannot reconstruct it. Re-review can reduce the evidence state and does not alter the specified rationale or expected behavior.

Later retrieval of the same publication retains the earlier verified identity snapshot that prior statement receipts depend on. Later network responses and hashes remain in the ledger. This preserves temporal consistency without turning a later retrieval into proof of the earlier review.
