"""Audit local evaluation record readiness without claiming scientific independence."""

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from controlomics.evaluation import EvaluationBundle, evaluate
from controlomics.privacy import canonical_json
from controlomics.project import decode_json


def snapshot(value):
    return hashlib.sha256(canonical_json(value.model_dump(mode='json'))).hexdigest()


def audit(bundles, minimum_test_cases=100, minimum_source_groups=100):
    if not bundles or not 1 <= minimum_test_cases <= 200 or not 1 <= minimum_source_groups <= 200:
        raise ValueError('bounded study inputs and prespecified minima are required')
    first = bundles[0]
    test_cases = [case for case in first.dataset.cases if case.partition == 'TEST']
    annotators = {bundle.annotator.strip().casefold() for bundle in bundles if bundle.annotator and bundle.judgment_origin == 'EXPERT_ATTESTATION'}
    checks = {
        'same_reference_and_prediction_snapshots': all(snapshot(bundle.dataset) == snapshot(first.dataset) and snapshot(bundle.predictions) == snapshot(first.predictions) for bundle in bundles),
        'expert_reference_origin_declared': all(bundle.dataset.annotation_origin == 'EXPERT_ATTESTATION' for bundle in bundles),
        'expert_judgment_origin_declared': all(bundle.judgment_origin == 'EXPERT_ATTESTATION' for bundle in bundles),
        'two_distinct_expert_judgment_names_declared': len(annotators) >= 2,
        'minimum_test_cases': len(test_cases) >= minimum_test_cases,
        'minimum_test_source_groups': len({case.source_group for case in test_cases}) >= minimum_source_groups,
        'essential_references_defined_for_every_test_case': bool(test_cases) and all(any(ref.essential for ref in case.references) for case in test_cases),
    }
    coverage = []
    for bundle in bundles:
        report = evaluate(bundle, 'TEST') if any(case.partition == 'TEST' for case in bundle.dataset.cases) else None
        observed = report['coverage'] if report else {'cases': 0, 'recommendations': 0, 'appropriateness_assessed': 0, 'unsupported_assessed': 0, 'reference_recall_cases': 0}
        coverage.append({name: observed[name] for name in ('cases', 'recommendations', 'appropriateness_assessed', 'unsupported_assessed', 'reference_recall_cases')})
    checks['all_test_recommendations_assessed'] = bool(test_cases) and all(item['appropriateness_assessed'] == item['recommendations'] and item['unsupported_assessed'] == item['recommendations'] and item['reference_recall_cases'] == len(test_cases) for item in coverage)
    return {'format': 'controlomics.study_readiness.v0.1', 'recorded_at': datetime.now(timezone.utc).isoformat(),
        'record_contract_status': 'REQUIREMENTS_MET' if all(checks.values()) else 'INCOMPLETE',
        'checks': checks, 'missing_record_requirements': [name for name, met in checks.items() if not met],
        'prespecified_record_minima': {'test_cases': minimum_test_cases, 'test_source_groups': minimum_source_groups},
        'bundle_count': len(bundles), 'declared_distinct_expert_judgment_names': len(annotators),
        'partition_case_counts': dict(Counter(case.partition for case in first.dataset.cases)),
        'test_source_groups': len({case.source_group for case in test_cases}), 'test_coverage_by_sheet': coverage,
        'bundle_sha256': [snapshot(bundle) for bundle in bundles], 'scientific_independence_verified': False,
        'scope': 'Metadata, immutable snapshot identity, declared origins and coverage only. No names, descriptions, source text, raw measurements or file paths are exported. Hashes are not anonymization.',
        'human_verification_still_required': ['Real case provenance, source/cohort independence and data-use permission.',
            'Actual reviewer expertise, independence and truthful attestations; distinct names do not establish distinct people.',
            'A predefined scientific protocol, sampling justification, blinded review and retained adjudication.',
            'Scientific interpretation of measured outcomes and limitations, including negative results.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, action='append', required=True)
    parser.add_argument('--minimum-test-cases', type=int, default=100)
    parser.add_argument('--minimum-source-groups', type=int, default=100)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        bundles = []
        if len(args.bundle) > 10:
            raise ValueError('too many annotation sheets')
        for path in args.bundle:
            with path.open('rb') as stream:
                raw = stream.read(2 * 1024 * 1024 + 1)
            value = decode_json(raw)
            bundles.append(EvaluationBundle.model_validate_json(json.dumps(value)))
        report = audit(bundles, args.minimum_test_cases, args.minimum_source_groups)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
        print('Saved local record-readiness observations. This does not certify scientific independence or validity.')
        return 0
    except (ValueError, TypeError, KeyError, OSError):
        print('Study input could not be validated. Input contents and paths are omitted.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
