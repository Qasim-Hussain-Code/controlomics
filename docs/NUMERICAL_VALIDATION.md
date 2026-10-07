# Numerical validation findings

Completed locally on 2026-10-07, Asia/Taipei, for Controlomics 0.6.0.dev0. This checks numerical implementation against independently maintained software and measures behavior in predefined synthetic populations. It is not an independently conducted expert study, biological experiment, or validation of control selection.

## Frozen design and environment

[The local protocol](validation/numerical_protocol.json) was frozen before computing outcomes. It fixes source SHA-256 values, seeds, comparisons, seven simulation scenarios, sample sizes, resampling settings, and analysis. It is a local freeze, not a public preregistration or authenticated independent audit. The initial NumPy 2.4.0 selection was replaced with non-yanked 2.4.6 before any comparison or simulation outcomes. No outcome-dependent change was made to the final protocol.

The application used CPython 3.14.0 and its existing standard-library numerical implementation. An isolated optional environment used NumPy 2.4.6 and SciPy 1.18.1. [The environment record](validation/reference_environment_checks.json) retains versions, wheel hashes, dependency-resolution history, and the observed 200.7 MB reference-environment size. Pydantic remains the sole application runtime dependency. Downloads concerned public documentation and package wheels; no research record or numeric input was transmitted.

## Independent reference calculations

All 896 scalar comparisons matched within the prespecified absolute and relative tolerances of 1e-12. The 128 synthetic cases comprise 64 independent-group cases and 64 complete-pair cases, including unequal independent-group sizes, ties, constant shifts, and all-zero inputs. Each case compares effect, absolute-tail probability, number of exact assignments, null mean, null population standard deviation, and two percentile-bootstrap endpoints. Group sizes range from two to five and bootstrap comparisons use 199 draws with requested coverage 0.90. [Every observed comparison is retained](validation/numerical_checks.json).

SciPy supplied exact permutation distributions. Controlomics's declared two-sided probability counts absolute effects at least as large as the observed effect. SciPy's native two-sided result doubles the smaller one-sided tail. The native value differed in 36 cases; those differences are preserved and were expected from the definitions. The reference explicitly aligns the absolute-tail definition rather than claiming the native outputs are identical. [SciPy permutation documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html).

The bootstrap comparison specifies the percentile method and gives SciPy the same explicit resampling indices used by Controlomics, including whole-pair indices. This isolates endpoint computation; it does not test equivalence between random-number generators or compare against SciPy's default BCa method. [SciPy bootstrap documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html).

These comparisons cover ordinary bounded synthetic inputs and exact permutation enumeration. They do not establish universal floating-point equivalence, Monte Carlo stream equivalence, exchangeability, sign invariance, or performance on real scientific data. Existing software regressions separately check extreme numerical scales and rejected unrepresentable effects.

## Prespecified simulation observations

Each row uses 1,000 trials. Normal inputs have mean zero and variance one; Laplace inputs are the difference of two independent rate-one exponential draws, with variance two. Independent scenarios draw separate units for both groups. Paired scenarios draw independent within-pair differences. A shift of one is added to group one or to every paired difference, with the same underlying inputs retained for each null/shift comparison. Resampling uses 499 draws where enumeration is unavailable; all intervals use 499 bootstrap draws and requested coverage 0.95. Rejection means p <= 0.05; coverage means that the interval contains the known null effect zero.

| Synthetic scenario | Units per group or pairs | Permutation calculation | Null rejections / 1,000 | Shifted rejections / 1,000 | Null interval coverage / 1,000 |
| --- | --- | --- | --- | --- | --- |
| Independent normal | 4 per group | Exact, 70 assignments | 23 (2.3%) | 139 (13.9%) | 854 (85.4%) |
| Independent normal | 8 per group | Monte Carlo, 499 draws | 44 (4.4%) | 463 (46.3%) | 924 (92.4%) |
| Independent Laplace | 4 per group | Exact, 70 assignments | 13 (1.3%) | 109 (10.9%) | 849 (84.9%) |
| Paired normal | 3 pairs | Exact, 8 assignments | 0 (0.0%) | 0 (0.0%) | 741 (74.1%) |
| Paired normal | 8 pairs | Exact, 256 assignments | 55 (5.5%) | 665 (66.5%) | 867 (86.7%) |
| Paired normal | 20 pairs | Monte Carlo, 499 draws | 41 (4.1%) | 986 (98.6%) | 939 (93.9%) |
| Paired Laplace | 8 pairs | Exact, 256 assignments | 44 (4.4%) | 509 (50.9%) | 868 (86.8%) |

