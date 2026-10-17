"""Bounded live Pump log shadow capture. Never executes lane admission or delivery."""
from collections import Counter
import argparse
import fcntl
import json
import shutil
import signal
import socket
import sqlite3
import time
import uuid
from pathlib import Path
from core import Journal,canonical,digest
from pump import PUMP
from stream_events import normalize,StreamGap
from stream_wire import PublicSocket,Refused

class Capture:
    def __init__(self,state,session_id=None):
        self.session_id=session_id or uuid.uuid4().hex
        if not isinstance(self.session_id,str) or not 1<=len(self.session_id)<=64 or not self.session_id.isalnum():raise ValueError('capture_session_id')
        self.path=Path(state);self.path.mkdir(parents=True,exist_ok=True,mode=0o750)
        self.db=sqlite3.connect(self.path/'stream_cache.sqlite3');self.db.row_factory=sqlite3.Row
        self.db.executescript('''PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;
        CREATE TABLE IF NOT EXISTS config(key TEXT PRIMARY KEY,body TEXT);
        CREATE TABLE IF NOT EXISTS notifications(signature TEXT PRIMARY KEY,slot INTEGER,observed_at REAL,body_hash TEXT);
        CREATE TABLE IF NOT EXISTS creations(mint TEXT PRIMARY KEY,at REAL,generation INTEGER,body TEXT);
        CREATE TABLE IF NOT EXISTS creation_sessions(mint TEXT PRIMARY KEY,session TEXT,observed_at REAL);
        CREATE TABLE IF NOT EXISTS trades(signature TEXT,event TEXT,mint TEXT,at REAL,slot INTEGER,generation INTEGER,body TEXT,PRIMARY KEY(signature,event));
        CREATE INDEX IF NOT EXISTS trade_mint ON trades(mint,slot,signature);
        CREATE TABLE IF NOT EXISTS mint_gaps(mint TEXT PRIMARY KEY,at REAL,reason TEXT);
        CREATE TABLE IF NOT EXISTS captured_transactions(signature TEXT PRIMARY KEY,slot INTEGER,observed_at REAL,body TEXT,conflict INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS transaction_gaps(signature TEXT PRIMARY KEY,slot INTEGER,observed_at REAL,reason TEXT);
        CREATE TABLE IF NOT EXISTS recoveries(mint TEXT PRIMARY KEY,at REAL,generation INTEGER,body TEXT);
        ''')
        self.audit=Journal(self.path/'stream_audit.sqlite3');self.subs={};self.counts={k:0 for k in('notifications','failed','duplicates','creations','trades','gaps','root_updates','non_economic_notifications','scoped_gaps','global_gaps')}
    def get(self,key,default=None):
        row=self.db.execute('SELECT body FROM config WHERE key=?',(key,)).fetchone();return json.loads(row[0])if row else default
    def put(self,key,value):self.db.execute('INSERT OR REPLACE INTO config VALUES(?,?)',(key,canonical(value)))
    def note(self,kind,body,at):
        key=kind+':'+str(at)+':'+digest(body)
        self.audit.atomic(lambda:self.audit.add(kind,key,body,at))
    def begin(self,at):
        self.subs={};g=self.get('generation',0)+1
        with self.db:self.put('generation',g);self.put('ready',False);self.put('connected_at',at);self.put('last_log_at',None);self.put('root_at',None)
        self.note('stream_open',{'generation':g,'admissible_for_screening':False},at)
    def gap(self,reason,at,mints=None):
        self.counts['gaps']+=1
        if mints:
            with self.db:
                for mint in mints:self.db.execute('INSERT OR REPLACE INTO mint_gaps VALUES(?,?,?)',(mint,at,reason))
            self.counts['scoped_gaps']+=1
            self.note('stream_gap',{'generation':self.get('generation',0),'reason':reason,'mints':mints,'scope':'affected_transaction_mints'},at)
        else:
            self.counts['global_gaps']+=1;g=self.get('generation',0)+1
            with self.db:self.put('generation',g);self.put('last_gap_at',at)
            self.note('stream_gap',{'generation':g,'reason':reason,'scope':'global'},at)
    def disconnect(self,reason,at):
        with self.db:self.put('ready',False)
        self.gap(reason,at)
    def ingest(self,message,now):
        if not isinstance(message,dict):raise StreamGap('response_shape')
        if 'id'in message:
            ident=message['id']
            if type(ident)is not int or ident not in(1,2)or ident in self.subs:raise StreamGap('subscription_response_id')
            if 'error'in message:raise StreamGap('required_subscription_unavailable')
            sub=message.get('result')
            if type(sub)is not int or sub<0 or sub in self.subs.values():raise StreamGap('subscription_response_shape')
            self.subs[ident]=sub
            if set(self.subs)=={1,2}:
                with self.db:self.put('ready',True);self.put('acknowledged_at',now)
            return
        params=message.get('params',{});kind=message.get('method')
        if kind=='rootNotification':
            if params.get('subscription')!=self.subs.get(2)or 2 not in self.subs:raise StreamGap('wrong_root_subscription')
            slot=params.get('result')
            if type(slot)is not int or slot<self.get('root_slot',0):raise StreamGap('root_regression_or_shape')
            with self.db:self.put('root_slot',slot);self.put('root_at',now)
            self.counts['root_updates']+=1;return
        if kind!='logsNotification'or 1 not in self.subs or params.get('subscription')!=self.subs[1]:raise StreamGap('unexpected_notification')
        result=params.get('result',{});slot=result.get('context',{}).get('slot')
        if type(slot)is not int or slot<=0:raise StreamGap('log_slot_shape')
        value=result.get('value')
        try:item=normalize(value,now)
        except StreamGap as exc:
            # Repair is demand-driven: queue one signature, never all mint history.
            # Unlocatable/malformed signatures remain a global stream gap.
            from stream_events import address
            signature=address(value.get('signature'),64)if isinstance(value,dict)else None
            if signature:
                with self.db:
                    self.db.execute('INSERT OR REPLACE INTO transaction_gaps VALUES(?,?,?,?)',(signature,slot,now,str(exc)))
                    self.db.execute('UPDATE captured_transactions SET conflict=1 WHERE signature=?',(signature,))
            raise
        signature=item['signature'];h=item['source_hash']
        if item.get('fast_path_safe'):
            old=self.db.execute('SELECT body,slot FROM captured_transactions WHERE signature=?',(signature,)).fetchone()
            with self.db:
                if old and (json.loads(old['body'])['source_hash']!=h or old['slot']!=slot):
                    self.db.execute('UPDATE captured_transactions SET conflict=1 WHERE signature=?',(signature,))
                    self.db.execute('INSERT OR REPLACE INTO transaction_gaps VALUES(?,?,?,?)',(signature,slot,now,'conflicting_signature_notification'))
                else:self.db.execute('INSERT OR IGNORE INTO captured_transactions VALUES(?,?,?,?,0)',(signature,slot,now,canonical(item)))
        if item['failed']or not(item['trades']or item['creations']):
            self.counts['notifications']+=1;self.counts['failed']+=item['failed'];self.counts['non_economic_notifications']+=not item['failed']
            if now-(self.get('last_log_at',0)or 0)>=1:
                with self.db:self.put('last_log_at',now);self.put('log_slot',max(slot,self.get('log_slot',0)))
            return
        old=self.db.execute('SELECT body_hash FROM notifications WHERE signature=?',(signature,)).fetchone()
        if old:
            if old[0]!=h:
                with self.db:
                    self.db.execute('UPDATE captured_transactions SET conflict=1 WHERE signature=?',(signature,))
                    self.db.execute('INSERT OR REPLACE INTO transaction_gaps VALUES(?,?,?,?)',(signature,slot,now,'conflicting_signature_notification'))
                raise StreamGap('conflicting_signature_notification')
            self.counts['duplicates']+=1;return
        g=self.get('generation',0)
        with self.db:
            self.put('last_log_at',now);self.put('log_slot',max(slot,self.get('log_slot',0)))
            self.db.execute('INSERT INTO notifications VALUES(?,?,?,?)',(signature,slot,now,h))
            for c in item['creations']:
                old=self.db.execute('SELECT body FROM creations WHERE mint=?',(c['mint'],)).fetchone()
                if old and json.loads(old[0])!=c:raise StreamGap('conflicting_creation')
                self.db.execute('INSERT OR IGNORE INTO creations VALUES(?,?,?,?)',(c['mint'],c['created_at'],g,canonical(c)))
                self.db.execute('INSERT OR IGNORE INTO creation_sessions VALUES(?,?,?)',(c['mint'],self.session_id,now))
            for trade in item['trades']:
                trade.update(slot=slot,source='public_rpc_pump_log_shadow',source_hash=h,admissible_for_screening=False)
                self.db.execute('INSERT INTO trades VALUES(?,?,?,?,?,?,?)',(signature,trade['event'],trade['mint'],trade['at'],slot,g,canonical(trade)))
        self.counts['notifications']+=1;self.counts['failed']+=item['failed'];self.counts['creations']+=len(item['creations']);self.counts['trades']+=len(item['trades'])
    def recover(self,mint,collector,now=None):
        """Only complete, fresh original RPC history can recover a gap.

        This proof covers that RPC snapshot, never future stream observations.
        Both admissions and any stream-only history-complete shortcut stay disabled.
        """
        clock=time.time if now is None else lambda:now
        rows,creation,at=collector.history(mint);end=clock()
        local_gap=self.db.execute('SELECT at FROM mint_gaps WHERE mint=?',(mint,)).fetchone()
        if not 0<=end-at<=60 or at<(local_gap[0]if local_gap else 0)or at<self.get('last_gap_at',0)or at<self.get('connected_at',0):raise StreamGap('recovery_incomplete_or_stale_interval')
        if creation.get('mint')!=mint or creation.get('created_at',at+1)>at or not creation.get('signature'):raise StreamGap('recovery_creation_identity')
        if not any(x.get('creation')==creation for x in rows)or any('error'in x or x.get('complete')is not True for x in rows):raise StreamGap('recovery_incomplete_rows')
        known=self.db.execute('SELECT body FROM creations WHERE mint=?',(mint,)).fetchone()
        if known:
            known=json.loads(known[0])
            if any(known.get(k)!=creation.get(k)for k in('mint','curve','creator','created_at','signature','initial_supply','initial_curve_tokens')):raise StreamGap('recovery_creation_conflict')
        key=lambda signature,t:(signature,t.get('event'),t['user'],t['side'],t['at'],t['qty'],t.get('quote_lamports'))
        reference=Counter(key(row['signature'],t)for row in rows for t in row.get('trades',[]))
        observed=[json.loads(r[0])for r in self.db.execute('SELECT body FROM trades WHERE mint=? AND at<=?',(mint,at))]
        mismatches=Counter(key(t['signature'],t)for t in observed)-reference
        if mismatches:raise StreamGap('recovery_stream_rpc_mismatch')
        body=dict(source='complete_rpc_history',at=at,reference_hash=digest(rows),reference_rows=len(rows),stream_rows_compared=len(observed),creation_hash=digest(creation),admissible_for_screening=False)
        g=self.get('generation',0)
        self.note('gap_recovery',dict(mint=mint,**body),end)
        with self.db:self.db.execute('INSERT OR REPLACE INTO recoveries VALUES(?,?,?,?)',(mint,at,g,canonical(body)))
        return body
    def coverage(self,mint,now):
        """Describe proof boundaries without promoting provisional stream data."""
        out={'admissible_for_screening':False,'status':'CAPTURED_UNVERIFIED','covered_through':None}
        row=self.db.execute('SELECT at,generation,body FROM recoveries WHERE mint=?',(mint,)).fetchone()
        local_gap=self.db.execute('SELECT at FROM mint_gaps WHERE mint=?',(mint,)).fetchone()
        if row and row['generation']==self.get('generation')and row['at']>=(local_gap[0]if local_gap else 0):
            out['covered_through']=row['at'];out['status']='RPC_SNAPSHOT_VERIFIED'if 0<=now-row['at']<=60 else'RECOVERY_STALE'
            return out
        if not self.get('ready',False):out['status']='STREAM_OFFLINE';return out
        creation=self.db.execute('SELECT generation FROM creations WHERE mint=?',(mint,)).fetchone()
        if local_gap or not creation or creation[0]!=self.get('generation'):out['status']='GAP_NEEDS_RPC'
        return out
    def prune(self,now):
        with self.db:
            self.db.execute('DELETE FROM captured_transactions WHERE observed_at<?',(now-1860,))
            self.db.execute('DELETE FROM transaction_gaps WHERE observed_at<?',(now-1860,))
            self.db.execute('DELETE FROM notifications WHERE observed_at<?',(now-1860,))
            self.db.execute('DELETE FROM creations WHERE at<?',(now-1860,))
            self.db.execute('DELETE FROM creation_sessions WHERE observed_at<?',(now-1860,))
            self.db.execute('DELETE FROM trades WHERE at<?',(now-1860,))
            self.db.execute('DELETE FROM recoveries WHERE at<?',(now-1860,))
            self.db.execute('DELETE FROM mint_gaps WHERE at<?',(now-1860,))
        if (self.path/'stream_cache.sqlite3').stat().st_size>256*1024**2:raise ValueError('stream_cache_bound')
    def report(self):
        return dict(**self.counts,retained_trades=self.db.execute('SELECT COUNT(*) FROM trades').fetchone()[0],retained_creations=self.db.execute('SELECT COUNT(*) FROM creations').fetchone()[0],generation=self.get('generation',0),subscription_ready=self.get('ready',False),admissible_for_screening=False,telegram_sent=0)
    def close(self):self.db.close();self.audit.db.close()

