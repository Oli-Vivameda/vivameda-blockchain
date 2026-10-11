"""Retrospective, private chart-pattern study. No fitting, network or promotion."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import statistics

BASE=Path(__file__).resolve().parent/'results/1791717527'
RECOVERY='recovery-1791718042/recovery.json'

def finite(v):return type(v) in (int,float) and math.isfinite(v)
def median(values):return statistics.median(values) if values else None

def price_features(rows,call):
    rows=sorted((t,p,pool) for t,p,pool in rows if call-600<=t<=call and finite(p) and p>0)
    if (len(rows)<6 or len({r[2] for r in rows})!=1 or not rows[0][2]
        or rows[0][0]-(call-600)>120 or call-rows[-1][0]>120
        or max([b[0]-a[0] for a,b in zip(rows,rows[1:])]+[0])>180):return {}
    prices=[r[1] for r in rows];lo,hi=min(prices),max(prices);peak=prices[0];dd=0
    for p in prices:peak=max(peak,p);dd=max(dd,1-p/peak)
    groups=[[p for t,p,_ in rows if min(2,int((t-(call-600))/200))==i] for i in range(3)]
    return {'range10':(hi-lo)/lo,'net10':prices[-1]/prices[0]-1,'drawdown10':dd,
        'position10':(prices[-1]-lo)/(hi-lo) if hi>lo else .5,
        'higher_lows10':int(min(groups[0])<min(groups[1])<min(groups[2])) if all(groups) else None,
        'span_seconds':rows[-1][0]-rows[0][0],'samples':len(rows)}

def group_stats(cases):
    return {'n':len(cases),'price_medians':{k:median([c['price10'][k] for c in cases if finite(c['price10'].get(k))])
        for k in ('range10','net10','drawdown10','position10','higher_lows10')},
        'summary_medians':{k:median([c['summary_features'][k] for c in cases if finite(c['summary_features'].get(k))])
        for k in ('buy_ratio','vol_accel','liq_change')},
        'negative_pre_call_return':sum(c['price10']['net10']<0 for c in cases),
        'not_higher_lows':sum(c['price10'].get('higher_lows10')==0 for c in cases)}

def groups(cases):
    return {'held_2x':group_stats([c for c in cases if c['outcome24']['endpoint_class']=='HELD_GAIN']),
        'spike_then_collapse':group_stats([c for c in cases if c['outcome24']['peak_then_collapse']]),
        'lost_half_without_2x':group_stats([c for c in cases if c['outcome24']['endpoint_class']=='LOST_HALF' and not c['outcome24']['peak_then_collapse']]),
        'middle':group_stats([c for c in cases if c['outcome24']['endpoint_class']=='MIDDLE'])}

def matched(cases):
    winners=[c for c in cases if c['outcome24']['endpoint_class']=='HELD_GAIN']
    losers=[c for c in cases if c['outcome24']['endpoint_class']=='LOST_HALF'];used=set();pairs=[]
    for a in sorted(winners,key=lambda c:c['ts']):
        pool=[b for b in losers if b['mint'] not in used and b['regime']==a['regime']
              and abs(b['ts']-a['ts'])<=86400 and min(a['entry_mc'],b['entry_mc'],a['entry_liq'],b['entry_liq'])>0
              and abs(math.log2(a['entry_mc']/b['entry_mc']))<=1 and abs(math.log2(a['entry_liq']/b['entry_liq']))<=1]
        if not pool:continue
        b=min(pool,key=lambda b:(abs(math.log(a['entry_mc']/b['entry_mc']))+abs(math.log(a['entry_liq']/b['entry_liq']))+abs(a['ts']-b['ts'])/86400,b['mint']))
        used.add(b['mint'])
        pairs.append({'winner_mint':a['mint'],'loser_mint':b['mint'],'winner_symbol':a['symbol'],'loser_symbol':b['symbol'],
            'regime':a['regime'],'range_difference':a['price10']['range10']-b['price10']['range10'],
            'buy_difference':a['summary_features']['buy_ratio']-b['summary_features']['buy_ratio'] if finite(a['summary_features'].get('buy_ratio')) and finite(b['summary_features'].get('buy_ratio')) else None,
            'drawdown_difference':a['price10']['drawdown10']-b['price10']['drawdown10']})
    return {'n':len(pairs),'winner_range_lower':sum(p['range_difference']<0 for p in pairs),
            'winner_buy_share_higher':sum(finite(p['buy_difference']) and p['buy_difference']>0 for p in pairs),'pairs':pairs,
            'limits':'Greedy controls, no failure reused; exploratory. Small counts, age/score not matched, unknown policy/knowledge times.'}

def study(audit,recovery):
    lookup={c['id']:c for c in recovery['cases']};cases=[]
    for c in audit['cases']:
        if not c['primary']:continue
        r=lookup.get(c['id'],{});f=price_features(r.get('saved_pre_price_samples',[]),c['decision_ts'])
        h=c['horizons']['1440']
        cases.append({'id':c['id'],'mint':c['mint'],'symbol':c['symbol'],'ts':c['decision_ts'],'regime':c['regime'],
            'entry_mc':c['entry_mc'],'entry_liq':c['entry_liq'],'price10':f,'eligible24':h['eligible'],
            'summary_features':{k:c['features'].get(k) for k in ('buy_ratio','vol_accel','liq_change')},
            'outcome24':{k:h.get(k) for k in ('endpoint_class','endpoint_multiple','peak_then_collapse','max_multiple','max_drawdown','drawdown_before_2x')},
            'chart_status':'usable_fixed_10_minute_window' if f else 'missing_or_incomplete_fixed_window'})
    complete=sorted([c for c in cases if c['price10'] and c['eligible24']],key=lambda c:(c['ts'],c['mint']))
    times=sorted({c['ts'] for c in complete});cut=times[max(0,int(len(times)*.7)-1)] if times else None
    earlier=[c for c in complete if c['ts']<=cut];later=[c for c in complete if c['ts']>cut]
    # Explicitly post-hoc example to expose false positives. This is NOT a trained or validated selector.
    illustrative=[c for c in complete if c['price10']['range10']<=.2 and finite(c['summary_features'].get('buy_ratio')) and c['summary_features']['buy_ratio']>=.7]
    return {'schema':'private-recovered-chart-study-v1','inventory':audit['inventory'],
        'first_call_tokens':len(cases),'usable_fixed_10_minute_charts':sum(bool(c['price10']) for c in cases),
        'complete_chart_and_24h_outcome':len(complete),'all_groups':groups(complete),
        'earlier_groups':groups(earlier),'later_groups':groups(later),'chronological_cutoff':cut,
        'matched':matched(complete),'illustrative_post_hoc_screen':{'conditions':'range10 <= 20%; recorded buy share >=70%',
            'selected':len(illustrative),'held':sum(c['outcome24']['endpoint_class']=='HELD_GAIN' for c in illustrative),
            'lost_half':sum(c['outcome24']['endpoint_class']=='LOST_HALF' for c in illustrative),
            'spike_then_collapse':sum(c['outcome24']['peak_then_collapse'] for c in illustrative),
            'status':'post_hoc_diagnostic_not_validated_not_promoted'},
        'cases':cases,'weights_updated':False,'rules_promoted':False,'live_execution':False,
        'learning_notes':['Peak-only labels confuse a temporary rally with a gain held at a fixed horizon.',
            'Narrow range and stronger recorded buying share are candidate evidence, but matched cases weaken the range explanation.',
            'Higher lows or a positive last-ten-minute return cannot be mandatory: several sustained winners did not show them.',
            'Volume acceleration changes direction between one-hour and 24-hour winners; the objective must specify a horizon.',
            'A promising chart is a research hypothesis; false positives remain substantial. These observations do not validate 100x probability.'],
        'limitations':['139 retained first calls, not every historical/manual mention. Protected evaluation mints excluded in the owner export.',
            'Fixed ten-minute window uses saved price samples with at most 120-second edge gaps and 180-second internal gaps, not OHLC candles.',
            'Later outcomes are market-cap proxies; historical pool/supply continuity and executable returns are unverified.',
            'Only eight complete 24-hour held-gain cases. All period comparisons are descriptive; later periods are not untouched validation.',
            'Recorded transaction buying share is not verified organic demand or unique buyer growth.',
            'Historical case feature knowledge times and production policy versions remain unestablished.']}

def markdown(result):
    lines=['# Recovered chart study — 11 October 2026','',
        f"Reviewed {result['first_call_tokens']} retained first-call tokens. {result['usable_fixed_10_minute_charts']} have usable fixed-window price histories; {result['complete_chart_and_24h_outcome']} also have complete 24-hour observed outcomes.",'',
        '| 24-hour outcome | n | Median pre-call 10-minute range | Median pre-call drawdown | Median recorded buying share |','|---|---:|---:|---:|---:|']
    for name,g in result['all_groups'].items():
        def pct(v):return 'missing' if v is None else f'{100*v:.2f}%'
        lines.append(f"| {name} | {g['n']} | {pct(g['price_medians']['range10'])} | {pct(g['price_medians']['drawdown10'])} | {pct(g['summary_medians']['buy_ratio'])} |")
    m=result['matched'];x=result['illustrative_post_hoc_screen']
    lines+=['',f"Among {m['n']} matched winner/failure pairs, winners had narrower ranges in {m['winner_range_lower']} and higher buying shares in {m['winner_buy_share_higher']}. Matching uses regime, market cap, liquidity and call time. This weakens a simple compression explanation.",'',
        f"A post-hoc range <=20% and buy-share >=70% example selected {x['selected']} cases: {x['held']} held >=2x, {x['lost_half']} lost at least half, and {x['spike_then_collapse']} briefly reached >=2x then collapsed. This screen is NOT validated or activated.",'',
        '## Lessons','']+['- '+v for v in result['learning_notes']]
    lines+=['','## Evidence limits','']+['- '+v for v in result['limitations']]
    lines+=['','Production has not changed. Learned chart evidence should inform an independent review and a prospective comparison before changing fire selection.','']
    return '\n'.join(lines)

def main():
    argparse.ArgumentParser().parse_args()
    audit=json.loads((BASE/'audit.json').read_text());recovery=json.loads((BASE/RECOVERY).read_text())
    result=study(audit,recovery);out=BASE/'study';out.mkdir(mode=0o700,exist_ok=True)
    for name,value in [('study.json',json.dumps(result,sort_keys=True,allow_nan=False)),('REPORT.md',markdown(result))]:
        with (out/name).open('w') as f:f.write(value+'\n')
        (out/name).chmod(0o600)
    print(json.dumps({k:result[k] for k in ('first_call_tokens','usable_fixed_10_minute_charts','complete_chart_and_24h_outcome','all_groups','earlier_groups','later_groups','illustrative_post_hoc_screen')},allow_nan=False))

if __name__=='__main__':main()
