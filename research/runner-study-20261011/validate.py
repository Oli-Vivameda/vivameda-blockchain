"""Evidence integrity checks; not a selection model or archive completeness proof."""
import argparse
from datetime import datetime
import json
import math


def timestamp(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Timezone required')
    return dt.timestamp()


def decision_view(records, cutoff, mint, pair):
    """Only evidence demonstrably available for this identity at decision time."""
    deadline = timestamp(cutoff)
    included, excluded = [], []
    for row in records:
        reason = None
        if row.get('mint') != mint or row.get('pair') != pair:
            reason = 'identity_mismatch'
        elif not row.get('knowledge_time_verified'):
            reason = 'knowledge_time_unverified'
        elif row.get('time_precision') != 'timestamp':
            reason = 'imprecise_time'
        else:
            try:
                if timestamp(row['observed_at']) > deadline or timestamp(row['known_at']) > deadline:
                    reason = 'not_available_at_decision'
            except (KeyError, ValueError, TypeError):
                reason = 'invalid_time'
        if reason:
            excluded.append({'record': row, 'reason': reason})
        else:
            included.append(row)
    return {'included': included, 'excluded': excluded}


def price_path(samples, entry_time, end_time, mint, pair):
    """Sampled path only. Entry must be an observed sample, never interpolated."""
    start, end = timestamp(entry_time), timestamp(end_time)
    if end <= start:
        raise ValueError('End must follow entry')
    prices = {}
    for row in samples:
        if row.get('mint') != mint or row.get('pair') != pair:
            raise ValueError('Mixed identities')
        t, p = timestamp(row['time']), row['price']
        if isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or p <= 0:
            raise ValueError('Invalid price')
        if t in prices and prices[t] != p:
            raise ValueError('Conflicting duplicate timestamp')
        prices[t] = p
    if start not in prices or end not in prices:
        raise ValueError('Observed entry and endpoint required')
    values = [p for t, p in sorted(prices.items()) if start <= t <= end]
    base = prices[start]
    return {'peak_multiple': max(values) / base,
            'endpoint_multiple': prices[end] / base,
            'minimum_multiple': min(values) / base,
            'samples': len(values), 'executable_return_verified': False,
            'label': 'sampled_price_only'}


def validate_status(status):
    timestamp(status['window_start'])
    if timestamp(status['window_end']) <= timestamp(status['window_start']):
        raise ValueError('Invalid study window')
    rows = status.get('ranked_records', [])
    identities = [(r['chain'], r['mint']) for r in rows]
    if len(set(identities)) != len(identities):
        raise ValueError('Duplicate ranked identity')
    verified = 0
    for row in rows:
        if row.get('ranked_runner_verified'):
            if not row.get('outcome_source') or not row.get('early_chart_source'):
                raise ValueError('Verified rank lacks outcome or early-chart provenance')
            if row.get('outcome_kind') != 'bounded_timestamped_path':
                raise ValueError('Global ATH is not a bounded outcome')
            verified += 1
    if verified != status['verified_ranked_runners']:
        raise ValueError('Ranked count inconsistent with records')
    if status.get('complete'):
        # A flag is not evidence of a complete historical universe. Separate
        # archive and ranking review is required before this validator evolves.
        raise ValueError('Completion unsupported by this provisional study validator')
    if status.get('production_loaded') or status.get('weights_updated'):
        raise ValueError('Research status cannot imply deployment or weight training')
    return {'complete': False, 'verified_ranked_runners': verified,
            'goal_ranked_runners': status['goal_ranked_runners'],
            'audited_early_charts': status['audited_early_charts'],
            'blockers': status.get('blockers', [])}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--status', required=True)
    args = parser.parse_args()
    with open(args.status, encoding='utf-8') as f:
        print(json.dumps(validate_status(json.load(f)), sort_keys=True))
