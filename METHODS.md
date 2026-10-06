# Methods development record

## Representation and reasoning

Researchers explicitly supply analysis, claim, category, support, context, and design. Immutable records retain control class, level, behavior, failure interpretation, uncertainty, privacy, evidence, and provenance. Method descriptions are unrestricted rather than domain dispatch. A rule flags causal claims whose support is associational, comparative, descriptive, predictive, or statistical.

The reference baseline specifies known-signal positive and signal-absent negative technical references, with abstention from unsupported biological selection. The default reasoner adds conditional specifications based on textual operation cues, supplied categories, and design fields. Cues and findings remain inspectable, provisional, and versioned; rules cannot establish actual design or biological relevance. Literal local description drafts preserve missing fields for researcher confirmation. See [the design rules](docs/DESIGN_RULES.md).

Optional Messages-compatible providers produce constrained proposals from selected public fields, attached to one known claim. Citation and verification fields are unavailable to proposals. No hosted model was evaluated.

## Evidence and review

Adapters use the official [Europe PMC service](https://europepmc.org/developers) and [Crossref API](https://github.com/CrossRef/rest-api-doc/blob/master/README.md). Metadata, aliases, time, licensing limitations, and response hashes are retained. Connected identifier records are consolidated. Identity remains separate from entailment and context.

Researchers supply local source text, a short excerpt and locator, an exact control statement, relation, rationale, source context, and limitations. Software checks excerpt presence and references; humans attest entailment. Normalized context comparison preserves unknowns and differing text without resolving synonyms. Both exact statements must have support with matching supplied context and no contradiction for workflow promotion. Receipts are not authenticated scientific proof.

## Numerical procedures

The effect is mean(group 1) minus mean(group 0), using `math.fsum`. Prespecified reference rules compare absolute effect error to a tolerance recorded before execution. Inferential outputs receive no automatic scientific PASS or FAIL.

Permutation tests enumerate all assignments up to 5,000; otherwise seeded sampled assignments use `(extreme + 1) / (draws + 1)`, following the nonzero Monte Carlo correction described by [Phipson and Smyth](https://pubmed.ncbi.nlm.nih.gov/21044043/). Two-sided tails compare absolute effects with a `1e-12` relative tolerance and zero absolute tolerance, preserving measurement-scale invariance. Exchangeability requires independent justification. Exact small tests are discrete, and nonsignificance does not establish equivalence or a biological negative.

Within-group bootstrap resampling yields percentile intervals with linear interpolation, following the general [NIST description](https://www.itl.nist.gov/div898/software/dataplot/refman1/auxillar/bootplot.htm). Small-sample coverage remains unestablished. Clustered, adjusted, sequential, and specialist primary analyses require other adapters.

The complete-pair adapter calculates the mean within-pair difference. It independently flips each pair difference, enumerating all 2^n assignments when at most 5,000; larger inputs use the stated seeded plus-one Monte Carlo convention. The absolute-tail definition is explicit and may differ from twice the smaller one-sided tail. [SciPy's permutation documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html) describes this paired swap/sign-flip construction. Pair differences must be independent and sign-invariant under the tested null; zero mean alone is insufficient. The paired percentile bootstrap resamples complete-pair indices, equivalent to resampling their differences for this statistic, as in [SciPy's paired bootstrap description](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html). Controlomics implements these narrow procedures with the standard library; SciPy is not a dependency. Population coverage and general scientific applicability were not established.

Packages retain fixed code, configuration, assumptions, seeds, environment, hashes, schemas, and a planned project snapshot. Results record observed versions and input hashes. Reproduction requires compatible retained artifacts; seeds alone do not guarantee identical output across changing algorithms or environments. See [Python reproducibility notes](https://docs.python.org/3/library/random.html#notes-on-reproducibility).

## Development evaluation

Synthetic provider and source fixtures test software gates. The initial identity run resolved two public papers through two providers without assessing entailment. Six manually specified cases test planted software findings. A seeded 100-trial independent Gaussian experiment checks the exact permutation adapter under null and shifted inputs. Observations are in [VALIDATION.md](VALIDATION.md).

The current identity run resolves four public papers through two providers. Six explicit development scenarios separately compare reference and design-rule outputs against supplied review-question codes. Unassessed judgment sheets yield no recommendation-quality or evidence-accuracy score. Evaluation tools calculate conditional precision, reference and critical recall, unsupported rates, finding-code metrics, execution success, abstention, evidence-layer accuracy, optional binary quadratic scores, and paired nominal agreement. See [definitions and denominators](docs/EVALUATION.md). The local workbench records actual supplied judgments with an explicit reviewer, declared origin, attestation, and snapshot hashes. Dataset references and predictions are retained. These tools do not create independent annotations.

No independent expert annotation, biological experiment, domain-held-out agent evaluation, or hosted-model comparison was performed. The development reference/design comparison is a software ablation, not a scientific validation study. Development observations do not support a validated domain-general control-generation claim.
