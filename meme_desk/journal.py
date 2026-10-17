"""Append-only hash chain; derived state is always reconstructed from events."""
import json
import sqlite3
import time
from decimal import Decimal as D
from common import canonical, digest
SKIP_REASONS=('too_late','cost','liquidity','risk','chart','no_conviction','position_limit')

class Journal:
    def __init__(self,path):
        self.db=sqlite3.connect(path,timeout=15,isolation_level=None)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY, time REAL NOT NULL,kind TEXT NOT NULL,event_key TEXT UNIQUE NOT NULL,body TEXT NOT NULL,previous_hash TEXT NOT NULL,hash TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS immutable_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'append only'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'append only'); END;''')
        self.verify()
    def transaction(self,fn):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            self.verify();out=fn();self.db.execute('COMMIT');return out
        except BaseException:
            self.db.execute('ROLLBACK');raise
    def append(self,kind,key,body,at=None):
        if self.db.execute('SELECT 1 FROM events WHERE event_key=?',(key,)).fetchone():return False
        last=self.db.execute('SELECT seq,hash FROM events ORDER BY seq DESC LIMIT 1').fetchone()
        seq=last['seq']+1 if last else 1;prev=last['hash'] if last else ''
        at=float(time.time() if at is None else at)
        h=digest({'seq':seq,'time':at,'kind':kind,'key':key,'body':body,'previous_hash':prev})
        self.db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?)',(seq,at,kind,key,canonical(body),prev,h));return True
    def verify(self):
        prev='';seq=0
        for r in self.db.execute('SELECT * FROM events ORDER BY seq'):
            seq+=1
            expected=digest({'seq':seq,'time':r['time'],'kind':r['kind'],'key':r['event_key'],'body':json.loads(r['body']),'previous_hash':prev})
            if r['seq']!=seq or r['previous_hash']!=prev or r['hash']!=expected:raise ValueError('journal_hash_chain_broken')
            prev=r['hash']
        return seq,prev
    def state(self,now=None):
        now=time.time() if now is None else now
        today=time.strftime('%Y-%m-%d',time.gmtime(now))
        tickets={};open_positions=set();actions={};daily_loss=D(0);losses=D(0);enabled=True;delivered=set();attempts={};closed=set()
        for r in self.db.execute('SELECT * FROM events ORDER BY seq'):
            b=json.loads(r['body']);k=r['kind']
            if k=='ticket':tickets[b['id']]=b
            elif k=='button':
                actions[b['ticket']]=b['action']
                if b['action']=='TAKEN':open_positions.add(b['ticket'])
            elif k=='position_closed':
                open_positions.discard(b['ticket']);closed.add(b['ticket'])
                loss=max(D(0),-D(b['net_pnl_usd']));losses+=loss
                if time.strftime('%Y-%m-%d',time.gmtime(r['time']))==today:daily_loss+=loss
                if loss>0 and losses>=25:enabled=False
            elif k=='owner_reenable':enabled=True
            elif k=='delivered':delivered.add(b['ticket'])
            elif k=='delivery_attempt':attempts[b['ticket']]=b
        return dict(tickets=tickets,open_positions=open_positions,actions=actions,daily_loss=daily_loss,cumulative_loss=losses,enabled=enabled,delivered=delivered,attempts=attempts,closed=closed)
    def button(self,key,ticket,action,reason=None,now=None):
        def op():
            state=self.state(now)
            if ticket not in state['tickets']:raise ValueError('unknown_ticket')
            if action not in ('TAKEN','SKIP'):raise ValueError('unknown_action')
            if action=='SKIP' and reason not in SKIP_REASONS:raise ValueError('skip_reason_required')
            if ticket in state['actions']:return False
            if action=='TAKEN' and len(state['open_positions'])>=3:raise ValueError('three_open_positions')
            return self.append('button','button:'+key,dict(ticket=ticket,action=action,reason=reason,manual_mark_only=True,review_warning=state['daily_loss']>=15 or not state['enabled']),now)
        return self.transaction(op)
    def close(self,key,ticket,pnl,now=None):
        def op():
            s=self.state(now)
            if ticket not in s['open_positions']:raise ValueError('position_not_open_or_already_closed')
            value=D(str(pnl))
            if not value.is_finite():raise ValueError('nonfinite_pnl')
            return self.append('position_closed','close:'+key,dict(ticket=ticket,net_pnl_usd=str(value),source='OWNER_ATTESTED_MANUAL; not reconciled fills'),now)
        return self.transaction(op)
    def reenable(self,key,reason,now=None):
        if not reason.strip():raise ValueError('reason_required')
        return self.transaction(lambda:self.append('owner_reenable','reenable:'+key,{'reason':reason},now))