def run(state,duration=60,session_id=None):
    if not 1<=duration<=7200:raise ValueError('bounded_shadow_duration_1_to_7200_seconds')
    path=Path(state);path.mkdir(parents=True,exist_ok=True,mode=0o750)
    lock=open(path/'stream_process.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    capture=Capture(path,session_id);until=time.monotonic()+duration;start=time.time();running=True;attempts=0;last_ping=0;last_prune=0
    def stop(*_):
        nonlocal running
        running=False
    old_handlers={s:signal.signal(s,stop)for s in(signal.SIGTERM,signal.SIGINT)}
    try:
        while running and time.monotonic()<until:
            if shutil.disk_usage(path).free<3*1024**3:raise ValueError('disk_reserve_below_3GiB')
            cooldown=capture.get('cooldown',0)
            if time.time()<cooldown:time.sleep(min(1,cooldown-time.time()));continue
            ws=PublicSocket();attempts+=1;capture.begin(time.time())
            try:
                ws.connect();ws.subscribe(1,PUMP);ws.subscribe(2);last_rx=time.time();last_ping=last_rx
                while running and time.monotonic()<until:
                    now=time.time()
                    if now-last_ping>=15:ws.ping();last_ping=now
                    if now-last_rx>30:raise StreamGap('stream_silence')
                    try:message=ws.receive()
                    except socket.timeout:continue
                    last_rx=time.time()
                    try:capture.ingest(message,last_rx)
                    except StreamGap as exc:capture.gap(str(exc),last_rx,getattr(exc,'mints',None))
                    if last_rx-last_prune>=5:
                        capture.prune(last_rx);last_prune=last_rx
                        if shutil.disk_usage(path).free<3*1024**3:raise ValueError('disk_reserve_below_3GiB')
            except (OSError,ValueError,KeyError,TypeError,IndexError)as exc:
                reason=str(exc)if isinstance(exc,(StreamGap,ValueError))else type(exc).__name__;capture.disconnect(reason[:100],time.time())
                delay=exc.retry_after if isinstance(exc,Refused)else min(60,2**min(attempts,6))
                with capture.db:capture.put('cooldown',time.time()+max(1,delay))
            finally:ws.close()
        capture.disconnect('shadow_stopped',time.time());result=capture.report();result.update(duration_s=time.time()-start,attempts=attempts,mode='STREAM_SHADOW_ONLY')
        from exporter import atomic
        atomic(path/'stream_receipt.json',result);return result
    finally:
        capture.close();lock.close()
        for s,h in old_handlers.items():signal.signal(s,h)

def main():
    p=argparse.ArgumentParser();p.add_argument('--state-dir',required=True);p.add_argument('--duration',type=int,default=60);a=p.parse_args();print(canonical(run(a.state_dir,a.duration)))
if __name__=='__main__':main()
