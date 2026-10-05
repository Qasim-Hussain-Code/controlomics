# Scientific specification

## Scope and research question

Controlomics investigates whether evidence-grounded reasoning can specify scientifically appropriate positive and negative controls for heterogeneous computational biology claims. General framework design, domain-specific evaluation, and demonstrated generalization are distinct. None implies another.

The software surrounds the primary analysis. It does not require reproducing that analysis. Its input must describe the scientific question, method, biological context, analytical design, observed result, claimed interpretation, and assumptions connecting the result to the interpretation. Missing information remains explicit.

A positive control asks whether an approach can recover a relevant known signal. A negative control asks whether an appropriate absence or irrelevant entity avoids the claimed signal. A statistical null describes a distribution under specified assumptions. A null procedure is not necessarily an experimentally inactive biological entity. Control class and scientific level are separate axes of the versioned ontology.

## Initial scientific records

| Record | Scientific role |
| --- | --- |
| AnalysisContext | Question, methods, result, design, context, and coverage uncertainty |
| ScientificClaim | Statement, claim category, computational support, assumptions, and origin |
| EvidenceItem | Source identifiers, metadata, retrieval, licensing, context, and identity check |
| ControlCandidate | Claim tested, positive or negative class, rationale, expected behavior, failure meaning, and uncertainty |
| VerifiedControl | Reviewed evidence state, entailment links, context assessment, and verification receipt |
| ExecutionPlan | Inputs, locality, software, parameters, randomness, output version, and optional decision rule |
| ControlResult | Execution state, finite measures, uncertainty, input hashes, software, and rule-based interpretation |
| AuditOutcome | Calibrated assessment with referenced evidence or results and explicit limitations |
| ProvenanceRecord | Timestamped action, record references, versions, hashes, and optional model metadata |

Additional records describe claim relationships, privacy policy, biological context, analytical design, evidence links, and the project manifest. The schemas require a researcher to preserve distinctions rather than letting unconstrained prose become a scientific verdict.

## Evidence and interpretation

Evidence states are EVIDENCE_BACKED, METHOD_BASED, AGENT_PROPOSED, UNVERIFIED, CONFLICTING_EVIDENCE, and INSUFFICIENT_EVIDENCE. Candidate generation cannot silently promote a recommendation. Publication identity and statement support require different receipts. Licensing may limit what source content can be retained or reported.

Context review should consider organism, strain, cell type, tissue, disease, experimental condition, target, assay, method, modality, scale, intervention, time, reference database, and software assumptions where relevant. Unknown values are not matches. Known mismatches must be visible. Partial compatibility requires explicit limitations. The initial schema checks recorded comparisons, not their truth or completeness.

Claims may be descriptive, associational, comparative, predictive, statistical, functional, mechanistic, or causal. A causal claim paired with noncausal computational support produces an interpretation warning. This warns about the stated evidence basis; it does not implement causal inference or judge whether a full causal design is adequate.

Priority is ESSENTIAL, RECOMMENDED, or EXPLORATORY with an inspectable rationale. No numerical truth score is defined. Final assessments use ROBUST, SUPPORTED, CONDITIONAL, FRAGILE, CONTROL_FAILURE, INSUFFICIENT_EVIDENCE, or UNRESOLVED. A passed control does not prove the original claim, and a failed control may reflect control design or execution problems.

## Execution and falsifiability

Numerical quantities must be computed by deterministic software, with recorded seeds when randomness is appropriate. Execution records represent estimates, intervals, null distributions, versions, and input hashes without requiring a binary decision. PASS or FAIL requires a decision rule specified before execution began, a completed result, and an interpretation. A syntactically correct decision rule still requires scientific justification.

The current version specifies execution records but performs no calculations or execution. No synthetic fixture result may be described as an observed Controlomics result.

## Unresolved scientific questions

- What minimum context suffices to propose a useful control without leaking sensitive information?
- Which controls are essential across methods, and which require domain-specific review?
- How should conflicting sources, study quality, retractions, and incomplete access affect acceptance?
- How reliably can entailment be assessed when abstracts omit important context?
- Which context mismatches permit a conditional recommendation?
- How can benchmark annotation distinguish biological negatives from statistical nulls consistently?
- What sampling and exchangeability assumptions justify each null procedure?
- Which baseline and domain-held-out designs fairly test generalization?

These questions require literature review, expert annotation, and empirical evaluation. The schemas alone cannot answer them.
