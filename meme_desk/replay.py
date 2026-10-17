#!/usr/bin/env python3
"""Frozen deterministic snapshot replay. Case traces never belong in public output."""
import argparse
import collections
import json
from pathlib import Path
from decimal import Decimal as D
from common import PLANS, REGIMES, PROTOCOL_SHA256, canonical, positive, screening, buy, sell
from reserves import select

def snapshot_order(rows):
    seen={}
    for s in rows:
        if s['ts'] in seen and canonical(seen[s['ts']]) != canonical(s):
            raise ValueError('conflicting_snapshot')
        seen[s['ts']]=s
    return [seen[t] for t in sorted(seen)]

def prepare(case):
    ok, _, reason=screening(case.get('review'),case['mint'],case.get('pair'),case['decision_ts'])
    if not ok: return None, reason
    snapshots=snapshot_order(case['snapshots'])
    covered=next((s for s in snapshots if s['ts']>=case['decision_ts']+3600),None)
    if covered is None or covered['ts']>case['decision_ts']+3780:
        return None,'insufficient_60min_coverage'
    try: positive(covered['price'])
    except ValueError:return None,'invalid_60min_endpoint'
    if covered['pair']!=case['pair']:return None,'coverage_pair_change'
    return snapshots,None

def simulate(case, plan, snapshots):
    result={'plan':plan,'mint':case['mint'],'alert':case['decision_ts'],'regime':case['regime'] if case.get('regime') in REGIMES else 'OTHER',
            'score_band':'10+' if isinstance(case.get('score'),(int,float)) and case['score']>=10 else '8-9' if isinstance(case.get('score'),(int,float)) and case['score']>=8 else 'OTHER',
            'resolved':False,'legs':[]}
    try:
        entry=next((s for s in snapshots if s['ts']>=case['decision_ts']+60),None)
        if entry is None or entry['ts']>case['decision_ts']+240:
            raise ValueError('entry_missing_or_late')
        pair=case['pair']; price=positive(entry['price'])
        if entry['pair']!=pair: raise ValueError('pair_change')
        reserves=select(case.get('reserves',[]),case['mint'],pair,entry['ts'],price)
        qty=buy(reserves['x'],reserves['y'])
        initial_qty=qty
        tp,stop,minutes=PLANS[plan]
        target,stop_price=price*(1+D(tp)),price*(1-D(stop))
        deadline=entry['ts']+minutes*60
        last=entry['ts'];target_hit=False;net=D('-10.15')
        result['entry']={'time':entry['ts'],'price':str(price),'qty':str(qty),'reserve_proof':reserves['proof_hash'],'all_in_usd':'10.15'}
        for s in snapshots:
            if s['ts']<=entry['ts']: continue
            if s['ts']-last>180: raise ValueError('snapshot_gap')
            last=s['ts']
            if s['pair']!=pair: raise ValueError('pair_change')
            px=positive(s['price']);kind=None;amount=qty;level=None
            if s['ts']>deadline:
                if s['ts']-deadline>180: raise ValueError('time_exit_late')
                kind='time'
            elif px<=stop_price:
                kind='stop';level=stop_price
            elif not target_hit and px>=target:
                kind='half_target';amount=initial_qty/2;level=target
            if not kind: continue
            r=select(case.get('reserves',[]),case['mint'],pair,s['ts'],px)
            gross=sell(r['x'],r['y'],amount);proceeds=gross*D('.99')-D('.05')
            net+=proceeds;qty-=amount
            result['legs'].append({'kind':kind,'time':s['ts'],'snapshot_price':str(px),'qty':str(amount),'gross_usd':str(gross),'net_usd':str(proceeds),
                                   'threshold_overshoot':str(px/level-1) if level else None,'time_exit_lateness':s['ts']-deadline if kind=='time' else None,'reserve_proof':r['proof_hash']})
            if kind=='half_target': target_hit=True
            if qty==0:
                result.update(resolved=True,net_pnl=str(net),net_return_per_10=str(net/10));return result
        raise ValueError('required_exit_snapshot_missing')
    except (ValueError,KeyError,TypeError) as exc:
        result['unresolved_reason']=str(exc).split(':')[0]
        return result

