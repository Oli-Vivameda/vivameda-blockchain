"""Private retrospective call audit. Read-only input; no network, model or alerts."""
import argparse
import datetime as dt
import hashlib
import html
import json
import math
import os
from pathlib import Path
import pwd
import sqlite3
import statistics
import time

DB = Path('/opt/vivameda-crypto-early-scout/data/early_scout.sqlite')
DELIVERY = Path('/var/lib/vivameda-100x-watchlist/delivery.json')
OUT = Path('/var/lib/vivameda-engineering/repo/client_learning/crypto_chart_audit_20261011/results')
HORIZONS = (60, 180, 360, 1440)
MAX_CASES = 10000
FEATURES = ('band', 'buy_ratio', 'vol_mc', 'pc5', 'pc1', 'liq_change', 'vol_accel',
            'pre_slope_per_minute', 'pre_drawdown', 'higher_lows', 'range_compression', 'breakout_ratio')

def finite(x):
    return type(x) in (int, float) and math.isfinite(x)

def canonical(x):
    return json.dumps(x, sort_keys=True, allow_nan=False, separators=(',', ':'))

def clean_features(raw):
    try:
        x = json.loads(raw) if isinstance(raw, str) else raw
        return {k: v for k, v in x.items() if finite(v)} if isinstance(x, dict) else {}
    except (ValueError, TypeError):
        return {}

def pre_features(rows, call):
    # Actual saved price samples only. Never substitute rounded evaluation timestamps.
    rows = sorted(r for r in rows if call-2100 <= r[0] <= call and finite(r[1]) and r[1] > 0)
    if len(rows) < 6 or rows[-1][0]-rows[0][0] < 600 or call-rows[-1][0] > 120:
        return {}, 'missing_or_short_pre_call_price_history'
    if max(b[0]-a[0] for a, b in zip(rows, rows[1:])) > 180:
        return {}, 'gapped_pre_call_price_history'
    if len({r[2] for r in rows}) != 1 or not rows[0][2]:
        return {}, 'pre_call_pool_identity_missing_or_changed'
    xs = [(r[0]-rows[0][0])/60 for r in rows]
    ys = [r[1]/rows[0][1] for r in rows]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    slope = sum((x-mx)*(y-my) for x,y in zip(xs,ys))/sum((x-mx)**2 for x in xs)
    peak, drawdown = ys[0], 0
    for y in ys:
        peak = max(peak, y); drawdown = max(drawdown, 1-y/peak)
    width = (rows[-1][0]-rows[0][0])/3
    bins = [[r[1] for r in rows if min(2, int((r[0]-rows[0][0])/width)) == i] for i in range(3)]
    result = {'pre_slope_per_minute': slope, 'pre_drawdown': drawdown,
              'breakout_ratio': rows[-1][1]/max(r[1] for r in rows[:-1])-1}
    if all(len(b) >= 2 for b in bins):
        lows = [min(b) for b in bins]
        result['higher_lows'] = int(lows[0] < lows[1] < lows[2])
        ranges = [(max(b)-min(b))/min(b) for b in bins]
        if ranges[0] > 0: result['range_compression'] = ranges[-1]/ranges[0]
    return result, 'saved_price_samples_pool_consistent'

