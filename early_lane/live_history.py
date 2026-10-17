"""Live/catch-up collection isolated by session, queue and fixed RPC quota."""
import copy
import json
import sqlite3
import time
from collections import Counter
from core import canonical,digest,number
from evidence import clean
from live_rpc import LaneRpc
from pump import curve
from pricing import addresses,pool_identity
from sources import SourceUnavailable
from stream_history import StreamCollector

class LiveCollector(StreamCollector):
    scan_tables=('live_scan','catchup_scan')
    def __init__(self,path,stream_path,session_id,http=None):
        super().__init__(path,stream_path,http)
        self.session_id=session_id;self.live_mints=set();self.scan_table='catchup_scan'
        for table in self.scan_tables:
            self.cache.execute('CREATE TABLE IF NOT EXISTS '+table+'(mint TEXT PRIMARY KEY,body TEXT)')
        self.cache.commit();self.rpc=LaneRpc(self.cache,self.http)
        self.worker_metrics={k:dict(enrichments=0,completed_histories=0)for k in ('live','catchup')}
    def discoveries(self,now):
        if not self.stream_path.exists():return []
        db=sqlite3.connect(self.stream_path.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)
        try:
            db.execute('PRAGMA query_only=ON')
            rows=db.execute('SELECT c.body FROM creations c JOIN creation_sessions s ON s.mint=c.mint WHERE s.session=? AND c.at BETWEEN ? AND ?',(self.session_id,now-1800,now))
            result=[]
            for body, in rows:
                c=json.loads(body)
                result.append({k:c[k]for k in ('mint','created_at','symbol','name','creator')})
            return result
        except sqlite3.OperationalError as exc:
            if 'no such table'in str(exc):return []
            raise
        finally:db.close()
    def captured_births(self,now):return set(self.live_mints)
    def select_lane(self,mint):
        lane='live'if mint in self.live_mints else'catchup'
        existing=[table for table in self.scan_tables if self.cache.execute('SELECT 1 FROM '+table+' WHERE mint=?',(mint,)).fetchone()]
        if len(existing)>1:raise SourceUnavailable('duplicate_retained_scan_state')
        self.scan_table=existing[0]if existing else lane+'_scan';self.rpc.lane=lane
        return lane
    def history(self,mint):
        self.select_lane(mint)
        return super().history(mint)
    def queue_summary(self,now):
        result={lane:dict(scans=0,initial_scans=0,pending_transactions=0,oldest_scan_age_s=0)for lane in ('live','catchup')}
        for table in self.scan_tables:
            for mint,body in self.cache.execute('SELECT mint,body FROM '+table):
                lane='live'if mint in self.live_mints else'catchup';state=json.loads(body);r=result[lane]
                r['scans']+=1;r['initial_scans']+=state.get('cursor')is None
                r['pending_transactions']+=len(state.get('pending',[]))
                if state.get('scan_at')is not None:r['oldest_scan_age_s']=max(r['oldest_scan_age_s'],max(0,now-state['scan_at']))
        return result
    def bind_creation(self,launch,creation):
        if abs(creation['created_at']-launch['created_at'])>120:raise SourceUnavailable('launch_creation_time_conflict')
        if launch.get('creator')and launch['creator']!=creation['creator']:raise SourceUnavailable('creator_identity_conflict')
        if creation['mint']!=launch['mint']:raise SourceUnavailable('creation_mint_conflict')
    def social_facts(self,creation):
        if not hasattr(self,'social_cache'):self.social_cache={}
        uri=creation['uri'];old=self.social_cache.get(uri)
        if old and 0<=time.time()-old['at']<=50:return copy.deepcopy(old['links'])
        self.social_cache.pop(uri,None)
        links=self.social(uri);self.social_cache[uri]={'at':time.time(),'links':copy.deepcopy(links)}
        return links
    @staticmethod
    def reason(exc):return str(exc)[:100]if isinstance(exc,ValueError)else type(exc).__name__
    def enrich(self,launch,now=None):
        """One history audit and one account/census pass; independent failures."""
        lane=self.select_lane(launch['mint']);f=clean(launch);f['provenance']={}
        f['collection_worker']=lane;issues={};rows=None;creation=None;at=None
        if self.rpc.quotas[lane]<=0:
            f.update(collection_attempted=False,collection_issues={'budget':lane+'_rpc_budget'},collection_issue=lane+'_rpc_budget')
            return f
        f['collection_attempted']=True;self.worker_metrics[lane]['enrichments']+=1
        before=self.metrics['completed_histories']
        try:
            rows,creation,at=self.history(f['mint'])
        except (OSError,ValueError,KeyError,TypeError,IndexError,TimeoutError)as exc:
            issues['history']=self.reason(exc);rows=None
            row=self.cache.execute('SELECT body FROM metadata WHERE mint=?',(f['mint'],)).fetchone()
            creation=json.loads(row[0])if row else None
        self.worker_metrics[lane]['completed_histories']+=self.metrics['completed_histories']-before
        if creation:
            try:self.bind_creation(launch,creation)
            except (ValueError,KeyError,TypeError)as exc:
                issues['creation']=self.reason(exc);creation=None;rows=None
        # Account cache contains only independently refreshed account facts.
        accounts,account_issues=self.account_facts(launch)
        f.update(accounts);issues.update(account_issues)
        f.update(collection_worker=lane,collection_attempted=True)
        if creation:
            f.update(created_at=creation['created_at'],creator=creation['creator'],creator_verified=True,
                uri=creation['uri'],symbol=creation.get('symbol',f.get('symbol')),name=creation.get('name',f.get('name')))
            f['provenance']['creation_signature']=creation['signature']
            snap=self.account_snapshot
            if snap and snap['mint']==f['mint']and snap['curve']==creation['curve']and 0<=time.time()-snap['at']<=60:
                try:
                    mark=curve(snap['market']['value'][1],f['mint'],creation)
                    f.update(curve_authenticated=True,curve_at=snap['at'],on_curve=mark['on_curve'],curve_progress_pct=mark['progress_pct'])
                    if not mark['on_curve']and rows is not None:
                        migrations=[r for r in rows if r.get('migration')is not None]
                        if not migrations:raise SourceUnavailable('graduation_provenance_missing')
                        latest=max(migrations,key=lambda r:r['migration']);_,expected_pool,authority=addresses(f['mint'])
                        if latest.get('pool')!=expected_pool:raise SourceUnavailable('graduated_pool_identity')
                        pool_identity(snap['market']['value'][2],f['mint'],authority)
                        f['graduated_at']=latest['migration']
                except (OSError,ValueError,KeyError,TypeError,IndexError)as exc:issues['curve']=self.reason(exc)
                if snap['holders']is not None:
                    f['dev_pct']=str(number(snap['holders'][creation['creator']])/snap['supply']*100)
            try:f['socials']=self.social_facts(creation)
            except (OSError,ValueError,KeyError,TypeError,IndexError,TimeoutError)as exc:issues['social']=self.reason(exc)
        if rows is not None:
            trades=[t for row in rows for t in row.get('trades',[])if creation['created_at']<=t['at']<=at]
            buyers={t['user']for t in trades if t['side']=='buy'}
            before_buyers={t['user']for t in trades if t['side']=='buy'and t['at']<=at-300}
            window=[t for t in trades if at-300<t['at']<=at]
            f.update(history_complete=True,history_at=at,unique_buyers=len(buyers),unique_5m_ago=len(before_buyers),
                buys_5m=sum(t['side']=='buy'for t in window),sells_5m=sum(t['side']=='sell'for t in window))
            f['provenance'].update(trade_history_hash=digest(rows),history_source='complete_finalized_signature_audit')
            try:
                blocks=self.rpc.call('getBlocks',[creation['slot'],creation['slot']+32,{'commitment':'finalized'}])
                if len(blocks)<2 or blocks[0]!=creation['slot']:raise SourceUnavailable('first_two_produced_blocks_missing')
                first={t['user']for t in trades if t['side']=='buy'and t['slot']in blocks[:2]};first.add(creation['creator'])
                f['first_blocks_complete']=True
                snap=self.account_snapshot
                if snap and snap['holders']is not None and 0<=time.time()-snap['at']<=60:
                    f['dev_first_pct']=str(sum(number(snap['holders'][x])for x in first)/snap['supply']*100)
            except (OSError,ValueError,KeyError,TypeError,IndexError)as exc:issues['first_blocks']=self.reason(exc)
        f['collection_issues']=issues
        if issues:f['collection_issue']=';'.join(k+':'+v for k,v in issues.items())[:300]
        return f
