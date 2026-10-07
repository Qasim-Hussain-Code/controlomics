"""Optional SciPy oracle for explicitly synthetic local numeric comparisons."""

import json
import math
import platform
import sys

import numpy as np
import scipy
from scipy.stats import bootstrap, permutation_test


class FixedIndices(np.random.Generator):
    """Give SciPy the prespecified resampling indices, not a different RNG stream."""

    def __init__(self, indices):
        super().__init__(np.random.PCG64(0))
        self.indices = list(indices)

    def integers(self, low, high=None, size=None, dtype=np.int64, endpoint=False):
        if not self.indices or low != 0 or endpoint or high is None:
            raise ValueError("unexpected reference resampling request")
        value = np.asarray(self.indices.pop(0), dtype=dtype)
        if value.shape != tuple(size) or value.min() < low or value.max() >= high:
            raise ValueError("reference resampling indices do not match the sample")
        return value


def difference(left, right, axis=-1):
    return np.mean(right, axis=axis) - np.mean(left, axis=axis)


def reference_case(case):
    left, right = np.asarray(case['left'], dtype=float), np.asarray(case['right'], dtype=float)
    if not 2 <= len(left) <= 6 or not 2 <= len(right) <= 6 or not np.isfinite(left).all() or not np.isfinite(right).all():
        raise ValueError("reference cases require bounded finite synthetic arrays")
    paired = case['adapter'] == 'PAIRED_DIFFERENCE'
    if paired and len(left) != len(right) or case['adapter'] not in ('PAIRED_DIFFERENCE', 'INDEPENDENT_REFERENCE'):
        raise ValueError("invalid reference adapter or pairing")
    if paired:
        # A one-sample paired permutation independently flips each difference.
        perm = permutation_test((right-left,), np.mean, permutation_type='samples',
            vectorized=True, n_resamples=np.inf, alternative='two-sided', batch=256)
    else:
        perm = permutation_test((left, right), difference, permutation_type='independent',
            vectorized=True, n_resamples=np.inf, alternative='two-sided', batch=256)
    observed = float(perm.statistic)
    null = np.asarray(perm.null_distribution)
    # SciPy's native two-sided convention is twice the smaller one-sided tail.
    # Controlomics specifies an absolute tail, so align definitions explicitly.
    extreme = (np.abs(null) >= abs(observed)) | np.isclose(np.abs(null), abs(observed), rtol=1e-12, atol=0)
    rng = FixedIndices(case['indices'])
    boot = bootstrap((left, right), difference, paired=paired, vectorized=True,
        n_resamples=case['draws'], batch=case['draws'], confidence_level=case['coverage'], method='percentile', rng=rng)
    if rng.indices:
        raise ValueError("not all prescribed resampling indices were consumed")
    return {'case_id': case['case_id'], 'effect': observed, 'p_absolute_tail': float(np.mean(extreme)),
        'p_scipy_native_two_sided': float(perm.pvalue), 'draws': int(null.size),
        'null_mean': float(np.mean(null)), 'null_sd_population': float(np.std(null, ddof=0)),
        'bootstrap_lower': float(boot.confidence_interval.low), 'bootstrap_upper': float(boot.confidence_interval.high)}


def main():
    raw = sys.stdin.buffer.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError("reference request exceeds its limit")
    payload = json.loads(raw)
    if payload['format'] != 'controlomics.synthetic_numeric_reference.v0.1' or not 1 <= len(payload['cases']) <= 128:
        raise ValueError("invalid reference request")
    records = [reference_case(case) for case in payload['cases']]
    if not all(math.isfinite(value) for record in records for value in record.values() if isinstance(value, (int, float))):
        raise ValueError("nonfinite independent reference result")
    print(json.dumps({'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__, 'cases': records}, allow_nan=False))


if __name__ == '__main__':
    main()
