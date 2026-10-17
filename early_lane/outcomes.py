"""Observed outcomes only, nearest checkpoints, DST-aware summaries, frozen review."""
import datetime as dt
import statistics
from decimal import Decimal as D
from zoneinfo import ZoneInfo
from core import number,digest,FOOTER
HORIZONS=(5,15,30,60,360,1440)
CYPRUS=ZoneInfo('Asia/Nicosia')

def observations(j,mint):return [r['body'] for r in j.rows('observation',mint)]

def record(lane,mint,at,mc,liq,now,source_id,provenance):
    cohort=lane.cohorts().get(mint)
    if not cohort or not cohort['at']<=at<=min(now,cohort['at']+86400+120):return False
    value=number(mc)
    if value<0:raise ValueError('negative_market_cap')
    if liq is not None and number(liq)<0:raise ValueError('negative_liquidity')
    data={'mint':mint,'observed_at':at,'received_at':now,'mc':str(value),'liquidity':None if liq is None else str(number(liq)),'source_id':source_id,'provenance':provenance}
    return lane.j.atomic(lambda:lane.j.add('observation','observation:'+mint+':'+source_id,data,now))

def finalize(lane,now):
    for mint,c in lane.cohorts().items():
        obs=observations(lane.j,mint)
        for h in HORIZONS:
            target=c['at']+h*60
            if now<target+120:continue
            # Only evidence available by finalization deadline, never a late provider backfill.
            choices=[o for o in obs if abs(o['observed_at']-target)<=120 and o['received_at']<=target+120]
            chosen=min(choices,key=lambda o:(abs(o['observed_at']-target),o['observed_at'],o['source_id'])) if choices else None
            body={'mint':mint,'horizon_min':h,'target':target,'observation':chosen,'status':'OBSERVED' if chosen else 'MISSING'}
            lane.j.atomic(lambda:lane.j.add('checkpoint','checkpoint:'+mint+':'+str(h),body,now))
        obs=[o for o in obs if o['observed_at']<=c['at']+86400]
        # Milestones remain immutable observations, not unobserved intraminute crossing claims.
        for threshold in (2,3,5,10):
            crossed=[o for o in obs if number(o['mc'])>=number(c['mc'])*threshold]
            for o in sorted(crossed,key=lambda o:o['observed_at']):
                lane.j.atomic(lambda:lane.j.add('milestone',f'milestone:{mint}:{threshold}:{o["source_id"]}',{'mint':mint,'multiple':threshold,'observed_at':o['observed_at'],'source_id':o['source_id']},now))
                break
        dead=[o for o in obs if number(o['mc'])<number(c['mc'])*D('.3') or o['liquidity'] is not None and number(o['liquidity'])==0]
        if dead:
            first=min(dead,key=lambda o:o['observed_at'])
            lane.j.atomic(lambda:lane.j.add('dead','dead:'+mint,{'mint':mint,'observed_at':first['observed_at'],'source_id':first['source_id'],'meaning':'dead/price-collapse, not proof of fraud'},now))

def individual(lane,c,now):
    obs=[o for o in observations(lane.j,c['mint']) if o['observed_at']<=c['at']+86400];base=number(c['mc'])
    points=[(c['at'],base)]+[(o['observed_at'],number(o['mc'])) for o in obs]
    peak=max(points,key=lambda p:(p[1],-p[0]));crossings={str(m):min((t for t,mc in points if mc>=base*m),default=None) for m in (2,3,5,10)}
    checkpoints=[r['body'] for r in lane.j.rows('checkpoint',c['mint'])]
    return {'mint':c['mint'],'selection':c['selection'],'at':c['at'],'mature':now>=c['at']+86400+120,'checkpoint_covered':len(checkpoints)==6 and all(x['status']=='OBSERVED' for x in checkpoints),
            'observed_peak_multiple':str(peak[1]/base),'time_to_peak_s':peak[0]-c['at'],'first_observed_crossings':crossings,
            'dead':any(mc<base*D('.3') for _,mc in points) or any(o['liquidity'] is not None and number(o['liquidity'])==0 for o in obs),
            'observations':len(obs),'checkpoints':checkpoints}

