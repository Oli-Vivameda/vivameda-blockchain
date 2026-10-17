#!/usr/bin/env python3
"""Separate read-only early lane. Never imports or restarts production agents."""
import argparse
import datetime as dt
import fcntl
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import shutil
import signal
import time
from core import Journal,Lane,canonical,number,RULES_SHA,digest,CHECKS,checks
from evidence import EvidenceCollector as Collector
from exporter import atomic
from outcomes import record,finalize,due_daily,review,individual,HORIZONS
from alerts import message,flush
from transport import configuration,UnixSender
from pricing import Marks

class Runner:
    def __init__(self,state):
        self.path=Path(state);self.path.mkdir(mode=0o750,parents=True,exist_ok=True)
        if shutil.disk_usage(self.path).free<3*1024**3:raise ValueError('disk_reserve_below_3GiB')
        self.j=Journal(self.path/'lane.sqlite3');self.lane=Lane(self.j);self.collector=Collector(self.path/'rpc_cache.sqlite3')
        self.log=logging.getLogger('early-lane:'+str(self.path.resolve()));self.log.setLevel(logging.INFO);self.log.propagate=False
        if not self.log.handlers:
            h=RotatingFileHandler(self.path/'lane.log',maxBytes=2*1024**2,backupCount=2);h.setFormatter(logging.Formatter('%(message)s'));self.log.addHandler(h)
        self.last_processed={}
        self.last_priced={};self.price_cache={}
    def poll(self,frame,now=None,fixtures=False,log_only=True):
        now=time.time() if now is None else now
        if frame.get('schema')!='early-lane-feed-v1' or frame.get('rules_sha256')!=RULES_SHA or not 0<=now-frame['exported_at']<=60:raise ValueError('missing_stale_or_wrong_owner_feed')
        existing=self.lane.cohorts()
        for o in frame.get('observations',[]):
            if o['mint'] in existing and o.get('mc') is not None:
                record(self.lane,o['mint'],o['observed_at'],o['mc'],o.get('liquidity'),now,o['source_id'],o['provenance'])
        launches=[x for x in frame['launches'] if 0<=now-x['created_at']<=1800]
        for x in launches:
            self.j.atomic(lambda:self.j.add('launch','launch:'+x['mint'],{'mint':x['mint'],'created_at':x['created_at'],'first_observed_at':now,'late_discovery_s':max(0,now-x['created_at'])},now))
        facts=[];collection_issues={};enriched=0;self.collector.rpc.budget(12)
        price_issue=None
        if not fixtures:
            watched={x['mint']:x for x in launches}
            for mint,c in existing.items():
                if now<=c['at']+86400+120:watched.setdefault(mint,{'mint':mint,'created_at':c['facts']['created_at']})
            def priority(x):
                c=existing.get(x['mint']);urgent=False
                if c:
                    done={r['body']['horizon_min'] for r in self.j.rows('checkpoint',x['mint'])}
                    urgent=any(h not in done and abs(c['at']+h*60-now)<=120 for h in HORIZONS)
                return (0 if urgent else 1,self.last_priced.get(x['mint'],0),-x['created_at'],x['mint'])
            batch=sorted(watched.values(),key=priority)[:30]
            try:
                marks=Marks(self.collector.rpc).read(batch)
                for x in batch:
                    mint=x['mint'];self.last_priced[mint]=now
                    mark=marks.get(mint,{})
                    if mark.get('mc') is not None:self.price_cache[mint]=mark
                    else:self.price_cache.pop(mint,None)
            except (OSError,ValueError,KeyError,TypeError,IndexError) as exc:
                price_issue=str(exc)[:100]
            current=time.time()
            for x in launches:
                mark=self.price_cache.get(x['mint'])
                if mark and 0<=current-mark['market_at']<=60 and current<=mark['market_expires_at']:x.update(mark)
            for mint,mark in self.price_cache.items():
                if mint in existing and 0<=current-mark['market_at']<=60:
                    record(self.lane,mint,mark['market_at'],mark['mc'],mark.get('liquidity'),current,digest([mint,mark['market_at'],mark['pricing_provenance']]),mark['pricing_provenance'])
            self.price_cache={m:v for m,v in self.price_cache.items() if m in watched}
            self.last_priced={m:v for m,v in self.last_priced.items() if m in watched}
        # Fair round-robin of price-eligible candidates; missing evidence cannot
        # turn budget pressure into a PASS or an undocumented population change.
        launches.sort(key=lambda x:(self.last_processed.get(x['mint'],0),x['created_at'],x['mint']))
        for launch in launches:
            if launch['mint'] in existing:continue
            f=dict(launch)
            try:cheap=8000<=number(f['mc'])<=25000
            except (ValueError,KeyError,TypeError):cheap=False
            if fixtures and 'fixture_facts' in f:f=f['fixture_facts']
            elif cheap and self.collector.rpc.remaining>0:
                f=self.collector.enrich(f,now);self.last_processed[f['mint']]=now;enriched+=1
                for stage,reason in f.get('collection_issues',{}).items():
                    key=stage+':'+reason;collection_issues[key]=collection_issues.get(key,0)+1
            facts.append(f)
        decision_at=now if fixtures else time.time()
        fresh_marks=sum(x.get('mc') is not None and x.get('market_at') is not None and 0<=decision_at-x['market_at']<=60 and decision_at<=x.get('market_expires_at',decision_at) for x in launches)
        chosen=self.lane.consider(facts,decision_at,live=frame.get('source_live') is True and not fixtures and fresh_marks>0,log_only=log_only)
        # Persist decision/anchor observation BEFORE emitting any log message.
        for c in chosen:
            record(self.lane,c['mint'],c['at'],c['mc'],None,c['at'],'anchor:'+c['mint'],{'source':'eligibility_decision'},)
            text=message(c) if c['selection']=='ALERT' else 'CAP_SUPPRESSED '+c['mint']
            self.log.info(canonical({'kind':c['selection'],'text':text}));print(text,flush=True)
        end=now if fixtures else time.time();finalize(self.lane,end);due_daily(self.lane,end);review(self.lane,end);review(self.lane,end,True)
        requests=[]
        for mint,c in self.lane.cohorts().items():
            if end>c['at']+86400+120:continue
            item=individual(self.lane,c,end);completed={x['horizon_min'] for x in item['checkpoints']}
            targets=[c['at']+h*60 for h in HORIZONS if h not in completed]
            deadline=min(targets,default=end+86400)
            last=max((r['body']['observed_at'] for r in self.j.rows('observation',mint)),default=c['at'])
            urgency=0 if abs(deadline-end)<=120 else 1
            requests.append({'mint':mint,'priority':urgency,'target_at':deadline,'last_observed_at':last})
        requests.sort(key=lambda x:(x['priority'],x['target_at'] if x['priority']==0 else x['last_observed_at'],x['mint']))
        atomic(self.path/'tracked.json',requests)
        self.collector.prune({x['mint'] for x in launches})
        complete=sum(all(v!='UNKNOWN' for v in checks(f,decision_at).values())for f in facts)
        return {'enriched_candidates':enriched,'fully_evaluated_candidates':complete,'collection_issues':collection_issues,'launches_in_window':len(launches),'fresh_market_marks':fresh_marks,'pricing_issue':price_issue,'decisions':len(chosen),'selected':sum(c['selection']=='ALERT' for c in chosen),'suppressed':sum(c['selection']=='CAP_SUPPRESSED' for c in chosen),'coverage':frame.get('coverage')}