def path_metrics(case, observations, checkpoint, now, horizon):
    start, entry = case['decision_ts'], case['entry_mc']
    due = start+horizon*60
    result = {'due_ts': due, 'eligible': False, 'reason': 'pending' if now < due else 'missing_checkpoint',
              'unit': 'observed_market_cap_multiple_not_price_or_profit'}
    if now < due or not checkpoint or not finite(entry) or entry <= 0: return result
    o = checkpoint
    valid = (type(o.get('lateness')) is int and 0 <= o['lateness'] <= 180
             and o.get('observed_ts') == due+o['lateness'] and o.get('coverage_ok') == 1
             and finite(o.get('max_gap')) and 0 <= o['max_gap'] <= 180
             and finite(o.get('multiple')) and o['multiple'] > 0)
    if not valid:
        result['reason'] = 'invalid_late_or_incomplete_checkpoint'; return result
    samples = sorted((t,m/entry,l) for t,m,l in observations if start <= t <= due and finite(m) and m > 0)
    gaps = [samples[0][0]-start, due-samples[-1][0]] if samples else [due-start]
    gaps += [b[0]-a[0] for a,b in zip(samples,samples[1:])]
    if not samples or max(gaps) > 180:
        result['reason'] = 'missing_or_gapped_ordered_observations'; return result
    peak, drawdown, drawdown_before_2 = 1.0, 0.0, 0.0
    hits = {}; trough = 1.0; low_liq = None
    for t,m,l in samples:
        peak = max(peak,m); trough = min(trough,m); drawdown = max(drawdown,1-m/peak)
        if '2x' not in hits: drawdown_before_2 = max(drawdown_before_2,1-m/peak)
        for label, predicate in [('2x', m>=2), ('3x',m>=3), ('5x',m>=5), ('half',m<=.5)]:
            if predicate and label not in hits: hits[label] = t-start
        if finite(l) and l >= 0: low_liq = l if low_liq is None else min(l, low_liq)
    target, stop = hits.get('2x'), hits.get('half')
    ordered = ('TARGET_FIRST' if target is not None and (stop is None or target < stop)
               else 'STOP_FIRST' if stop is not None else 'NEITHER')
    endpoint = o['multiple']
    result.update(eligible=True, reason='complete_observed_path', endpoint_multiple=endpoint,
                  checkpoint_lateness=o['lateness'], samples=len(samples), max_gap=max(gaps),
                  max_multiple=peak, min_multiple=trough, max_drawdown=drawdown,
                  drawdown_before_2x=drawdown_before_2, first_hits_seconds=hits,
                  observed_2x_vs_half_order=ordered, minimum_observed_liquidity=low_liq,
                  peak_then_collapse=peak>=2 and endpoint<=.5,
                  endpoint_class='HELD_GAIN' if endpoint>=2 else 'LOST_HALF' if endpoint<=.5 else 'MIDDLE')
    return result

def comparisons(cases):
    # First call per mint only; gains held at a fixed horizon, not maximum-ever labels.
    eligible = [c for c in cases if c['primary'] and c['horizons']['60']['eligible']]
    winners = [c for c in eligible if c['horizons']['60']['endpoint_class']=='HELD_GAIN']
    losers = [c for c in eligible if c['horizons']['60']['endpoint_class']=='LOST_HALF']
    def compare(subset):
        w = [c for c in subset if c in winners]; l = [c for c in subset if c in losers]
        features = {}
        for k in FEATURES:
            a = [c['features'][k] for c in w if finite(c['features'].get(k))]
            b = [c['features'][k] for c in l if finite(c['features'].get(k))]
            features[k] = {'winner_n':len(a), 'loser_n':len(b),
                           'winner_median':statistics.median(a) if a else None,
                           'loser_median':statistics.median(b) if b else None}
        return {'eligible':len(subset), 'held_gain':len(w), 'lost_half':len(l), 'features':features}
    ordered = sorted(eligible, key=lambda c:(c['decision_ts'], c['id']))
    # Never split same-time calls across temporal partitions.
    times = sorted({c['decision_ts'] for c in ordered})
    cutoff = times[max(0,int(len(times)*.7)-1)] if times else None
    earlier = [c for c in ordered if c['decision_ts']<=cutoff]
    later = [c for c in ordered if c['decision_ts']>cutoff]
    return {'all':compare(ordered), 'earlier_70_percent_time_groups':compare(earlier),
            'later_30_percent_time_groups':compare(later),
            'per_regime':{r:compare([c for c in ordered if c['regime']==r]) for r in sorted({c['regime'] for c in ordered})},
            'status':'descriptive_feature_comparison_only_no_fitted_rule',
            'note':'Directions must be checked on later calls. Small groups and missing charts do not validate a selection rule.'}

def utc(ts):
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat()