The machine-readable record reports a descriptive Wilson 95% interval for every rate. No simultaneous confidence claim or calibration pass threshold was specified. The 7,000 trials concern these particular synthetic populations, sample sizes, seeds, and procedures.

The requested 95% percentile intervals covered the truth in 74.1% to 93.9% of trials. The corresponding Wilson intervals were approximately 71.3% to 76.7% for three normal pairs and 92.2% to 95.2% for twenty normal pairs. These findings expose small-sample undercoverage; a requested coverage value is not a demonstrated population guarantee. The algorithms, seeds, and records were retained rather than tuned to remove unfavorable observations. General population coverage remains unestablished.

For three pairs, the smallest absolute-tail probability is 2/8 = 0.25. Consequently this exact procedure cannot reject at 0.05, including after the injected shift. Zero rejections are a discreteness limitation, not evidence of no effect. With four independent units per group and continuous inputs, only the two completely separated assignments among 70 can reject at 0.05. The theoretical null rejection probability is therefore 2/70, approximately 2.86%, rather than 5%.

The Laplace four-per-group run's 13/1,000 rejection rate is lower than that 2/70 probability, and its descriptive Wilson interval, approximately 0.76% to 2.21%, does not include 2/70. This fixed-seed observation is retained without reseeding or excluding the row. A separately labeled [post-hoc analytical diagnostic](validation/analytic_diagnostics.json) counted strict group separation directly on the original seeded inputs, without calling the permutation implementation. It reproduced both four-per-group rejection counts, 23 and 13. That check addresses the rejection-event calculation; it does not turn this unusually low realization into a calibration guarantee.

The interface and standalone report label the setting as requested coverage and retain the poor-coverage warning. [A targeted browser check](validation/coverage_labels_ui_checks.json) verifies these labels against an actual synthetic result. All inferential outcomes remain INDETERMINATE. No biological PASS, FAIL, expert accuracy score, or domain-general agent claim follows from these computations.

## Local reproduction

The retained study used an ignored environment at `local_projects/validation/reference_env/`; source downloads do not include it. Create a separate environment on a compatible Windows CPython 3.14 installation:

```powershell
.\.venv\Scripts\python.exe -m venv local_projects/validation/reference_env
.\local_projects\validation\reference_env\Scripts\python.exe -m pip install --only-binary=:all: -r requirements-validation.lock
```

Package installation requests public packages from the configured index. The calculation scripts perform no network request and accept no primary research dataset. Keep the retained protocol and source files byte-identical; Git's LF attributes preserve the frozen source hashes. Run against the retained protocol, writing a separate repetition record:

```powershell
.\.venv\Scripts\python.exe scripts/run_numerical_validation.py --protocol docs/validation/numerical_protocol.json --reference-python local_projects/validation/reference_env/Scripts/python.exe --output local_projects/validation/numerical_repetition.json
```

If methods, dependencies, or sources change, retain this run and define a new protocol before computing new outcomes. `--freeze` refuses to replace an existing protocol. A changed algorithm needs a new evaluation; matching this record is not a promise that every future environment produces byte-identical output.

## Remaining scientific study

The local [readiness observation](validation/study_readiness.json) finds six DEVELOPMENT cases, zero TEST cases, and no declared independent expert judgment sheets. The [expert-study protocol](INDEPENDENT_VALIDATION_PROTOCOL.md) specifies proposed real-case curation, blinded independent review, source partitions, adjudication, sampling, comparisons, uncertainty, and local privacy. Real cases and genuinely independent annotations are required to perform that study. Neither synthetic cases nor the software that proposes controls can supply their own independent scientific reference answers.
