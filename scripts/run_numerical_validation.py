"""Freeze and run synthetic statistical validation, with optional SciPy references.

No clinical/biological input is accepted and no outbound request is performed.
This script does not provide independent expert control-selection judgments.
"""

import argparse
import hashlib
import json
import math
import platform
import random
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from controlomics import __version__
from controlomics.benchmark import wilson
from controlomics.statistics import bootstrap_difference, paired_bootstrap, paired_permutation, permutation_test

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = ('src/controlomics/statistics.py', 'scripts/scientific_reference.py', 'scripts/run_numerical_validation.py')
SCENARIOS = (
    ('independent_normal_n4', 'INDEPENDENT_REFERENCE', 'NORMAL', 4),
    ('independent_normal_n8', 'INDEPENDENT_REFERENCE', 'NORMAL', 8),
    ('independent_laplace_n4', 'INDEPENDENT_REFERENCE', 'LAPLACE', 4),
    ('paired_normal_n3', 'PAIRED_DIFFERENCE', 'NORMAL', 3),
    ('paired_normal_n8', 'PAIRED_DIFFERENCE', 'NORMAL', 8),
    ('paired_normal_n20', 'PAIRED_DIFFERENCE', 'NORMAL', 20),
    ('paired_laplace_n8', 'PAIRED_DIFFERENCE', 'LAPLACE', 8),
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8', newline='\n')


def freeze(path):
    if path.exists():
        raise ValueError('refusing to replace an existing frozen protocol')
    plan = {'format': 'controlomics.synthetic_numerical_protocol.v0.1', 'frozen_at': datetime.now(timezone.utc).isoformat(),
        'controlomics_version': __version__, 'seed': 20261007, 'reference_cases_per_adapter': 64,
        'reference_draws': 199, 'reference_coverage': 0.90, 'trials_per_scenario': 1000,
        'simulation_draws': 499, 'alpha': 0.05, 'simulation_coverage': 0.95, 'injected_shift': 1.0,
        'absolute_comparison_tolerance': 1e-12, 'relative_comparison_tolerance': 1e-12,
        'source_sha256': {name: digest((ROOT/name).read_bytes()) for name in SOURCE_FILES},
        'scenarios': [{'scenario_id': name, 'adapter': adapter, 'distribution': distribution, 'units_per_group_or_pairs': n} for name, adapter, distribution, n in SCENARIOS],
        'reference_method': 'Compare exact SciPy enumeration after explicit absolute-tail alignment; compare percentile bootstrap endpoints using identical explicit resampling indices. RNG-stream equivalence is not tested.',
        'analysis': 'Report every comparison and scenario. Estimate null rejection, shifted rejection and null bootstrap coverage with descriptive Wilson 95% intervals; no calibration pass threshold or biological verdict is assigned.',
        'scope': 'Synthetic computational validation only. Independently maintained software is the numeric comparator, not an independent reviewer or biological ground truth. No public preregistration or independent audit is claimed.'}
    write(path, plan)


def make_cases(plan):
    generator = random.Random(plan['seed'])
    cases = []
    for adapter in ('INDEPENDENT_REFERENCE', 'PAIRED_DIFFERENCE'):
        for index in range(plan['reference_cases_per_adapter']):
            n0 = 2 + index % 4
            n1 = n0 if adapter == 'PAIRED_DIFFERENCE' else 2 + (index // 4) % 4
            left = [generator.randint(-12, 12) / 2 for _ in range(n0)]
            right = [generator.randint(-12, 12) / 2 for _ in range(n1)]
            if index == 0:
                left, right = [0.0, 1.0], [2.0, 3.0]
            if index == 1:
                left, right = [1.0] * n0, [3.0] * n1
            if index == 2:
                left, right = [0.0] * n0, [0.0] * n1
            rng = random.Random(plan['seed'] + index)
            draws = plan['reference_draws']
            if adapter == 'PAIRED_DIFFERENCE':
                indices = [[[i for i in rng.choices(range(len(left)), k=len(left))] for _ in range(draws)]]
            else:
                rows = [(rng.choices(range(len(left)), k=len(left)), rng.choices(range(len(right)), k=len(right))) for _ in range(draws)]
                indices = [[row[column] for row in rows] for column in (0, 1)]
            cases.append({'case_id': adapter.lower() + '.' + str(index), 'adapter': adapter, 'left': left, 'right': right,
                'seed': plan['seed'] + index, 'draws': draws, 'coverage': plan['reference_coverage'], 'indices': indices})
    return cases


def comparisons(plan, python):
    cases = make_cases(plan)
    request = {'format': 'controlomics.synthetic_numeric_reference.v0.1', 'cases': cases}
    raw = json.dumps(request, allow_nan=False).encode('utf-8')
    oracle = subprocess.run([str(python), '-I', str(ROOT/'scripts/scientific_reference.py')], input=raw,
        capture_output=True, check=True, timeout=120)
    references = json.loads(oracle.stdout)
    if references['numpy'] != '2.4.6' or references['scipy'] != '1.18.1':
        raise ValueError('reference package versions differ from the frozen validation environment')
    records = []
    for case, reference in zip(cases, references['cases'], strict=True):
        left, right = case['left'], case['right']
        if case['adapter'] == 'PAIRED_DIFFERENCE':
            differences = [b-a for a, b in zip(left, right)]
            perm = paired_permutation(differences)
            boot = paired_bootstrap(differences, seed=case['seed'], draws=case['draws'], coverage=case['coverage'])
        else:
            values, labels = left+right, [0]*len(left)+[1]*len(right)
            perm = permutation_test(values, labels)
            boot = bootstrap_difference(values, labels, seed=case['seed'], draws=case['draws'], coverage=case['coverage'])
        actual = {'effect': perm['effect'], 'p_absolute_tail': perm['p_value'], 'draws': perm['draws'],
            'null_mean': perm['null_mean'], 'null_sd_population': perm['null_sd'], 'bootstrap_lower': boot['lower'], 'bootstrap_upper': boot['upper']}
        matches = {name: math.isclose(value, reference[name], rel_tol=plan['relative_comparison_tolerance'], abs_tol=plan['absolute_comparison_tolerance']) for name, value in actual.items()}
        records.append({'case_id': case['case_id'], 'adapter': case['adapter'], 'matches': matches, 'controlomics': actual, 'scipy': reference})
    return {'reference_software': {key: references[key] for key in ('python', 'numpy', 'scipy')},
        'request_sha256': digest(raw), 'case_count': len(records), 'all_matched': all(all(record['matches'].values()) for record in records),
        'native_tail_definition_differences': sum(not math.isclose(record['scipy']['p_scipy_native_two_sided'], record['controlomics']['p_absolute_tail'], abs_tol=1e-12) for record in records), 'cases': records}


def observation(count, total):
    return {'numerator': count, 'denominator': total, 'estimate': count/total, 'wilson_95_interval': wilson(count, total)}


def simulations(plan):
    records = []
    for number, scenario in enumerate(plan['scenarios']):
        generator = random.Random(plan['seed'] + 10000*(number+1))
        n, paired = scenario['units_per_group_or_pairs'], scenario['adapter'] == 'PAIRED_DIFFERENCE'
        counts = {'null_rejection': 0, 'shifted_rejection': 0, 'null_interval_coverage': 0}
        def draw():
            if scenario['distribution'] == 'NORMAL':
                return generator.gauss(0, 1)
            return generator.expovariate(1)-generator.expovariate(1)
        for trial in range(plan['trials_per_scenario']):
            values = [draw() for _ in range(n if paired else 2*n)]
            settings = {'seed': plan['seed']+trial, 'draws': plan['simulation_draws']}
            if paired:
                perm = paired_permutation(values, **settings)
                shifted = paired_permutation([value+plan['injected_shift'] for value in values], **settings)
                interval = paired_bootstrap(values, coverage=plan['simulation_coverage'], **settings)
            else:
                labels = [0]*n+[1]*n
                perm = permutation_test(values, labels, **settings)
                shifted = permutation_test(values[:n]+[value+plan['injected_shift'] for value in values[n:]], labels, **settings)
                interval = bootstrap_difference(values, labels, coverage=plan['simulation_coverage'], **settings)
            counts['null_rejection'] += perm['p_value'] <= plan['alpha']
            counts['shifted_rejection'] += shifted['p_value'] <= plan['alpha']
            counts['null_interval_coverage'] += interval['lower'] <= 0 <= interval['upper']
        records.append({**scenario, 'trials': plan['trials_per_scenario'], 'permutation_mode': 'EXACT' if perm['exact'] else 'MONTE_CARLO',
            'permutation_assignments_or_draws': perm['draws'], 'measurements': {name: observation(value, plan['trials_per_scenario']) for name, value in counts.items()}})
        print('Completed synthetic scenario: ' + scenario['scenario_id'], flush=True)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--reference-python', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.freeze:
        freeze(args.protocol)
        print('Frozen local synthetic protocol. No outcome was calculated or public preregistration made.')
        return
    if args.reference_python is None or args.output is None:
        parser.error('the run requires --reference-python and --output')
    plan = json.loads(args.protocol.read_bytes())
    if plan.get('format') != 'controlomics.synthetic_numerical_protocol.v0.1' or set(plan.get('source_sha256', {})) != set(SOURCE_FILES):
        raise ValueError('invalid frozen local numerical protocol')
    for name, expected in plan['source_sha256'].items():
        if digest((ROOT/name).read_bytes()) != expected:
            raise ValueError('frozen protocol source changed; retain the old protocol and define a new run')
    started = datetime.now(timezone.utc).isoformat()
    agreement = comparisons(plan, args.reference_python.resolve())
    result = {'format': 'controlomics.synthetic_numerical_validation.v0.1', 'started_at': started,
        'protocol_sha256': digest(args.protocol.read_bytes()), 'controlomics_version': __version__, 'python': platform.python_version(),
        'numeric_reference_agreement': agreement, 'synthetic_simulations': simulations(plan), 'scientific_control_selection_validated': False,
        'limitations': ['Synthetic populations and independently maintained numeric software do not constitute independent expert or biological validation.',
            'References align the declared absolute-tail convention; SciPy native two-sided probabilities can differ by definition.',
            'Identical supplied bootstrap indices isolate statistical calculations; equivalence of RNG algorithms is not claimed.',
            'Small-sample interval undercoverage is reported, not relabeled as validation success. Simulations do not establish coverage on real datasets.',
            'No human judgments, new publication identity checks, hosted model, external dataset, or outbound research request were used.']}
    result['completed_at'] = datetime.now(timezone.utc).isoformat()
    write(args.output, result)
    print(json.dumps({'reference_cases': agreement['case_count'], 'all_numeric_comparisons_matched': agreement['all_matched'], 'synthetic_scenarios': len(result['synthetic_simulations']), 'scientific_control_selection_validated': False}))
    raise SystemExit(0 if agreement['all_matched'] else 1)


if __name__ == '__main__':
    main()
