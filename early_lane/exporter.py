#!/usr/bin/env python3
"""Owner-run sanitized launch/market export; scanner database is strictly read-only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import sqlite3
import tempfile
import time
import urllib.parse
from core import canonical,RULES_SHA,number
from sources import PublicHTTPS,SourceUnavailable,retry_seconds
DB='/opt/vivameda-crypto-early-scout/data/early_scout.sqlite'
COLUMNS={'launches':{'mint','created_ts','creator','name','symbol','protocol','token_program','pump_pool','first_seen','last_pump_seen','last_trade_ts','current_mc','complete','pinned_pair'},'snapshots':{'mint','ts','pair','price','mc','liq'}}

def readonly(path):
    c=sqlite3.connect('file:'+urllib.parse.quote(str(Path(path).resolve()),safe='/')+'?mode=ro',uri=True,timeout=.2);c.row_factory=sqlite3.Row
    c.execute('PRAGMA query_only=ON');c.execute('BEGIN');started=time.monotonic()
    c.set_progress_handler(lambda:int(time.monotonic()-started>15),1000)
    def auth(a,t,col,db,tr):
        if a==sqlite3.SQLITE_READ:return sqlite3.SQLITE_OK if t in COLUMNS and (col in COLUMNS[t] or col=='') else sqlite3.SQLITE_DENY
        if a in (sqlite3.SQLITE_SELECT,sqlite3.SQLITE_FUNCTION):return sqlite3.SQLITE_OK
        if a==sqlite3.SQLITE_TRANSACTION and t=='ROLLBACK':return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    c.set_authorizer(auth);return c

def atomic(path,obj,reader_uid=None):
    p=Path(path);p.parent.mkdir(mode=0o750,parents=True,exist_ok=True)
    if p.is_symlink():raise ValueError('symlink_export_refused')
    fd,tmp=tempfile.mkstemp(prefix='.early-lane-',dir=p.parent)
    try:
        os.fchmod(fd,0o640)
        with os.fdopen(fd,'w') as f:f.write(canonical(obj)+'\n');f.flush();os.fsync(f.fileno())
        os.replace(tmp,p)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    if reader_uid is not None:
        if os.geteuid()!=0 or p.parent.stat().st_uid!=0 or p.parent.stat().st_mode&0o022:raise ValueError('owner_controlled_export_directory_required')
        reader=pwd.getpwuid(reader_uid);os.chown(p.parent,-1,reader.pw_gid);p.parent.chmod(0o750);os.chown(p,0,reader.pw_gid);p.chmod(0o640)

def collect(c,now,tracked=()):
    rows=c.execute('SELECT mint,created_ts,creator,name,symbol,protocol,token_program,pump_pool,first_seen,last_pump_seen,last_trade_ts,current_mc,complete,pinned_pair FROM launches WHERE created_ts>=? AND created_ts<=? ORDER BY created_ts,mint LIMIT 100001',((now-1800)*1000,now*1000)).fetchall()
    if len(rows)>100000:raise ValueError('launch_export_limit_no_partial_data')
    launches=[];observations=[]
    for row in rows:
        x=dict(row);x.update(created_at=x.pop('created_ts')/1000,first_seen_at=(x.get('first_seen') or 0)/1000)
        # current_mc has no atomic capture time: never redate a cached value to now.
        x['mc']=None;x['market_at']=None;x['market_issue']='cached_launch_mc_timestamp_unestablished';launches.append(x)
    for mint in set(tracked)|{x['mint'] for x in launches}:
        latest=c.execute('SELECT ts,mc,liq,pair FROM snapshots WHERE mint=? AND ts BETWEEN ? AND ? ORDER BY ts DESC LIMIT 1',(mint,now-120,now)).fetchone()
        if latest:
            s=dict(latest)
            # Scanner stores missing liquidity as zero in some paths: zero alone
            # is not authenticated evidence of drained reserves.
            observations.append({'mint':mint,'observed_at':s['ts'],'mc':s['mc'],'liquidity':s['liq'] if s['liq'] is not None and s['liq']>0 else None,'source_id':'scanner-snapshot:'+str(s['ts'])+':'+mint,'provenance':{'source':'owner_readonly_snapshot','pair':s['pair']}})
            launch=next((x for x in launches if x['mint']==mint),None)
            if launch and now-s['ts']<=60 and s['mc'] is not None:launch.update(mc=s['mc'],market_at=s['ts'],market_issue=None)
    return {'schema':'early-lane-feed-v1','exported_at':now,'rules_sha256':RULES_SHA,'source_live':True,'launches':launches,'observations':observations,'coverage':{'universal_launch_coverage':False,'scope':'retained scanner launch rows, NSFW excluded, source gaps possible'}}

def refresh(frame,http=None,tracked=()):
    """Owner explicitly refreshes the scanner's existing PUBLIC launch endpoint.

    No source import/DB write. Original provider trade time remains visible; capture
    time is a fresh public response, not a retroactive price/fill guarantee.
    """
    h=http or PublicHTTPS();now=time.time();seen={};complete=False
    for offset in range(0,2001,100):
        q=urllib.parse.urlencode({'offset':offset,'limit':100,'sort':'created_timestamp','order':'DESC','includeNsfw':'false'})
        response=h.get('https://frontend-api-v3.pump.fun/coins?'+q,limit=2*1024*1024)
        if response['status']==429:
            error=SourceUnavailable('launch_endpoint_rate_limit_respect_retry_after');error.retry_after=retry_seconds(response['headers']);raise error
        if response['status']!=200:raise SourceUnavailable('launch_endpoint_unavailable')
        data=json.loads(response['body']);captured=time.time()
        if not isinstance(data,list) or len(data)>100:raise SourceUnavailable('launch_feed_schema')
        for row in data:
            created=row.get('created_timestamp')
            if type(created) not in (int,float):continue
            if created/1000<now-1800:complete=True;continue
            if created/1000>captured or not isinstance(row.get('mint'),str):continue
            vals=[number(row[k]) for k in ('market_cap_usd','usd_market_cap') if row.get(k) is not None]
            mc=vals[0] if vals and all(v==vals[0] for v in vals) and vals[0]>=0 else None
            trade=row.get('last_trade_timestamp')
            age=next((v for k,v in response['headers'].items() if k.lower()=='age'),'0')
            try:fresh=0<=float(age)<=60
            except ValueError:fresh=False
            seen[row['mint']]={'mint':row['mint'],'created_at':created/1000,'creator':row.get('creator'),'name':row.get('name'),'symbol':row.get('symbol'),'mc':str(mc) if mc is not None and fresh else None,'market_at':captured if mc is not None and fresh else None,'first_seen_at':captured,'provider_trade_at':trade/1000 if type(trade) in (int,float) else None,'source_response_hash':hashlib.sha256(response['body']).hexdigest(),'market_issue':None if mc is not None and fresh else 'missing_or_stale_usd_cap'}
        if len(data)<100:complete=True
        if complete:break
        time.sleep(1)
    # Track the existing feed's single-token records after the 30-minute watch
    # window, including after the production scanner's own coverage window ends.
    attempted=0
    for item in tracked[:12]:
        mint=item['mint'] if isinstance(item,dict) else item
        if mint in seen:continue
        from pump import public
        if not public(mint):raise SourceUnavailable('invalid_tracked_mint')
        attempted+=1
        response=h.get('https://frontend-api-v3.pump.fun/coins/'+mint,limit=524288)
        if response['status']==429:
            error=SourceUnavailable('launch_endpoint_rate_limit_respect_retry_after');error.retry_after=retry_seconds(response['headers']);raise error
        if response['status']!=200:continue
        raw=json.loads(response['body']);captured=time.time()
        if not isinstance(raw,dict) or raw.get('mint')!=mint:continue
        values=[number(raw[k]) for k in ('market_cap_usd','usd_market_cap') if raw.get(k) is not None]
        age=next((v for k,v in response['headers'].items() if k.lower()=='age'),'0')
        try:fresh=0<=float(age)<=60
        except ValueError:fresh=False
        if not values or not all(x==values[0] for x in values) or values[0]<0 or not fresh:continue
        frame['observations'].append({'mint':mint,'observed_at':captured,'mc':str(values[0]),'liquidity':None,'source_id':'tracked-feed:'+hashlib.sha256(response['body']).hexdigest()+':'+str(captured),'provenance':{'source':'same_public_launch_feed_single_token','provider_last_trade':raw.get('last_trade_timestamp'),'note':'provider-reported market cap at capture; not executable price'}})
        time.sleep(1)
    frame['coverage'].update(tracked_refresh_attempted=attempted,tracked_refresh_requested=len(tracked),tracked_refresh_budget=12)
    by_mint={x['mint']:x for x in frame['launches']};by_mint.update(seen);frame['launches']=list(by_mint.values())
    frame['coverage'].update(public_launch_refresh=True,pagination_30min_boundary_reached=complete,nsfw_included=False)
    # This is a fresh measured point for outcome cohorts present in the same feed.
    for x in seen.values():
        if x.get('mc') is not None:frame['observations'].append({'mint':x['mint'],'observed_at':x['market_at'],'mc':x['mc'],'liquidity':None,'source_id':'launch-response:'+x['source_response_hash']+':'+x['mint']+':'+str(x['market_at']),'provenance':{'source':'same_public_launch_feed_owner_refresh','last_trade_at':x['provider_trade_at']}})
    frame['exported_at']=time.time();return frame

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',default=DB);p.add_argument('--output',required=True);p.add_argument('--tracked');p.add_argument('--refresh-launch-feed',action='store_true');p.add_argument('--expected-bundle',required=True);p.add_argument('--reader-uid',type=int);a=p.parse_args()
    from verify import verify
    verify(a.expected_bundle)
    tracked=[]
    if a.tracked and Path(a.tracked).exists():
        tracked=json.loads(Path(a.tracked).read_text())
        if not isinstance(tracked,list) or len(tracked)>100000 or any(not isinstance(x,(str,dict)) for x in tracked):raise ValueError('tracked_mints_shape')
    cooldown=Path(a.output).parent/'feed_cooldown.json'
    if cooldown.exists() and time.time()<json.loads(cooldown.read_text()).get('retry_at',0):raise ValueError('launch_feed_cooldown')
    c=readonly(a.source)
    try:frame=collect(c,time.time(),[x['mint'] if isinstance(x,dict) else x for x in tracked])
    finally:c.rollback();c.close()
    if a.refresh_launch_feed:
        try:frame=refresh(frame,tracked=tracked)
        except SourceUnavailable as exc:
            if hasattr(exc,'retry_after'):atomic(cooldown,{'retry_at':time.time()+exc.retry_after})
            raise
    atomic(a.output,frame,a.reader_uid)
    print(canonical({'output':a.output,'launches':len(frame['launches']),'observations':len(frame['observations']),'query_only':True,'scanner_modified':False,'coverage':frame['coverage']}))
if __name__=='__main__':main()
