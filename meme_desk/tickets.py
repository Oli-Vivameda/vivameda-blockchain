"""Human-review tickets; no execution. Only accepted owner-exported market inputs."""
import datetime
from decimal import Decimal as D
from common import canonical, positive, screening, digest, PROTOCOL_SHA256, buy, sell
from reserves import select
from journal import SKIP_REASONS

def build(case,now,state,replay=None):
    if not state['enabled']:return None,'cumulative_loss_halt'
    if len(state['open_positions'])>=3:return None,'three_open_positions'
    age=now-case['decision_ts']
    if not 0<=age<=60:return None,'alert_too_old_or_future'
    snapshots=[s for s in case['snapshots'] if s['ts']<=now]
    if not snapshots:return None,'snapshot_missing'
    s=max(snapshots,key=lambda s:s['ts'])
    if now-s['ts']>30:return None,'stale_market_snapshot'
    ok,checks,why=screening(case.get('review'),case['mint'],case.get('pair'),now)
    if not ok:return None,why
    try:
        px=positive(s['price']);liq=positive(s['liq']);mc=positive(s['mc'])
        if liq<25000:return None,'liquidity_below_25000'
        if s['pair']!=case['pair']:return None,'pair_change'
        r=select(case.get('reserves',[]),case['mint'],case['pair'],s['ts'],px,30)
        if now-r['observed_at']>30:return None,'stale_reserves'
        x,y=D(r['x']),D(r['y'])
        qty=buy(x,y); buy_impact=1-qty/(D(10)/(y/x))
        # Round-trip comparison uses the post-buy virtual pool, not two untouched
        # pre-buy states. It assumes no intervening external trades.
        x_after,y_after=x-qty,y+10
        gross=sell(x_after,y_after,qty)
        sell_impact=1-gross/(qty*(y_after/x_after))
        # Conservative sum of per-side impact + 1% fees each + network 1% notional.
        # Fees assessed separately; no double-count inside reserve formulas.
        cost_pct=buy_impact+sell_impact+D('.02')+D('.015')
        if cost_pct>D('.06'):return None,'round_trip_cost_above_6pct'
        liq=min(liq,2*y)
        if liq<25000:return None,'authenticated_liquidity_below_25000'
        deadline=datetime.datetime.fromtimestamp(now+45*60,datetime.timezone.utc).strftime('%H:%M:%S UTC')
        created=case.get('created_ts')
        token_age=max(0,now-created/1000) if isinstance(created,(int,float)) and created>1e12 else None
        regime=case.get('regime') if case.get('regime') in ('CONTINUATION','COMPRESSION','RECLAIM') else 'OTHER'
        stats=(replay or {}).get('plans',{}).get('A',{}).get('regimes',{}).get(regime)
        ident=digest({'case':case['id'],'mint':case['mint']})[:24]
        unknown=[k for k,v in checks.items() if v=='UNKNOWN']
        counter=['Authenticated reserve captures and screening do not guarantee sellability; protocol upgrade/admin risk remains.']
        for k,v in case.get('review',{}).get('checks',{}).items():
            if k in unknown:counter.append(k+': '+str(v.get('reason') or 'missing evidence'))
        ticket={'id':ident,'source_case':case['id'],'mint':case['mint'],'symbol':str(case.get('symbol','?'))[:32],
                'created_at':now,'alert_time':case['decision_ts'],'alert_age_s':age,'token_age_s':token_age,
                'price':str(px),'entry_ceiling':str(px*D('1.03')),'size_usd':'10','market_cap_usd':str(mc),'liquidity_usd':str(liq),
                'regime':regime,'score':case.get('score'),'buy_impact_pct':str(100*buy_impact),'sell_impact_pct':str(100*sell_impact),
                'round_trip_cost_pct':str(100*cost_pct),'round_trip_cost_model':'Conservative side-impact sum, 1% fee each side and three $0.05 network charges for split plan A.',
                'plan_a':{'half_target':str(px*D('1.40')),'stop_remaining':str(px*D('.75')),'time_exit':deadline,'deadline_ts':now+2700,'reference':'current snapshot; owner must adjust to actual manual fill'},
                'invalidation':{'liquidity_below_usd':str(liq*D('.8')),'new_screening_reject':True,'price_above_ceiling':True,'market_or_reserves_stale':True},
                'unknown_checks':unknown,'counter_evidence':counter,'replay_a_regime':stats or 'no replay yet',
                'review_only':state['daily_loss']>=15,'label':'REVIEW ONLY, daily limit reached' if state['daily_loss']>=15 else 'MANUAL REVIEW; desk never executes',
                'links':{'chart':'https://dexscreener.com/solana/'+case['mint'],'jupiter':'https://jup.ag/swap/SOL-'+case['mint']},
                'buttons':[{'text':'TAKEN','callback_data':'take:'+ident},{'text':'SKIP','callback_data':'skip:'+ident}],
                'skip_reasons':SKIP_REASONS,'reserve_proof':r['proof_hash'],'screening_hash':digest(case['review']), 'execution':False}
        return ticket,'ticket'
    except (ValueError,KeyError,TypeError) as exc:
        return None,str(exc).split(':')[0]