def stats(rows):
    resolved=[D(r['net_pnl']) for r in rows if r['resolved']]
    wins=[x for x in resolved if x>0];losses=[x for x in resolved if x<0]
    trimmed=sorted(resolved)[:-5] if len(resolved)>5 else []
    mean=lambda x: str(sum(x)/len(x)) if x else None
    return {'case_count':len(rows),'resolved':len(resolved),'unresolved':len(rows)-len(resolved),
            'unresolved_reasons':dict(collections.Counter(r.get('unresolved_reason','unknown') for r in rows if not r['resolved'])),
            'win_rate':str(D(len(wins))/len(resolved)) if resolved else None,'average_win_usd':mean(wins),'average_loss_usd':mean(losses),
            'largest_single_loss_usd':str(min(losses)) if losses else None,'total_net_pnl_usd':str(sum(resolved)) if resolved else None,
            'mean_net_pnl_usd':mean(resolved),'mean_net_return_per_10':str(sum(resolved)/len(resolved)/10) if resolved else None,
            'excluding_best_5':{'resolved':len(trimmed),'mean_net_pnl_usd':mean(trimmed),'mean_net_return_per_10':str(sum(trimmed)/len(trimmed)/10) if trimmed else None}}

def run(export):
    if export.get('schema')!='meme-desk-export-v1' or export.get('mode')!='replay' or export.get('protocol_sha256')!=PROTOCOL_SHA256 or export.get('frozen_membership_excluded') is not True:
        raise ValueError('untrusted_or_wrong_export_contract')
    eligible=[];excluded=collections.Counter()
    for case in export['rows']:
        try:
            rows,reason=prepare(case)
        except (ValueError,KeyError,TypeError) as exc:
            rows,reason=None,str(exc)
        if reason: excluded[reason]+=1
        else: eligible.append((case,rows))
    eligible.sort(key=lambda cr:(cr[0]['decision_ts'],cr[0]['mint']))
    results=[]
    for i,(case,rows) in enumerate(eligible):
        for plan in PLANS:
            r=simulate(case,plan,rows);r['half']='EARLY' if i<len(eligible)//2 else 'LATE';results.append(r)
    aggregates={'protocol_sha256':PROTOCOL_SHA256,'status':'COMPUTED' if eligible else 'NO_ELIGIBLE_CASES','exported_development_cases':len(export['rows']),
                'eligible_cases':len(eligible),'exclusions':dict(excluded),'plans':{}}
    for p in PLANS:
        rows=[r for r in results if r['plan']==p]
        aggregates['plans'][p]={'overall':stats(rows),'regimes':{g:stats([r for r in rows if r['regime']==g]) for g in REGIMES},
                                'score_bands':{g:stats([r for r in rows if r['score_band']==g]) for g in ['8-9','10+','OTHER']},
                                'chronological_halves':{g:stats([r for r in rows if r['half']==g]) for g in ['EARLY','LATE']}}
    return aggregates,results

def markdown(a):
    lines=['# Exit-rule snapshot replay results','','Protocol SHA-256: '+PROTOCOL_SHA256,'','Status: '+a['status'],
           '', 'Snapshot replays, not real fills. Missing data stays unresolved. Negative results are valid. No model probabilities or protected cases used.','',
           '```json',json.dumps(a,indent=2,sort_keys=True),'```','']
    return '\n'.join(lines)

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--private-rows',required=True);p.add_argument('--aggregates',required=True);p.add_argument('--markdown',required=True);a=p.parse_args()
    aggregates,private=run(json.loads(Path(a.input).read_text()))
    from exporter import atomic_write
    atomic_write(a.private_rows,private);atomic_write(a.aggregates,aggregates)
    Path(a.markdown).write_text(markdown(aggregates))
    print(canonical({'status':aggregates['status'],'eligible':aggregates['eligible_cases'],'private_rows_written':len(private)}))
if __name__=='__main__':main()