def aggregate(rows):
    n=len(rows);counts={str(m):sum(r['first_observed_crossings'][str(m)] is not None for r in rows) for m in (2,3,5,10)}
    covered=[r for r in rows if r['mature'] and r['checkpoint_covered']]
    return {'count':n,'mature':sum(r['mature'] for r in rows),'mature_checkpoint_covered':len(covered),'crossings':counts,
            'observed_rates_all':{k:counts[k]/n if n else None for k in counts},'dead':sum(r['dead'] for r in rows),
            'dead_rate':sum(r['dead'] for r in rows)/n if n else None,
            'median_observed_time_to_peak_s':statistics.median(r['time_to_peak_s'] for r in rows) if rows else None,
            'ten_x_rate_mature_covered':sum(r['first_observed_crossings']['10'] is not None for r in covered)/len(covered) if covered else None,
            'coverage_note':'Observed lower bounds; complete checkpoints do not establish intraminute peak coverage.'}

def summary(lane,start,end,now):
    rows=[individual(lane,c,now) for c in lane.cohorts().values() if start<=c['at']<end]
    return {'start':start,'end':end,'generated_at':now,'alerts':aggregate([r for r in rows if r['selection']=='ALERT']),
            'suppressed':aggregate([r for r in rows if r['selection']=='CAP_SUPPRESSED']),
            'note':'Small sample. Observed peak multiples, not realized profit. Immature or missing outcomes are not failures.'}

def due_daily(lane,now):
    activation=lane.activation()
    if activation is None:return None
    local=dt.datetime.fromtimestamp(now,CYPRUS)
    if local.hour<8:return None
    day=local.date()-dt.timedelta(days=1)
    start=dt.datetime.combine(day,dt.time(),CYPRUS).timestamp();end=dt.datetime.combine(day+dt.timedelta(days=1),dt.time(),CYPRUS).timestamp()
    if activation>=end:return None
    data=summary(lane,max(start,activation),end,now);data.update(day=str(day),timezone='Asia/Nicosia',provisional=True)
    added=lane.j.atomic(lambda:lane.j.add('daily','daily:'+str(day),data,now))
    return data if added else None

def review(lane,now,final=False):
    activation=lane.activation()
    if activation is None:return None
    cutoff=activation+14*86400
    if now<cutoff+(86400+120 if final else 0):return None
    data=summary(lane,activation,cutoff,now);rows=[individual(lane,c,now) for c in lane.cohorts().values() if activation<=c['at']<cutoff]
    fields=['dev_pct','dev_first_pct','top_holder_pct','unique_buyers','buys_5m','sells_5m']
    exploratory={}
    cohorts=lane.cohorts()
    for field in fields:
        wins=[];others=[]
        for r in rows:
            if not r['mature'] or not r['checkpoint_covered']:continue
            value=cohorts[r['mint']]['facts'].get(field)
            if value is None:continue
            (wins if r['first_observed_crossings']['10'] is not None else others).append(float(number(value)))
        exploratory[field]={'ten_x_mean':statistics.mean(wins) if wins else None,'other_mean':statistics.mean(others) if others else None,'n_10x':len(wins),'n_other':len(others)}
    rate=data['alerts']['observed_rates_all']['10']
    data.update(review='final' if final else 'day14_provisional',review_date=dt.datetime.fromtimestamp(now,CYPRUS).isoformat(),
                observed_ten_percent_benchmark_met=None if rate is None else rate>=.1,
                conclusion='Descriptive only; missing/immature samples cannot validate a funding decision. No automatic spending or filter change.',
                exploratory=exploratory,exploratory_limits='All selected/suppressed cohorts passed every filter. These within-pass value contrasts cannot identify the causal value of any filter or of dropping it.')
    key='review:final' if final else 'review:day14'
    return data if lane.j.atomic(lambda:lane.j.add('review',key,data,now)) else None
