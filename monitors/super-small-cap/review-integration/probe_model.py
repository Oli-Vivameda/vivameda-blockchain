"""Local model schema probe on synthetic evidence; no production sends or records."""
import json,time
import review_worker as w
from test_review import fixture

def probe():
    p,_=fixture();p['comparable_pair_available']=False
    p['evidence'].pop('case_failure');p['evidence'].pop('case_held_gain')
    p['evidence']['comparison_missing']={'text':'No comparable completed pair; do not promote.'}
    now=int(time.time());p['alert_ts']=now-120
    for row,t in zip(p['observations'],[now-90,now-45,now]):row['ts']=t
    p['screening']['checked_at']=now
    for v in p['screening']['checks'].values():v['observed_at']=now
    started=time.monotonic();selection=w.model_review(p,w.agent_settings(),timeout=90);review=w.bind_review(p,selection,int(time.time()))
    if review['decision']=='FIRE_REVIEWED':raise ValueError('model probe promoted missing comparators')
    cold_elapsed=time.monotonic()-started;warm=time.monotonic()
    selection=w.model_review(p,w.agent_settings());review=w.bind_review(p,selection,int(time.time()))
    return {'model_schema_probe':'passed','initial_elapsed_seconds':round(cold_elapsed,3),'warm_elapsed_seconds':round(time.monotonic()-warm,3),'decision':review['decision'],'synthetic':True,'telegram_messages_sent':0,'selection_quality_validated':False}
if __name__=='__main__':print(json.dumps(probe(),sort_keys=True))