def svg_chart(case, pre, observations):
    def panel(samples, baseline, start, end, top, title):
        pieces = [f'<text x="45" y="{top-10}">{html.escape(title)}</text>',
                  f'<rect x="45" y="{top}" width="810" height="160" fill="none" stroke="#999"/>']
        if not samples or not finite(baseline) or baseline<=0:
            return ''.join(pieces)+f'<text x="55" y="{top+70}">No retained samples; chart unavailable</text>'
        logs = [math.log(max(1e-6,v/baseline)) for _,v in samples]
        low, high = min(min(logs),0), max(max(logs),0)
        if high-low < .1: low-=.05;high+=.05
        def xy(t,v): return (45+810*(t-start)/max(1,end-start),top+160-160*(math.log(max(1e-6,v/baseline))-low)/(high-low))
        baseline_y = xy(start,baseline)[1]
        pieces += [f'<path d="M45 {baseline_y:.1f} H855" stroke="#bbb" stroke-dasharray="4 3"/>']
        segments = []; segment = []; previous = None
        for t,v in samples:
            if previous is not None and t-previous>180:
                if segment: segments.append(segment)
                segment=[]
            segment.append(xy(t,v));previous=t
        if segment:segments.append(segment)
        for seg in segments:
            if len(seg)>1:
                points=' '.join(f'{x:.1f},{y:.1f}' for x,y in seg)
                pieces.append(f'<polyline points="{points}" fill="none" stroke="#176dad" stroke-width="1.7"/>')
            else:
                x,y=seg[0];pieces.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="#176dad"/>')
        pieces.append(f'<text x="45" y="{top+179}">log scale; baseline 1×; gaps above 180s are disconnected</text>')
        return ''.join(pieces)
    start=case['decision_ts']; end=start+86400
    pre_samples=[(r[0],r[1]) for r in pre if finite(r[1]) and r[1]>0]
    post=[(t,m) for t,m,_ in observations if start<=t<=end and finite(m) and m>0]
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="900" height="590" viewBox="0 0 900 590">'
            '<rect width="900" height="590" fill="white"/><g font-family="sans-serif" font-size="13" fill="#222">'
            f'<text x="45" y="25">{html.escape(str(case.get("symbol") or "?"))} — {utc(start)}</text>'
            f'<text x="45" y="46">{html.escape(case["mint"])}</text>'
            +panel(pre_samples,case.get('entry_price'),start-2100,start,90,'Before call: saved price samples, 35 minutes')
            +panel(post,case['entry_mc'],start,end,320,'After call: market-cap proxy observations, 24 hours; NOT a price candle chart')
            +'<text x="45" y="540">Post-call pool/supply continuity and executable returns are unverified.</text>'
            '<text x="45" y="560">Retained calls only. Missing samples stay missing; this is not a 100× forecast.</text></g></svg>')

