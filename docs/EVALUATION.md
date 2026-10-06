# Evaluation records and protocol

The evaluation tools calculate metrics from caller-supplied cases, predictions, and annotations. They do not supply independent scientific ground truth. No expert control judgments, human comparison, hosted-model performance, or biological validation have been performed for the included cases.

## Included development materials

`examples/benchmark.dataset.json` contains six hypothetical operation and design scenarios. Three scenarios identify public method papers as motivation. All cases are DEVELOPMENT; none constitutes a held-out domain or test set. Reference controls and expected finding codes are marked DEVELOPMENT_FIXTURE.

Two offline runs are provided: the original two-reference baseline and the default design reasoner. Their `*.unassessed.json` bundles contain null appropriateness and unsupported judgments. Recommendation quality and evidence-layer accuracy are therefore unavailable. The observed development finding-code comparison is in [design_development_evaluation.json](validation/design_development_evaluation.json). It compares implementations against their supplied development expectations and does not establish independent generalization.

Recreate these records locally:

```powershell
.\.venv\Scripts\python.exe scripts/generate_benchmark_dataset.py
.\.venv\Scripts\controlomics.exe run-dataset examples/benchmark.dataset.json --reasoner design --output local_projects/predictions.json
.\.venv\Scripts\controlomics.exe annotation-template examples/benchmark.dataset.json local_projects/predictions.json --output local_projects/unassessed.json
.\.venv\Scripts\controlomics.exe evaluate local_projects/unassessed.json --output local_projects/evaluation.json
```

In the Evaluation tab, open a bundle, choose a declared partition, and calculate its metrics. All computation remains local. Export the report before closing the page. The CLI supports DEVELOPMENT, VALIDATION, or TEST filtering. A partition without cases is rejected rather than reported as zero performance.

## Record contracts

Structural schemas are in `schemas/workflow/0.1.0`. Python validation additionally enforces reference integrity, partition isolation, and annotation-state rules. Each dataset contains at most 200 cases. Each case identifies its partition, source group, optional publication identifiers, explicit intake for runnable baselines, reference controls, and expected finding codes when assessed.

A prediction run covers every case exactly once, including explicit full abstentions. Each recommendation has an ID, class, level, description, and optional probability of appropriateness. Findings and execution states are separate observations. A recommendation judgment references the exact case and recommendation, states appropriate or inappropriate or uncertain, independently states unsupported or supported or uncertain, and identifies any appropriate reference matches. Evidence decisions separately assess citation identity, statement entailment, and context compatibility.

Origins are UNASSESSED, DEVELOPMENT_FIXTURE, and EXPERT_ATTESTATION. UNASSESSED bundles cannot assert recommendation or evidence reference judgments. An expert origin requires an explicitly supplied annotator name, which remains an unauthenticated attestation. Do not change origin or fill judgments merely to produce a score. Reference origin and judgment origin remain separately visible in reports.

Source groups and shared normalized publication identifiers cannot cross partitions. This check cannot recognize every semantic duplicate, related cohort, disjoint DOI/PMID alias, or potential training contamination. Curators must establish and review these relationships before assigning splits.

## Denominators

| Metric | Included denominator |
| --- | --- |
| Recommendation precision | Recommendations with definite appropriateness judgments |
| Reference and critical-control recall | Supplied reference controls, or essential references, in completely judged cases |
| Unsupported recommendation rate | Recommendations with definite unsupported judgments |
| Finding recall and precision | Expected and reported codes in cases with supplied finding annotations |
| Execution success | Completed plus failed attempts; blocked and not-run states counted separately |
| Abstention rate | All selected cases; only explicit full abstentions enter the numerator |
| Each evidence-layer accuracy | Definite binary reference decisions for that layer |
| Binary quadratic score | Supplied appropriateness probabilities paired with definite judgments |

Unknown and missing judgments are excluded from definite-decision denominators and counted in coverage. Incompletely judged cases are excluded from reference recall; explicitly abstained cases with assessed references remain in recall and contribute uncovered references. Distinct matches prevent duplicated recommendations from increasing coverage. Always inspect coverage alongside the conditional metrics, since missing judgments can make a narrow score misleading.

A zero denominator yields null, displayed as Unavailable. Descriptive Wilson intervals accompany ratios. Correlated cases, references, recommendations, and repeated source material violate an independent-binomial interpretation; scientific uncertainty requires a separately specified design.

The binary quadratic score uses mean `(p-y)^2` on the single-probability 0-to-1 convention. The original [Brier paper, 1950](https://journals.ametsoc.org/doi/abs/10.1175/1520-0493%281950%29078%3C0001%3AVOFEIT%3E2.0.CO%3B2) motivates quadratic probability scoring, with a different multicategory scaling. This scalar score alone does not demonstrate calibration. Local baselines supply no appropriateness probabilities.

## Annotation agreement

Independent annotation sheets must retain the same dataset and predictions. Compare their definite and uncertain nominal appropriateness labels with:

```powershell
.\.venv\Scripts\controlomics.exe compare-annotations local_projects/reviewer_a.json local_projects/reviewer_b.json --output local_projects/agreement.json
```

The report gives paired and missing units, observed agreement, marginal expected agreement, and Cohen's kappa. UNCERTAIN is a nominal category; a missing judgment is not agreement. Degenerate marginals yield no kappa. See [Cohen, 1960](https://journals.sagepub.com/doi/abs/10.1177/001316446002000104). Agreement does not establish correctness, independent recruitment, or authenticated reviewers.

## Independent research still required

Predefine the target populations, outcomes, annotation rubric, sample sizes, source and domain partitions, adjudication, and statistical analysis before evaluating models. Experts should judge exact claims, control roles, biological applicability, contradictory evidence, missing critical controls, and negative cases without treating one model's answer as sole truth. Retain independent sheets and adjudicated records separately.

Compare the reference baseline, method checklists, retrieval-only reasoning, and configured models on the same independently sourced cases. Specify retrieval, representation, review, and execution ablations before comparison. Report failures, abstentions, unassessed recommendations, retrieval availability, execution exclusions, and uncertainty. The included software development comparison is an initial operational check, not this research study.