def volume_report(j):
    buckets={}
    for r in j.rows('launch'):
        hour=int(r['ts']//3600)*3600;b=buckets.setdefault(hour,{'first_seen_candidates':0,'filter_evaluations':0,'pass_each':{k:0 for k in CHECKS},'unknown_each':{k:0 for k in CHECKS},'sequential_pass':{k:0 for k in CHECKS},'selected':0,'suppressed':0});b['first_seen_candidates']+=1
    for r in j.rows('filter_audit'):
        hour=int(r['ts']//3600)*3600;b=buckets.setdefault(hour,{'first_seen_candidates':0,'filter_evaluations':0,'pass_each':{k:0 for k in CHECKS},'unknown_each':{k:0 for k in CHECKS},'sequential_pass':{k:0 for k in CHECKS},'selected':0,'suppressed':0});b['filter_evaluations']+=1;sequential=True
        for k in CHECKS:
            status=r['body']['checks'][k]
            if status=='PASS':b['pass_each'][k]+=1
            if status=='UNKNOWN':b['unknown_each'][k]+=1
            sequential=sequential and status=='PASS'
            if sequential:b['sequential_pass'][k]+=1
    for r in j.rows('cohort'):
        hour=int(r['ts']//3600)*3600
        if hour in buckets:buckets[hour]['selected' if r['body']['selection']=='ALERT' else 'suppressed']+=1
    # Unique mints ever passing each gate in the hour, distinct from repeated evaluations.
    for hour,b in buckets.items():
        audits=[r for r in j.rows('filter_audit') if int(r['ts']//3600)*3600==hour]
        b['unique_mints_passing_each']={k:len({r['body']['mint'] for r in audits if r['body']['checks'][k]=='PASS'}) for k in CHECKS}
    return {dt.datetime.fromtimestamp(t,dt.timezone.utc).isoformat():v for t,v in sorted(buckets.items())}

def rollout_gate(duration,valid,priced,max_feed_gap,max_price_gap,fully_evaluated):
    transport=duration>=7200 and valid>0 and priced>0 and max_feed_gap<=120 and max_price_gap<=120
    return {'transport_rollout_pass':transport,'screening_rollout_pass':transport and fully_evaluated>0,'live_rollout_pass':transport and fully_evaluated>0}

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['run','log-only','once','report']);p.add_argument('--state-dir',required=True);p.add_argument('--input');p.add_argument('--duration',type=int,default=7200);p.add_argument('--delivery-config');a=p.parse_args()
    path=Path(a.state_dir);path.mkdir(parents=True,exist_ok=True)
    if a.command!='report':
        lock=open(path/'process.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    r=Runner(path)
    if a.command=='report':print(canonical({'activation':r.lane.activation(),'volume':volume_report(r.j),'journal_head':r.j.verify(),'cohort_count':len(r.lane.cohorts())}));return
    if not a.input:p.error('input required')
    running=True
    def stop(*_):
        nonlocal running
        running=False
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    start=time.time();until=time.monotonic()+a.duration if a.command=='log-only' else float('inf');valid=0;cycles=0;errors={};valid_times=[];priced_times=[];fully_evaluated=0;issue_totals={}
    while running:
        if shutil.disk_usage(path).free<3*1024**3:raise SystemExit(75)
        cycles+=1
        try:
            conf={}
            if a.command=='run' and a.delivery_config:
                try:conf=configuration(a.delivery_config)
                except (ValueError,OSError,KeyError):r.log.error(canonical({'kind':'DELIVERY_CONFIG_BLOCKED'}))
            frame=json.loads(Path(a.input).read_text());data=r.poll(frame,log_only=not conf.get('new_channel_confirmed',False));valid+=1;valid_times.append(time.time());status='LOG_ONLY'
            if data.get('fresh_market_marks',0)>0:priced_times.append(time.time())
            fully_evaluated+=data.get('fully_evaluated_candidates',0)
            for key,count in data.get('collection_issues',{}).items():issue_totals[key]=issue_totals.get(key,0)+count
            if conf.get('new_channel_confirmed'):
                flush(r.lane,UnixSender(conf['socket']),conf,time.time());status='CONFIRMED_DELIVERY_QUEUE'
        except (OSError,ValueError,KeyError,TypeError) as exc:
            key=str(exc)[:100] if isinstance(exc,ValueError) else type(exc).__name__;errors[key]=errors.get(key,0)+1;data={};status='WAITING_FOR_OWNER_FEED' if isinstance(exc,FileNotFoundError) else 'SOURCE_BLOCKED'
        heartbeat={'at':time.time(),'status':status,'cycle':cycles,'valid_polls':valid,'telegram':False,**data};r.log.info(canonical(heartbeat));print(canonical(heartbeat),flush=True)
        if a.command=='once' or time.monotonic()>=until:break
        target=min(until,time.monotonic()+5)
        while running and time.monotonic()<target:time.sleep(min(1,max(0,target-time.monotonic())))
    finished=time.time();gaps=[b-a for a,b in zip([start]+valid_times,valid_times+[finished])];max_gap=max(gaps,default=finished-start)
    price_gap=max((b-a for a,b in zip([start]+priced_times,priced_times+[finished])),default=finished-start)
    gate=rollout_gate(finished-start,valid,len(priced_times),max_gap,price_gap,fully_evaluated);transport_pass=gate['transport_rollout_pass']
    receipt={'transport_rollout_pass':transport_pass,'screening_rollout_pass':transport_pass and fully_evaluated>0,'fully_evaluated_candidate_polls':fully_evaluated,'collection_issues':issue_totals,'maximum_valid_feed_gap_s':max_gap,'priced_polls':len(priced_times),'maximum_priced_poll_gap_s':price_gap,'started_at':start,'finished_at':time.time(),'duration_s':time.time()-start,'valid_owner_feed_polls':valid,'cycles':cycles,'errors':errors,'volume_per_hour':volume_report(r.j),'telegram_sent':0,'live_rollout_pass':transport_pass and fully_evaluated>0,'status':'OBSERVED_LOG_ONLY' if priced_times else 'BLOCKED_NO_USABLE_PRICES_NOT_A_ROLLOUT_PASS'}
    atomic(path/'log_only_receipt.json',receipt);print(canonical(receipt))
if __name__=='__main__':main()