def load_audit(conn, delivered, now, delivery_available=True):
    conn.row_factory=sqlite3.Row
    required={'v2_cases','v2_outcomes','v2_horizon_metrics','v2_observations','snapshots','launches','pl_predictions'}
    tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not required <= tables: raise ValueError('Required audit or exclusion table missing')
    # Identifiers/count only. Never read prediction bodies, model probabilities or pl_results.
    excluded={r[0] for r in conn.execute('SELECT mint FROM pl_predictions')}
    alerts=conn.execute("SELECT COUNT(*) FROM v2_cases WHERE source='ALERT'").fetchone()[0]
    rows=conn.execute('''SELECT c.*,l.symbol,l.name,l.created_ts FROM v2_cases c
        LEFT JOIN launches l ON l.mint=c.mint
        WHERE c.source='ALERT' AND NOT EXISTS(SELECT 1 FROM pl_predictions p WHERE p.mint=c.mint)
        ORDER BY c.decision_ts,c.id LIMIT ?''',(MAX_CASES+1,)).fetchall()
    if len(rows)>MAX_CASES: raise ValueError('Audit case bound exceeded; no silent truncation')
    first=set();cases=[];charts={}
    for r in rows:
        case=dict(r);mint=case['mint'];start=case['decision_ts']
        case['primary']=mint not in first;first.add(mint)
        case['features']=clean_features(case.get('features'))
        pre=[tuple(x) for x in conn.execute('SELECT ts,price,pair FROM snapshots WHERE mint=? AND ts BETWEEN ? AND ? ORDER BY ts',(mint,start-2100,start))]
        extra,reason=pre_features(pre,start);case['features'].update(extra)
        case['pre_chart_status']=reason
        case['feature_provenance']='reconstructed_saved_case_features; historical knowledge time and policy versions unestablished'
        case['fire_delivery']=delivered.get(mint,{}).get('result')
        obs=[tuple(x) for x in conn.execute('SELECT observed_ts,mc,liq FROM v2_observations WHERE id=? AND observed_ts BETWEEN ? AND ? ORDER BY observed_ts LIMIT 2001',(case['id'],start,start+86400))]
        if len(obs)>2000:raise ValueError('Observation bound exceeded; no silent truncation')
        case['horizons']={}
        for h in HORIZONS:
            row=conn.execute('''SELECT o.observed_ts,o.lateness,o.multiple,h.coverage_ok,h.max_gap
                FROM v2_outcomes o LEFT JOIN v2_horizon_metrics h
                ON h.id=o.id AND h.horizon=o.horizon AND h.observed_ts=o.observed_ts
                WHERE o.id=? AND o.horizon=?''',(case['id'],h)).fetchone()
            case['horizons'][str(h)]=path_metrics(case,obs,dict(row) if row else None,now,h)
        # Peak here is only a descriptive maximum of retained local observations, never ATH.
        multiples=[m/case['entry_mc'] for _,m,_ in obs if finite(m) and m>0 and finite(case['entry_mc']) and case['entry_mc']>0]
        case['retained_peak_multiple']=max([1.0]+multiples)
        case['retained_last_multiple']=multiples[-1] if multiples else None
        cases.append(case);charts[case['id']]=svg_chart(case,pre,obs)
    eligible_delivery={m:v for m,v in delivered.items() if m not in excluded}
    unmatched=[{'mint':m,'result':v.get('result'),'attempted_at':v.get('attempted_at')} for m,v in eligible_delivery.items() if m not in first]
    inventory={'retained_alert_events':alerts, 'audited_non_holdout_events':len(cases),
        'first_call_tokens':len(first), 'repeat_call_events':len(cases)-len(first),
        'protected_mints_excluded':len(excluded), 'protected_alert_events_excluded':alerts-len(cases),
        'fire_delivery_ledger_available':delivery_available,
        'fire_deliveries_non_holdout':sum(v.get('result')=='sent' for v in eligible_delivery.values()),
        'unmatched_fire_attempts':len(unmatched),
        'calls_with_usable_pre_price_chart':sum(c['pre_chart_status']=='saved_price_samples_pool_consistent' for c in cases)}
    summary={}
    for h in HORIZONS:
        group=[c['horizons'][str(h)] for c in cases if c['primary']]
        ok=[m for m in group if m['eligible']]
        summary[str(h)]={'eligible':len(ok),'missing_or_pending':len(group)-len(ok),
            'held_gain':sum(m['endpoint_class']=='HELD_GAIN' for m in ok),
            'lost_half':sum(m['endpoint_class']=='LOST_HALF' for m in ok),
            'target_first':sum(m['observed_2x_vs_half_order']=='TARGET_FIRST' for m in ok),
            'stop_first':sum(m['observed_2x_vs_half_order']=='STOP_FIRST' for m in ok),
            'peak_then_collapse':sum(m['peak_then_collapse'] for m in ok)}
    report={'schema':'private-retrospective-chart-audit-v1','generated_at':now,'inventory':inventory,
        'horizon_summary':summary,'comparisons':comparisons(cases),'cases':cases,'unmatched_fire_attempts':unmatched,
        'weights_updated':False,'rules_promoted':False,'live_execution':False,
        'limitations':['Retained server ALERT and separate fire-delivery records only; old deleted calls and manual chat mentions are not reconstructed.',
            'Protected prediction-ledger mints are excluded entirely; their outcomes are never queried.',
            'Pre-call price charts may have expired. Aggregated features cannot recreate candles.',
            'Post-call observations are market cap, not price; historical pool/supply continuity is unverified.',
            'First barrier crossings mean first observed crossings, not guaranteed intraminute order or achievable fills.',
            'Incomplete paths and late checkpoints stay missing; no future data or global ATH is substituted.',
            'Feature comparisons are hypotheses, not trained weights or validated selection rules.']}
    return report,charts

