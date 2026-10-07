# Independent scientific validation protocol

Status: Proposed expert-study protocol, 2026-10-07, Asia/Taipei. Real cases, qualified independent reviewers, and a sampling frame for the intended population have not been supplied. No expert study or public preregistration is claimed.

The completed software checks and synthetic numerical experiments concern computation. The research claim still needs an independently curated study of whether proposed controls are appropriate for actual scientific questions. Independently maintained reference software can check numerical implementation; it cannot replace those reviewers or biological observations. Neutral benchmarking also requires attention to bias, fair parameter choices, and the study's stated purpose. [Weber and colleagues, 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6584985/).

## Target and sampling

The proposed primary outcome is complete coverage of independently specified essential controls per test case. A case scores one only when every essential reference is covered by an appropriate recommendation; full abstention scores zero. Cases with unresolved reference or recommendation judgments remain explicitly unresolved and cannot silently become successes. Report conservative bounds and annotation coverage alongside any complete-case estimate.

The planning target is 100 independent source groups with one primary case each, spread across five researcher-selected analysis families. For a binary case outcome, 100 independent observations give an approximate worst-case 95% precision of ten percentage points. This is a planning illustration, not a power calculation or a justification for correlated recommendations. Review feasibility, intended population, source dependence, and the primary comparison before adopting it. A separate annotation pilot can refine the rubric; its cases must not enter the final test set.

Use actual published or approved private analyses with traceable scientific question, method, sampling unit, context, observed result, claimed interpretation, and uncertainty. Include prespecified negative, ambiguous, unsupported, and abstention cases. Select cases using a recorded sampling frame, rather than choosing cases where Controlomics already performs well. Exclude the six development fixtures and semantic duplicates of tuning cases. Curators must resolve DOI/PMID aliases, common cohorts, related experiments, and source overlap before freezing partitions.

A held-out domain claim requires genuinely reserved analysis families and a recorded tuning history. Calling a case TEST does not prove that history. Hosted providers may have encountered public papers during training; record exposure uncertainty and avoid claiming contamination-free evaluation without evidence.

## Reference curation and review

At least two genuinely qualified reviewers should independently define appropriate controls from the source analysis before seeing system output. They must distinguish biological inactivity, mechanistic specificity, technical references, and statistical nulls. Record applicability, criticality, limitations, contradictory evidence, and source locators. A separate adjudicator should resolve disagreements while preserving the original sheets and explanations.

After reference curation, freeze the dataset and each prediction run. Compare the default design reasoner and reference baseline on the same cases, with their settings fixed. A researcher-specified method checklist and retrieval-only or hosted baselines may be added only after their procedures, configuration, cost, and privacy permissions are defined. Never fill their results with simulated expert answers.

For recommendation review, remove provider names and randomize presentation order using a privately retained mapping. Reviewers should supply appropriateness, unsupported status, and reference matches independently. Keep uncertain labels. Record actual expertise, roles, conflicts, independence declarations, and attestations in a protected local manifest. Distinct supplied names and checked attestations do not authenticate people or establish independence.

Assess citation identity, exact statement support, and biological context separately. A paper's existence cannot substitute for source entailment. Preserve contrary sources and inaccessible material. Do not infer biological control efficacy solely from a passed numeric reference or from agreement between reviewers.

## Analysis and interpretation

Report the primary case outcome, critical/reference recall, recommendation precision, unsupported rate, abstention, evidence-layer decisions, failures, exclusions, and missing judgments. State every denominator. Preserve per-case paired comparisons and source-group structure; do not treat correlated recommendations as independent cases. Use a predefined paired analysis and source-group resampling where appropriate. Report uncertainty rather than choosing a favorable result after seeing the data.

Keep independent reviewer agreement and adjudicated accuracy separate. A high agreement score does not prove correctness. Perform source/context review and sensitivity analyses for unresolved cases and sampling choices. Prespecify retrieval, representation, review, and execution ablations before generating their test predictions. Do not revise the tested algorithm using the frozen test outcomes; a revised algorithm needs a newly declared evaluation.

Completion means the actual study was performed, its records were checked, and its findings were reported, including unfavorable results. It does not imply that Controlomics passed every scientific criterion. Conclusions must remain restricted to the evaluated populations, providers, methods, evidence availability, and uncertainty.

## Local privacy and execution

Keep case data, source texts, reviewer identities, blinding mappings, permissions, and adjudication in ignored `local_projects/independent_study/` or another approved private directory. Use minimized analysis descriptions; raw primary datasets are not required for control-selection annotation. Full source texts remain local. Review exported excerpts and metadata before any separately authorized sharing. Hashes are equality fingerprints, not anonymization or authenticated provenance.

No public hosting, GitHub push, external recruitment message, private-data upload, or automatic hosted reasoning is authorized by this protocol. Public retrieval still uses the exact-payload approval boundary. Private reviewer packets must be delivered only through a separately authorized method.

The existing local tools provide dataset execution, blank annotations, metrics, and paired agreement:

```powershell
.\.venv\Scripts\controlomics.exe run-dataset local_projects/independent_study/dataset.json --reasoner design --output local_projects/independent_study/design.predictions.json
.\.venv\Scripts\controlomics.exe annotation-template local_projects/independent_study/dataset.json local_projects/independent_study/design.predictions.json --output local_projects/independent_study/design.unassessed.json
.\.venv\Scripts\controlomics.exe compare-annotations local_projects/independent_study/reviewer_a.json local_projects/independent_study/reviewer_b.json --output local_projects/independent_study/agreement.json
.\.venv\Scripts\controlomics.exe evaluate local_projects/independent_study/adjudicated.json --partition TEST --output local_projects/independent_study/evaluation.json
.\.venv\Scripts\python.exe scripts/check_study_readiness.py --bundle local_projects/independent_study/reviewer_a.json --bundle local_projects/independent_study/reviewer_b.json --output local_projects/independent_study/readiness.json
```

Run the readiness audit after real annotations are supplied, separately for each prediction run. Reviewer sheets in a single audit must retain identical dataset and prediction snapshots. Its default record minima follow the proposed 100-case/100-source-group plan. Adopt different minima only through a documented protocol revision. The audit checks metadata and coverage, omits private text and names, and cannot certify expertise, independent provenance, sampling validity, or scientific validity. Use [EVALUATION.md](EVALUATION.md) for record contracts and conditional metric definitions.

The remaining inputs are approved real case paths and provenance, actual independent expert annotations and expertise/independence declarations, retained adjudication, and the adopted sampling and analysis plan. These cannot be produced by relabeling the development fixtures or by having the proposing system grade itself.
