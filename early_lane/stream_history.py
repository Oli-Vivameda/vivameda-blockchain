"""Finalized signature audit + captured log reuse; demand-driven canonical repairs.

Stream continuity is never a completeness proof. Every successful mint signature
must be accounted for, from creation through a fresh finalized RPC snapshot.
Creation, migrations, AMM, conflicting and absent notifications use full RPC bodies.
This module cannot send Telegram messages or change frozen predicates.
"""
import copy
import json
from pathlib import Path
import sqlite3
import time
from core import canonical,digest
from evidence import EvidenceCollector
from pump import decode_tx,b58decode
from sources import SourceUnavailable

def confirmed_failed(entry):
    error=entry.get("err")
    return entry.get("confirmationStatus")=="finalized" and ((isinstance(error,dict)and bool(error))or(isinstance(error,str)and bool(error)))

class StreamCollector(EvidenceCollector):
    scan_table='stream_scan'
    scan_tables=('stream_scan',)
    def __init__(self,path,stream_path,http=None):
        super().__init__(path,http)
        self.stream_path=Path(stream_path)/'stream_cache.sqlite3'
        self.cache.executescript('''
        CREATE TABLE IF NOT EXISTS stream_scan(mint TEXT PRIMARY KEY,body TEXT);
        CREATE TABLE IF NOT EXISTS repair(signature TEXT PRIMARY KEY,slot INTEGER,status TEXT,attempts INTEGER,next_at REAL,body TEXT);
        CREATE TABLE IF NOT EXISTS stream_proofs(mint TEXT PRIMARY KEY,at REAL,body TEXT);
        ''')
        self.metrics={'reused_stream_transactions':0,'canonical_repairs':0,'failed_signatures_skipped':0,'completed_histories':0}
    def captured(self,entry,mint,db=None):
        """A finalized signature + slot + blockTime binds a complete log event set.

        Read a transactionally consistent snapshot. The capture process has its
        own SQLite connection; no protected scanner/state database is opened.
        """
        if db is not None:return self.captured_row(db,entry,mint)
        if not self.stream_path.exists():return None
        conn=sqlite3.connect(self.stream_path.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)
        try:
            conn.execute('PRAGMA query_only=ON')
            return self.captured_row(conn,entry,mint)
        except sqlite3.OperationalError:return None
        finally:conn.close()
    def captured_row(self,db,entry,mint):
        row=db.execute('SELECT slot,body,conflict FROM captured_transactions WHERE signature=?',(entry['signature'],)).fetchone()
        if not row or row[2] or row[0]!=entry['slot']:return None
        if db.execute('SELECT 1 FROM transaction_gaps WHERE signature=?',(entry['signature'],)).fetchone():return None
        item=json.loads(row[1]);stamp=entry.get('blockTime')
        if type(stamp)is not int or not item.get('fast_path_safe')or item.get('failed')or item.get('creations')or item.get('amm_seen'):return None
        if item.get('signature')!=entry['signature']:return None
        trades=[copy.deepcopy(t)for t in item['trades']if t['mint']==mint]
        if not trades:return None
        for trade in trades:
            if abs(trade['at']-stamp)>30:return None
            trade.update(at=stamp,slot=entry['slot'])
        return dict(signature=entry['signature'],slot=entry['slot'],at=stamp,trades=trades,creation=None,migration=None,pool=None,complete=True,evidence_hash=item['source_hash'],source='finalized_signature_bound_program_logs')
    def canonical_transaction(self,entry):
        sig=entry['signature'];now=time.time()
        row=self.cache.execute('SELECT slot,status,attempts,next_at,body FROM repair WHERE signature=?',(sig,)).fetchone()
        if row and row['slot']!=entry['slot']:raise SourceUnavailable('finalized_signature_slot_conflict')
        if row and row['status']=='DONE':
            tx=json.loads(row['body']);self.validate_transaction(tx,entry);return tx
        if row and now<row['next_at']:raise SourceUnavailable('transaction_repair_wait')
        attempts=(row['attempts']if row else 0)+1
        self.cache.execute('INSERT OR REPLACE INTO repair VALUES(?,?,?,?,?,NULL)',(sig,entry['slot'],'PENDING',attempts,now+5));self.cache.commit()
        tx=self.rpc.call('getTransaction',[sig,{'encoding':'jsonParsed','commitment':'finalized','maxSupportedTransactionVersion':1}])
        if tx is None:raise SourceUnavailable('transaction_gap_retry')
        self.validate_transaction(tx,entry)
        body=canonical(tx)
        used=self.cache.execute('SELECT COALESCE(SUM(LENGTH(body)),0) FROM repair').fetchone()[0]
        if used+len(body.encode())>128*1024**2:raise SourceUnavailable('repair_cache_bound')
        self.cache.execute("UPDATE repair SET status='DONE',body=? WHERE signature=?",(body,sig));self.cache.commit();self.metrics['canonical_repairs']+=1
        return tx
    @staticmethod
    def validate_transaction(tx,entry):
        sig=entry['signature']
        # Never take a caller-supplied signature as evidence of returned identity.
        if tx.get('transaction',{}).get('signatures',[None])[0]!=sig or tx.get('slot')!=entry['slot']:raise SourceUnavailable('canonical_transaction_identity')
        if tx.get('meta',{}).get('err','missing')is not None:raise SourceUnavailable('canonical_success_status_conflict')
        if type(tx.get('blockTime'))is not int or entry.get('blockTime')is not None and tx['blockTime']!=entry['blockTime']:raise SourceUnavailable('canonical_block_time_conflict')
    def parsed(self,entry,mint,local_only=False,capture_db=None,commit=True):
        old=self.cache.execute('SELECT body,slot FROM tx WHERE mint=? AND sig=?',(mint,entry['signature'])).fetchone()
        if old:
            parsed=json.loads(old['body'])
            if old['slot']!=entry['slot'] or bool(parsed.get('failed'))!=bool(confirmed_failed(entry)):raise SourceUnavailable('cached_finalized_slot_or_status_conflict')
            if parsed.get('at')is not None and entry.get('blockTime')is not None and parsed['at']!=entry['blockTime']:raise SourceUnavailable('cached_finalized_time_conflict')
            return parsed
        if confirmed_failed(entry):
            out=dict(signature=entry['signature'],slot=entry['slot'],trades=[],failed=True,complete=True,status_evidence_hash=digest(entry))
            self.metrics['failed_signatures_skipped']+=1
        else:
            out=self.captured(entry,mint,capture_db)
            if out:self.metrics['reused_stream_transactions']+=1
            else:
                if local_only:return None
                tx=self.canonical_transaction(entry)
                try:out=decode_tx(tx,mint,entry['signature'])
                except (ValueError,KeyError,TypeError,IndexError)as exc:out=dict(signature=entry['signature'],slot=entry['slot'],error=str(exc)[:100])
        self.cache.execute('INSERT INTO tx VALUES(?,?,?,?)',(mint,entry['signature'],entry['slot'],canonical(out)))
        if out.get('creation'):self.cache.execute('INSERT OR REPLACE INTO metadata VALUES(?,?)',(mint,canonical(out['creation'])))
        if commit:self.cache.commit()
        return out
    @staticmethod
    def validate_page(page):
        if not isinstance(page,list)or len(page)>1000:raise SourceUnavailable('signature_page_shape')
        seen=set();previous=None
        for entry in page:
            sig=entry.get('signature');slot=entry.get('slot')
            try:valid=len(b58decode(sig))==64
            except ValueError:valid=False
            error=entry.get('err','missing')
            if not valid or sig in seen or type(slot)is not int or slot<0 or previous is not None and slot>previous:raise SourceUnavailable('signature_page_identity_or_order')
            if entry.get('confirmationStatus')!='finalized' or 'err'not in entry or error is not None and not confirmed_failed(entry):raise SourceUnavailable('signature_status_not_finalized')
            seen.add(sig);previous=slot
    def reconcile_conflicts(self,mint):
        if not self.stream_path.exists():return
        db=sqlite3.connect(self.stream_path.resolve().as_uri()+'?mode=ro',uri=True)
        try:
            db.execute('PRAGMA query_only=ON')
            conflicts={r[0]for r in db.execute('SELECT signature FROM captured_transactions WHERE conflict=1 UNION SELECT signature FROM transaction_gaps')}
        finally:db.close()
        for row in self.cache.execute('SELECT sig,body FROM tx WHERE mint=?',(mint,)).fetchall():
            old=json.loads(row['body'])
            if row['sig']not in conflicts or old.get('source')!='finalized_signature_bound_program_logs':continue
            entry=dict(signature=row['sig'],slot=old['slot'],blockTime=old['at'],err=None,confirmationStatus='finalized')
            tx=self.canonical_transaction(entry)
            try:parsed=decode_tx(tx,mint,row['sig'])
            except (ValueError,KeyError,TypeError,IndexError)as exc:raise SourceUnavailable('conflicting_stream_transaction_unresolved')from exc
            self.cache.execute('UPDATE tx SET body=? WHERE mint=? AND sig=?',(canonical(parsed),mint,row['sig']));self.cache.commit()

    def compact_stream_pending(self,mint,state):
        """Drain local evidence across the queue before any network repair.
        
        These entries already passed finalized signature validation. A cache hit
        still checks signature, slot, status and timestamp. No missing entry is
        discarded. Partial cache commits are safe to replay after interruption.
        """
        conn=None
        try:
            if self.stream_path.exists():
                conn=sqlite3.connect(self.stream_path.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)
                conn.execute('PRAGMA query_only=ON');conn.execute('BEGIN')
            pending=[]
            for i,entry in enumerate(state['pending']):
                out=self.parsed(entry,mint,local_only=True,capture_db=conn,commit=False)
                if out is None:pending.append(entry)
                if i%500==499:self.cache.commit()
            self.cache.commit();state['pending']=pending
        finally:
            if conn is not None:conn.close()

    def captured_births(self,now):
        """Scheduling hint only; cannot grant creation or history verification."""
        if not self.stream_path.exists():return set()
        db=sqlite3.connect(self.stream_path.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)
        try:
            db.execute('PRAGMA query_only=ON')
            return {r[0]for r in db.execute('SELECT mint FROM creations WHERE at BETWEEN ? AND ?',(now-1800,now))}
        finally:db.close()

    def queue_summary(self,now):
        states=[json.loads(r[0])for r in self.cache.execute('SELECT body FROM '+self.scan_table)]
        return dict(scans=len(states),initial_scans=sum(x.get('cursor')is None for x in states),
            pending_transactions=sum(len(x.get('pending',[]))for x in states),
            oldest_scan_age_s=max((max(0,now-x['scan_at'])for x in states if x.get('scan_at')is not None),default=0))

    def history(self,mint):
        row=self.cache.execute('SELECT body FROM '+self.scan_table+' WHERE mint=?',(mint,)).fetchone()
        s=json.loads(row[0])if row else dict(cursor=None,before=None,head=None,pending=[],paging_done=False,scan_at=None,last_slot=None)
        def save():
            self.cache.execute('INSERT OR REPLACE INTO '+self.scan_table+' VALUES(?,?)',(mint,canonical(s)));self.cache.commit()
        self.compact_stream_pending(mint,s);save()
        while not s['paging_done']:
            options={'limit':1000,'commitment':'finalized'}
            if s['before']:options['before']=s['before']
            page=self.rpc.call('getSignaturesForAddress',[mint,options]);self.validate_page(page)
            if s['scan_at']is None:s['scan_at']=time.time();s['head']=page[0]['signature']if page else s['cursor']
            if page and s['last_slot']is not None and page[0]['slot']>s['last_slot']:raise SourceUnavailable('signature_pagination_order')
            boundary=next((i for i,x in enumerate(page)if x['signature']==s['cursor']),None)
            selected=page[:boundary]if boundary is not None else page
            pending={x['signature']:x for x in s['pending']}
            for entry in selected:
                if entry['signature']in pending and pending[entry['signature']]!=entry:raise SourceUnavailable('signature_duplicate_conflict')
                if not self.cache.execute('SELECT 1 FROM tx WHERE mint=? AND sig=?',(mint,entry['signature'])).fetchone():pending[entry['signature']]=entry
            s['pending']=list(pending.values())
            self.compact_stream_pending(mint,s)
            if len(s['pending'])>10000:raise SourceUnavailable('transaction_backlog_bound')
            if boundary is not None or len(page)<1000:
                if s['cursor']and boundary is None:raise SourceUnavailable('rpc_history_cursor_gap')
                s['paging_done']=True
            else:
                if page[-1]['signature']==s['before']:raise SourceUnavailable('history_pagination_not_advancing')
                s['before']=page[-1]['signature'];s['last_slot']=page[-1]['slot']
            save()
        s['pending'].sort(key=lambda x:(x['slot'],x['signature']))
        while s['pending']:
            self.parsed(s['pending'][0],mint);s['pending'].pop(0);save()
        self.reconcile_conflicts(mint)
        stamp=s['scan_at'];head=s['head']
        s=dict(cursor=head,before=None,head=None,pending=[],paging_done=False,scan_at=None,last_slot=None);save()
        rows=[json.loads(r[0])for r in self.cache.execute('SELECT body FROM tx WHERE mint=? ORDER BY slot,sig',(mint,))]
        if any(x.get('complete')is not True or 'error'in x for x in rows):raise SourceUnavailable('unsupported_or_incomplete_trade_history')
        origins=[r['creation']for r in rows if r.get('creation')]
        if len(origins)!=1:raise SourceUnavailable('creation_provenance_missing_or_conflicting')
        creation=origins[0]
        if not creation.get('initial_supply')or not creation.get('initial_curve_tokens'):raise SourceUnavailable('creation_reserves_missing')
        # Stale completed work advances the cursor, but never grants fresh evidence.
        if not 0<=time.time()-stamp<=60:raise SourceUnavailable('signature_audit_stale_catching_up')
        proof=dict(at=stamp,head=head,rows=len(rows),history_hash=digest(rows),source='complete_finalized_mint_signature_audit')
        self.cache.execute('INSERT OR REPLACE INTO stream_proofs VALUES(?,?,?)',(mint,stamp,canonical(proof)));self.cache.commit();self.metrics['completed_histories']+=1
        return rows,creation,stamp
    def prune(self,active):
        super().prune(active)
        for table in (*self.scan_tables,'stream_proofs'):
            for row in self.cache.execute('SELECT mint FROM '+table).fetchall():
                if row[0]not in active:self.cache.execute('DELETE FROM '+table+' WHERE mint=?',(row[0],))
        # Shared full bodies only serve active watch-window scans. Preserve hashes
        # in the lane journal, not an unbounded raw transaction archive.
        needed={r[0]for r in self.cache.execute('SELECT sig FROM tx')}
        for row in self.cache.execute(' UNION ALL '.join('SELECT body FROM '+table for table in self.scan_tables)):
            needed.update(x['signature']for x in json.loads(row[0]).get('pending',[]))
        for row in self.cache.execute('SELECT signature FROM repair').fetchall():
            if row[0]not in needed:self.cache.execute('DELETE FROM repair WHERE signature=?',(row[0],))
        self.cache.commit()