def markdown(report):
    inv=report['inventory'];lines=['# Private historical call and chart audit','',f'Generated: {utc(report["generated_at"])}','']
    lines+=['| Coverage | Count |','|---|---:|']+[f'| {k} | {v} |' for k,v in inv.items()]
    lines+=['','## Outcomes of first calls per mint','','Market-cap observations only. Gains held and target-before-stop are separate outcomes.','',
             '| Horizon | Complete | Missing/pending | Held ≥2× | Lost ≥50% | 2× observed first | Half observed first | Peaked ≥2× then ended ≤0.5× |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for h,x in report['horizon_summary'].items():
        lines.append('| '+str(h)+' min | '+' | '.join(str(x[k]) for k in ('eligible','missing_or_pending','held_gain','lost_half','target_first','stop_first','peak_then_collapse'))+' |')
    lines+=['','## What differed before the calls','','Descriptive medians of saved features; missing inputs are not filled. First calls only. The JSON separately compares earlier/later periods and regimes.','',
             '| Feature | Held-gain n | Lost-half n | Held-gain median | Lost-half median |','|---|---:|---:|---:|---:|']
    for k,x in report['comparisons']['all']['features'].items():
        vals=[x['winner_n'],x['loser_n'],x['winner_median'],x['loser_median']]
        lines.append('| '+k+' | '+' | '.join('missing' if v is None else f'{v:.6g}' for v in vals)+' |')
    lines+=['','## Evidence limits','']+['- '+x for x in report['limitations']]
    lines+=['','Every eligible retained ALERT event has its own private JSON case and SVG chart. Repeated alerts remain visible but are excluded from primary comparisons. No new Telegram selection policy has been activated.','']
    return '\n'.join(lines)

def private_write(path, text, uid=None, gid=None):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:
        f.write(text);f.flush();os.fsync(f.fileno())
        if uid is not None:os.fchown(f.fileno(),uid,gid)

def main():
    p=argparse.ArgumentParser();p.add_argument('--expected-sha256',required=True);p.add_argument('--owner-audit',action='store_true');a=p.parse_args()
    source_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if a.expected_sha256!=source_hash:raise ValueError('Reviewed audit hash mismatch')
    if not a.owner_audit or os.geteuid()!=0:raise ValueError('Fixed-path owner audit required; production database is private')
    now=int(time.time());identity=pwd.getpwnam('vivameda-engineer')
    if OUT.is_symlink() or OUT.parent.is_symlink():raise ValueError('Output symlink refused')
    if OUT.exists() and (not OUT.is_dir() or OUT.stat().st_uid!=identity.pw_uid):raise ValueError('Unexpected output owner')
    OUT.mkdir(mode=0o700,exist_ok=True);os.chown(OUT,identity.pw_uid,identity.pw_gid);os.chmod(OUT,0o700)
    run=OUT/str(now);run.mkdir(mode=0o700);os.chown(run,identity.pw_uid,identity.pw_gid)
    delivered={};delivery_available=DELIVERY.exists()
    if DELIVERY.exists():
        if DELIVERY.is_symlink() or DELIVERY.stat().st_size>1024*1024:raise ValueError('Delivery ledger invalid')
        raw=json.loads(DELIVERY.read_text())
        if not isinstance(raw,dict):raise ValueError('Delivery ledger invalid')
        delivered={k:v for k,v in raw.items() if not k.startswith('_') and isinstance(v,dict)}
    if DB.is_symlink():raise ValueError('Database symlink refused')
    con=sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True,timeout=30)
    started=time.monotonic();con.set_progress_handler(lambda:int(time.monotonic()-started>120),10000)
    try:
        con.execute('PRAGMA query_only=ON');con.execute('BEGIN')
        report,charts=load_audit(con,delivered,now,delivery_available)
    finally:con.close()
    report['audit_source_sha256']=source_hash
    report['output_directory']=str(run)
    uid,gid=identity.pw_uid,identity.pw_gid
    private_write(run/'audit.json',canonical(report)+'\n',uid,gid)
    private_write(run/'REPORT.md',markdown(report),uid,gid)
    chart_dir=run/'charts';chart_dir.mkdir(mode=0o700);os.chown(chart_dir,uid,gid)
    index={}
    for case_id,text in charts.items():
        name=hashlib.sha256(case_id.encode()).hexdigest()[:24]+'.svg'
        private_write(chart_dir/name,text,uid,gid);index[case_id]=name
    private_write(run/'chart_index.json',canonical(index)+'\n',uid,gid)
    print(canonical({'completed':True,'output_directory':str(run),'inventory':report['inventory'],
        'horizon_summary':report['horizon_summary'],'scanner_changed':False,'relay_changed':False,
        'weights_updated':False,'private_raw_data_uploaded':False}))

if __name__=='__main__':
    main()