def render(t,now=None):
    now=t['created_at'] if now is None else now
    late=max(0,int(now-t['alert_time']))
    stats=t['replay_a_regime']
    replay_text=('resolved '+str(stats.get('resolved'))+', unresolved '+str(stats.get('unresolved'))+', win rate '+str(stats.get('win_rate'))+', mean net/$10 '+str(stats.get('mean_net_pnl_usd'))) if isinstance(stats,dict) else str(stats)
    lines=[t['label'],t['symbol']+' | '+t['mint'],f'Alert age {late}s'+(' — LATE TICKET' if late>60 else ''),
           f'Token age: {t["token_age_s"]} seconds | MC ${t["market_cap_usd"]} | liquidity ${t["liquidity_usd"]}',
           f'Regime {t["regime"]} | score {t["score"]}',f'Current {t["price"]}; entry ceiling {t["entry_ceiling"]}; size $10',
           f'Impact in/out: {t["buy_impact_pct"]}% / {t["sell_impact_pct"]}%; round-trip estimate {t["round_trip_cost_pct"]}%',
           'Costs: 1% swap each side + three $0.05 network charges for split plan A.',
           f'Plan A: half at {t["plan_a"]["half_target"]}; stop unsold at {t["plan_a"]["stop_remaining"]}; time exit {t["plan_a"]["time_exit"]}',
           'Levels reference current snapshot; adjust to actual manual fill.',
           f'VOID if liquidity <${t["invalidation"]["liquidity_below_usd"]}, any new REJECT, ceiling breached or data stale.',
           'UNKNOWN: '+(', '.join(t['unknown_checks']) or 'none reported'),
           'Counter-evidence: '+'; '.join(str(x)[:200] for x in t['counter_evidence'][:3]),
           'Replay A, this regime: '+replay_text,t['links']['chart'],t['links']['jupiter'],'[TAKEN] [SKIP → fixed reason]']
    return '\n'.join(lines)

def ingest(j,export,now,replay=None):
    if export.get('schema')!='meme-desk-export-v1' or export.get('mode')!='tickets' or export.get('protocol_sha256')!=PROTOCOL_SHA256 or export.get('frozen_membership_excluded') is not True:
        raise ValueError('export_contract')
    if not 0<=now-export['exported_at']<=30:raise ValueError('stale_or_future_export')
    produced=[]
    for c in export['rows']:
        def op():
            state=j.state(now)
            ident=digest({'case':c['id'],'mint':c['mint']})[:24]
            if ident in state['tickets']:return
            ticket,reason=build(c,now,state,replay)
            if ticket:
                if j.append('ticket','ticket:'+ident,ticket,now):produced.append(ticket)
            else:
                # Preserve decision reason, but do not flood duplicate source polls.
                j.append('ticket_rejected','reject:'+c['id']+':'+reason,{'source_case':c['id'],'reason':reason},now)
        j.transaction(op)
    return produced
