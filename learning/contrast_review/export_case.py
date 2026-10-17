"""Owner-run read-only two-case comparison. Frozen members are never opened."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import time

DB = Path('/opt/vivameda-crypto-early-scout/data/early_scout.sqlite')
CHECKS = ('wallet_clusters', 'developer_history', 'top_holder_ownership', 'wallet_age',
          'token_controls', 'liquidity_control', 'trading_mechanics')
COLUMNS = {
    'sqlite_master': {'name', 'type'},
    'pl_predictions': {'mint'},
    'launches': {'mint', 'symbol', 'name', 'created_ts', 'first_seen', 'pinned_pair'},
    'v2_cases': {'mint', 'id', 'decision_ts', 'source', 'score', 'level', 'regime',
                 'entry_price', 'entry_mc', 'entry_liq'},
    'snapshots': {'mint', 'ts', 'pair', 'price', 'mc', 'liq', 'vol_m5', 'vol_h1',
                  'buys_m5', 'sells_m5', 'buys_h1', 'sells_h1', 'pc_m5', 'pc_h1'},
    'prealert_reviews': {'mint', 'level', 'checked_at', 'policy', 'verdict', 'review'},
}

def authorizer(action, table, column, database, trigger):
    if action == sqlite3.SQLITE_READ:
        return sqlite3.SQLITE_OK if table in COLUMNS and column in COLUMNS[table] else sqlite3.SQLITE_DENY
    if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_TRANSACTION): return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY

def number(value):
    return type(value) in (int, float) and math.isfinite(value)

def ratio(a, b):
    return a / b if number(a) and number(b) and b > 0 else None

def numeric_details(value, depth=0):
    """Only bounded numeric evidence; no arbitrary report text or wallet lists."""
    if depth > 4: return None
    if isinstance(value, dict):
        return {k: numeric_details(v, depth + 1) for k, v in list(value.items())[:40]
                if isinstance(k, str) and not re.search('prob|secret|password|credential|api_key|token_key', k, re.I)
                and (number(v) or isinstance(v, (dict, list)))}
    if isinstance(value, list): return [numeric_details(v, depth + 1) for v in value[:20] if number(v) or isinstance(v, dict)]
    return value if number(value) else None

def summarize(rows, alert):
    before = [r for r in rows if r['ts'] <= alert]
    after = [r for r in rows if r['ts'] >= alert]
    baseline = before[-1] if before and 0 <= alert - before[-1]['ts'] <= 120 else None
    features = None
    if baseline:
        b = baseline['buys_m5']; s = baseline['sells_m5']
        features = {k: baseline[k] for k in ('ts', 'price', 'mc', 'liq', 'vol_m5', 'vol_h1', 'pc_m5', 'pc_h1')}
        features.update(snapshot_age_seconds=alert-baseline['ts'],
                        buy_share_m5=ratio(b, b+s) if number(b) and number(s) else None,
                        liquidity_to_cap=ratio(baseline['liq'], baseline['mc']),
                        volume_acceleration=ratio(baseline['vol_m5'], baseline['vol_h1']/12) if number(baseline['vol_h1']) else None)
    endpoints = {}
    for minute in (5, 15, 30, 60):
        deadline = alert + minute*60
        hit = next((r for r in after if deadline <= r['ts'] <= deadline + 180), None)
        window = [r['ts'] for r in after if r['ts'] <= deadline + 180]
        coverage = bool(window and window[0] <= alert+180 and window[-1] >= deadline and
                        max((b-a for a,b in zip(window,window[1:])), default=0) <= 180)
        endpoints[str(minute)] = {'status': 'observed' if hit else 'missing', 'coverage_ok': coverage}
        if hit:
            endpoints[str(minute)].update(observed_ts=hit['ts'], lateness=hit['ts']-deadline,
                mc=hit['mc'], liquidity=hit['liq'],
                multiple=ratio(hit['mc'], baseline['mc']) if baseline else None)
    valid = [r for r in after if number(r['mc']) and r['mc'] > 0]
    peak = max(valid, key=lambda r:r['mc']) if valid else None
    return {'asof_snapshot_features': features, 'timed_endpoints_minutes': endpoints,
            'sampled_peak_lower_bound': {'mc': peak['mc'], 'ts': peak['ts']} if peak else None,
            'retained_prealert_samples': len(before), 'retained_postalert_samples': len(after),
            'scope': 'retained snapshots; no interpolation, lifetime ATH, fills or realized PnL'}

def collect(connection, mints, now):
    result = {'read_only': True, 'case_count_requested': len(mints), 'cases': [],
              'learning_applied': False, 'rules_changed': False,
              'selection': 'owner_selected_contrast_not_a_random_or_preregistered_validation_sample',
              'prediction_values_read': False, 'frozen_outcomes_read': False}
    present = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='pl_predictions'").fetchone()
    if not present: raise ValueError('frozen_membership_table_required')
    for mint in mints:
        # FIRST query for each identity: boolean membership only. No study bodies or labels.
        member = connection.execute('SELECT 1 FROM pl_predictions WHERE mint=? LIMIT 1', (mint,)).fetchone()
        if member:
            result['cases'].append({'mint': mint, 'status': 'EXCLUDED_FROZEN_NO_CASE_DATA_READ'})
            continue
        case = connection.execute('SELECT id,decision_ts,score,level,regime,entry_price,entry_mc,entry_liq FROM v2_cases WHERE mint=? AND source=\'ALERT\' ORDER BY decision_ts,id LIMIT 1', (mint,)).fetchone()
        if not case:
            result['cases'].append({'mint': mint, 'status': 'NO_RETAINED_ALERT'}); continue
        case = dict(case); alert = case['decision_ts']
        launch = connection.execute('SELECT symbol,name,created_ts,first_seen,pinned_pair FROM launches WHERE mint=?', (mint,)).fetchone()
        rows = [dict(r) for r in connection.execute('SELECT ts,pair,price,mc,liq,vol_m5,vol_h1,buys_m5,sells_m5,buys_h1,sells_h1,pc_m5,pc_h1 FROM snapshots WHERE mint=? AND ts BETWEEN ? AND ? ORDER BY ts LIMIT 2049', (mint, alert-2100, min(now, alert+86400)))]
        if len(rows) > 2048: raise ValueError('snapshot_export_bound')
        review = connection.execute('SELECT checked_at,policy,verdict,review FROM prealert_reviews WHERE mint=? AND level=? AND checked_at BETWEEN ? AND ? ORDER BY checked_at DESC LIMIT 1', (mint, case['level'], alert-300, alert)).fetchone()
        screening = {'status': 'NO_RETAINED_ASOF_REVIEW', 'checks': {k: {'status': 'UNKNOWN'} for k in CHECKS}}
        if review:
            raw = json.loads(review['review']); checks = raw.get('checks', {})
            screening.update(status='RETAINED_ASOF_REVIEW', checked_at=review['checked_at'], policy=review['policy'],
                verdict=review['verdict'], identity_bound=bool(launch and raw.get('mint')==mint and raw.get('chain')=='solana' and raw.get('pair')==launch['pinned_pair']))
            for key in CHECKS:
                item = checks.get(key, {}); at = item.get('observed_at'); refs = item.get('evidence_refs')
                fresh = number(at) and 0 <= alert-at <= 300
                verified = screening['identity_bound'] and fresh and isinstance(refs,list) and bool(refs) and all(isinstance(x,str) and bool(x.strip()) for x in refs)
                status = item.get('status') if verified else 'UNKNOWN'
                screening['checks'][key] = {'status': status if status in ('PASS','REJECT') else 'UNKNOWN',
                    'observed_at': at if number(at) else None, 'evidence_ref_count': len(refs) if isinstance(refs,list) else 0,
                    'numeric_details': numeric_details(item.get('details', {}))}
        result['cases'].append({'mint': mint, 'status': 'EXPLORATORY_NONFROZEN', 'first_retained_alert': case,
            'launch': dict(launch) if launch else None, 'screening_asof_alert': screening, **summarize(rows, alert)})
    result['pair_eligible_for_exploratory_comparison'] = all(c['status'] == 'EXPLORATORY_NONFROZEN' for c in result['cases'])
    return result

def audit(path, mints, now=None):
    if len(mints) != 2 or len(set(mints)) != 2 or any(not re.fullmatch('[1-9A-HJ-NP-Za-km-z]{32,44}', m) for m in mints):
        raise ValueError('two_distinct_exact_mints_required')
    connection = sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro', uri=True, timeout=2)
    try:
        connection.row_factory = sqlite3.Row; connection.execute('PRAGMA query_only=ON'); connection.execute('BEGIN')
        deadline = time.monotonic()+20
        connection.set_progress_handler(lambda: int(time.monotonic()>deadline), 1000)
        connection.set_authorizer(authorizer)
        return collect(connection, mints, int(time.time()) if now is None else now)
    finally:
        connection.rollback(); connection.close()

def main():
    p = argparse.ArgumentParser(); p.add_argument('--expected-sha256', required=True); p.add_argument('--mint', action='append', required=True)
    args = p.parse_args()
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != args.expected_sha256:
        raise SystemExit('hash_mismatch_no_database_opened')
    try: print(json.dumps(audit(DB, args.mint), sort_keys=True, allow_nan=False))
    except Exception as error: raise SystemExit('read_only_audit_unavailable:'+type(error).__name__) from None

if __name__ == '__main__': main()
