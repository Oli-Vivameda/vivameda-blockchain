"""Validate independent research classifications. No model, network, prices or sending."""
import hashlib
import json
import math

POLICY='crypto-super-small-cap-v1'
CORE=('token_controls','liquidity_control','trading_mechanics')
BACKGROUND=('wallet_clusters','developer_history','top_holder_ownership','wallet_age')
LABELS=('DISCOVERY','EARLY_WATCH','PROMISING_SETUP','FIRE_REVIEWED','AVOID')

def number(x):return type(x) in (int,float) and math.isfinite(x)
def fresh(x,now):return number(x) and 0<=now-x<=300
def cited(item):
    refs=item.get('evidence_refs') if isinstance(item,dict) else None
    return isinstance(refs,list) and bool(refs) and all(isinstance(r,str) and bool(r.strip()) for r in refs)
def evidence_hash(packet):
    # The caller must supply authoritative observations and screening, not model-invented data.
    fields=('mint','pair','chain','alert_ts','observations','screening','evidence','market_cap','cap_source')
    return hashlib.sha256(json.dumps({k:packet.get(k) for k in fields},sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def chart_ok(packet,now):
    rows=packet.get('observations',[])
    if not isinstance(rows,list) or len(rows)<3:return False
    times=[]
    for row in rows:
        if not isinstance(row,dict) or row.get('mint')!=packet.get('mint') or row.get('pair')!=packet.get('pair'):return False
        if not number(row.get('ts')) or not number(row.get('price')) or row['price']<=0 or row['ts']>now:return False
        times.append(row['ts'])
    # Evidence completeness, not a learned return filter. Use actual short-window samples.
    return (times==sorted(set(times)) and 0<=now-times[-1]<=45
            and 60<=times[-1]-times[0]<=180
            and max(b-a for a,b in zip(times,times[1:]))<=90)

def supported(item,evidence):
    if not isinstance(item,dict) or not isinstance(item.get('text'),str) or not item['text'].strip():return False
    refs=item.get('evidence_refs')
    return isinstance(refs,list) and bool(refs) and all(isinstance(r,str) and r in evidence for r in refs)

def classify(packet,now,previous_label=None,fire_already_delivered=False):
    result={'policy':POLICY,'classification':'DISCOVERY','reasons':[],'unknowns':[],
            'fire_message_eligible':False,'live_execution':False,'validated_100x_probability':None,'trigger':'SUPER_SMALL_CAP','experimental':True}
    if not isinstance(packet,dict) or not number(now):raise ValueError('Invalid packet or clock')
    if packet.get('chain')!='solana' or not packet.get('mint') or not packet.get('pair'):
        result.update(classification='EARLY_WATCH',reasons=['identity_missing_or_unsupported']);return result
    mc=packet.get('market_cap')
    if not number(mc) or not 10000<=mc<=20000:
        result.update(classification='EARLY_WATCH',reasons=['outside_super_small_cap_band_or_cap_unknown']);return result
    screen=packet.get('screening',{})
    if not isinstance(screen,dict):screen={}
    checks=screen.get('checks',{})
    if not isinstance(checks,dict):checks={}
    screen_identity=screen.get('mint')==packet['mint'] and screen.get('pair')==packet['pair'] and fresh(screen.get('checked_at'),now)
    if screen_identity and any(isinstance(v,dict) and v.get('status')=='REJECT' and fresh(v.get('observed_at'),now) and cited(v) for v in checks.values()):
        result.update(classification='AVOID',reasons=['current_explicit_screening_reject']);return result
    review=packet.get('independent_review')
    if not isinstance(review,dict):return result
    result['classification']='EARLY_WATCH'
    if not screen_identity:
        result['reasons']=['screening_missing_stale_or_identity_mismatch'];return result
    for name in CORE:
        item=checks.get(name,{})
        if not isinstance(item,dict) or item.get('status')!='PASS' or not fresh(item.get('observed_at'),now) or not cited(item):
            result['reasons']=['required_screening_incomplete'];return result
    result['unknowns']=[k for k in BACKGROUND if not isinstance(checks.get(k),dict) or checks[k].get('status')!='PASS' or not fresh(checks[k].get('observed_at'),now) or not cited(checks[k])]
    if not chart_ok(packet,now):
        result['reasons']=['chart_missing_gapped_stale_or_identity_mismatch'];return result
    refs=packet.get('evidence',{})
    if not isinstance(refs,dict):refs={}
    if not supported(review.get('chart_setup'),refs):
        result['reasons']=['chart_setup_unassessed'];return result
    result.update(classification='PROMISING_SETUP',reasons=['supported_chart_setup'])
    identity=(review.get('mint')==packet['mint'] and review.get('pair')==packet['pair'] and review.get('policy')==POLICY)
    if not identity or not fresh(review.get('reviewed_at'),now) or review.get('based_on_sha256')!=evidence_hash(packet):
        result['reasons'].append('independent_review_missing_stale_or_wrong_evidence_version');return result
    if review.get('kind')=='independent' and review.get('decision')=='AVOID' and supported(review.get('thesis_failure'),refs):
        result.update(classification='AVOID',reasons=['evidenced_current_thesis_failure']);return result
    if review.get('kind')!='independent' or review.get('decision')!='FIRE_REVIEWED':return result
    alert=packet.get('alert_ts');latest=packet['observations'][-1]['ts']
    if not number(alert) or not alert<latest<=review['reviewed_at']:
        result['reasons'].append('no_new_post_alert_observation');return result
    for name in ('participation_and_liquidity','thesis','historical_failure','invalidation'):
        if not supported(review.get(name),refs):
            result['reasons'].append(name+'_missing_or_unreferenced');return result
    # AVOID based on thesis failure is an explicitly evidenced current assessment, not an unknown.
    if review.get('thesis_status')!='SUPPORTED':
        result['reasons'].append('thesis_not_supported');return result
    result.update(classification='FIRE_REVIEWED',reasons=['separate_review_completed'],
                  fire_message_eligible=previous_label!='FIRE_REVIEWED' and not fire_already_delivered)
    return result
