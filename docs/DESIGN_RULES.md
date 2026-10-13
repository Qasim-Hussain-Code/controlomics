# Local design reasoning

The default `local_design_reasoner_v1` derives provisional specifications from analytical operations and explicitly supplied claim categories. The inspectable profile uses `design_rules.v0.1`. It does not identify biological entities or establish that a design, control, or publication is scientifically appropriate.

## Interpretation

The local description parser preserves labelled fields or explicit phrases. Missing results, methods, categories, and support remain missing. Suggestions about claim categories do not determine computational support. Review the draft in Analysis and choose both categories before creating a project.

Rules inspect descriptions, methods, analysis assumptions, claim assumptions, partition descriptions, independence assumptions, and covariates. They recognize lexical cues for prediction, comparison, association, ranking, overlap, similarity, repeated units, temporal dependence, nuisance structure, and causal interpretation. Rank-test wording is distinguished from ranking an entity list; genetically predicted quantities do not alone imply predictive-model evaluation. A cue includes the text or supplied category that caused it. Negation, ambiguous wording, synonyms, and unstated design features can produce missed or inappropriate cues. Findings are review questions unless they concern an explicitly missing field or a declared support mismatch.

## Specifications

| Operation or assumption | Added specification | Scientific limit |
| --- | --- | --- |
| Prediction | Training-partition leakage and label-information null challenges | Untouched evaluation, unit-level partitioning, and exchangeability require justification |
| Comparison or association | Design-preserving contrast null | A null is separate from a biological negative |
| Repeated, nested, or temporal observations | Independent-unit sensitivity analysis | Aggregation, dependence models, and pairing may change the estimand |
| Batch or nuisance structure | Nuisance-structure challenge | Correction alone does not establish identifiability |
| Set overlap | Matched-background enrichment challenge | Eligibility, annotation versions, multiplicity, and dependence matter |
| Ranking or similarity | Matched reference discrimination challenge | Biological references need separate evidence review |
| Causal or mechanistic interpretation | Alternative-explanation falsification | Observational wording cannot establish an intervention or causation |

All profiles retain the two generic technical reference specifications and general heuristic limitations. The operation-unrecognized question, `operation_uncertain`, appears only when neither text nor a supplied category produces any cue. A causal, mechanistic, predictive, comparative, or associational category alone can suppress that question and trigger conditional design challenges even when the analytical operation is unspecified. This does not establish the operation; review missing method information explicitly. Priorities indicate provisional assumption relevance, not measured scientific importance. `analyze --reasoner reference` selects the original two-reference proposal baseline. The dataset runner also uses that baseline's limited finding codes for the development ablation. A project audit still runs the full conservative design diagnostics regardless of proposal reasoner, so it does not omit a known design concern merely because simpler proposals were requested.

The method gate reviews technical and statistical specifications with a stated basis. Newly created built-in local proposals can pass that gate during their creation action. Existing hosted and researcher-drafted candidates require explicit method review; adding a claim, repeating analysis, or loading a saved project does not review them. METHOD_BASED does not mean experimentally validated, applicable to the current design, or executable with the installed adapter. The three fixed numeric procedures support only technical positive and negative reference specifications with declared independent-unit two-group inputs. Design challenges and biological specifications require applicable computation in the researcher's environment; this runner rejects their attachment.

## Scientific motivation

Feature selection and tuning using evaluation information can bias prediction assessment, motivating a question about where each fitted step occurs. See [Varma and Simon, 2006](https://link.springer.com/article/10.1186/1471-2105-7-91). Nested observations motivate checking the replication unit; the included scenario does not endorse one universal analysis over competing methods. See [Zimmerman and colleagues, 2021](https://www.nature.com/articles/s41467-021-21038-1). Set-based analysis motivates inspecting the tested universe and null assumptions. See [Subramanian and colleagues, 2005](https://pubmed.ncbi.nlm.nih.gov/16199517/).

These papers motivate development scenarios. They are not statement-entailment receipts for generated controls. The six scenarios and expected review-question codes were constructed during software development, not independently annotated by experts. Agreement with their expected codes is not scientific diagnosis accuracy.

## Claims and revisions

Additional claims retain their own categories, support, assumptions, controls, and audit outcomes. Local proposals populate only claims without existing controls. Hosted proposals target one selected claim and remain unreviewed. This prevents one hosted response being copied onto several claims.

A researcher can create or edit an unreviewed candidate. Saving a specification never promotes its evidence state. Reviewed specifications and execution-bound candidates cannot be edited through that action. Evidence re-review instead requires the SHA-256 of the current reviewed snapshot and records the superseded hash. Preserve exported snapshots to inspect the prior contents; a hash is not the contents or an authenticated review history.
