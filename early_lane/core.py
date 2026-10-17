"""Frozen early-lane predicates and small append-only evidence journal."""
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from decimal import Decimal as D
RULES_SHA='ce4ec9f2af33afc637ac403755e3b1f567666c52cca6573c55af9b6eb994a463'
RULES_COMMIT='959cdebdea5107f48bcc03b16c3968b34dc24fbe'
FOOTER='EXPERIMENTAL early alert. Not safety-screened like scanner alerts. Most early tokens fail.'
CHECKS=('age','market_cap','curve','developer','first_two_blocks','top_holder','unique_buyers','buyer_growth','buy_share','authorities','social')

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False,default=str)
def digest(x):return hashlib.sha256(canonical(x).encode()).hexdigest()
def number(x):
    try:
        d=D(str(x))
        if not d.is_finite():raise ValueError('nonfinite')
        return d
    except Exception:raise ValueError('not_a_number')

def checks(f,now):
    now=number(now)
    result={k:'UNKNOWN' for k in CHECKS}
    def evidence(ok):
        if not ok:raise ValueError('evidence_missing_or_stale')
        return True
    def test(k,fn):
        try:result[k]='PASS' if fn() else 'FAIL'
        except (ValueError,KeyError,TypeError,ZeroDivisionError):pass
    test('age',lambda:0<=now-number(f['created_at'])<=1800)
    # Caller supplies RPC-normalized evidence, never scanner's self-asserted verdict.
    fresh=lambda key:evidence(0<=now-number(f[key])<=60)
    test('market_cap',lambda:fresh('market_at') and evidence(now<=number(f['market_expires_at']) if 'market_expires_at' in f else True) and 8000<=number(f['mc'])<=25000)
    test('curve',lambda:fresh('curve_at') and f['curve_authenticated'] is True and
         (f['on_curve'] is True or f['on_curve'] is False and 0<=now-number(f['graduated_at'])<=300) and 0<=number(f['curve_progress_pct'])<=100)
    complete=lambda:evidence(f['census_complete'] is True) and fresh('holders_at')
    test('developer',lambda:complete() and f['creator_verified'] is True and 0<=number(f['dev_pct'])<5)
    test('first_two_blocks',lambda:complete() and f['first_blocks_complete'] is True and 0<=number(f['dev_first_pct'])<15)
    test('top_holder',lambda:complete() and 0<=number(f['top_holder_pct'])<=8)
    history=lambda:evidence(f['history_complete'] is True) and fresh('history_at')
    test('unique_buyers',lambda:history() and number(f['unique_buyers'])>=25)
    test('buyer_growth',lambda:history() and now-number(f['created_at'])>=300 and evidence(number(f['unique_5m_ago'])>0) and
         number(f['unique_buyers'])/number(f['unique_5m_ago'])-1>=D('.5'))
    test('buy_share',lambda:history() and number(f['buys_5m'])>=0 and number(f['sells_5m'])>=0 and
         number(f['buys_5m'])/(number(f['buys_5m'])+number(f['sells_5m']))>=D('.6'))
    test('authorities',lambda:fresh('authority_at') and f['authorities_authenticated'] is True and f['mint_revoked'] is True and f['freeze_revoked'] is True)
    test('social',lambda:bool(f['socials']) and all(x['verified'] is True and 0<=now-number(x['checked_at'])<=60 for x in f['socials']))
    return result

class Journal:
    def __init__(self,path):
        self.db=sqlite3.connect(path,timeout=15,isolation_level=None);self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY,ts REAL NOT NULL,kind TEXT NOT NULL,key TEXT UNIQUE NOT NULL,body TEXT NOT NULL,previous TEXT NOT NULL,hash TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS event_kind ON events(kind,seq);
        CREATE INDEX IF NOT EXISTS event_mint ON events(kind,json_extract(body,'$.mint'),seq);
        CREATE TRIGGER IF NOT EXISTS no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'append only'); END;
        CREATE TRIGGER IF NOT EXISTS no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'append only'); END;''')
        self.verify()
    def atomic(self,fn):
        self.db.execute('BEGIN IMMEDIATE')
        try:r=fn();self.db.execute('COMMIT');return r
        except BaseException:self.db.execute('ROLLBACK');raise
    def add(self,kind,key,body,at=None):
        if self.db.execute('SELECT 1 FROM events WHERE key=?',(key,)).fetchone():return False
        ts=float(time.time() if at is None else at);last=self.db.execute('SELECT seq,hash FROM events ORDER BY seq DESC LIMIT 1').fetchone()
        seq=last['seq']+1 if last else 1;prev=last['hash'] if last else ''
        h=digest(dict(seq=seq,ts=ts,kind=kind,key=key,body=body,previous=prev))
        self.db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?)',(seq,ts,kind,key,canonical(body),prev,h));return True
    def rows(self,kind=None,mint=None):
        q='SELECT * FROM events';args=[]
        if kind:q+=' WHERE kind=?';args.append(kind)
        if mint is not None:q+=(' AND ' if kind else ' WHERE ')+"json_extract(body,'$.mint')=?";args.append(mint)
        q+=' ORDER BY seq'
        for r in self.db.execute(q,args):
            yield {**dict(r),'body':json.loads(r['body'])}
    def verify(self):
        prev='';n=0
        for r in self.rows():
            n+=1
            if r['seq']!=n or r['previous']!=prev or r['hash']!=digest(dict(seq=n,ts=r['ts'],kind=r['kind'],key=r['key'],body=r['body'],previous=prev)):
                raise ValueError('journal_chain_broken')
            prev=r['hash']
        return n,prev

class Lane:
    def __init__(self,journal):
        self.j=journal
        if hashlib.sha256(Path(__file__).with_name('RULES.md').read_bytes()).hexdigest()!=RULES_SHA:raise ValueError('rules_file_changed')
        binding=next(journal.rows('rules'),None)
        if binding and binding['body']['sha256']!=RULES_SHA:raise ValueError('rules_binding_changed')
        journal.atomic(lambda:journal.add('rules','rules',dict(sha256=RULES_SHA,commit=RULES_COMMIT)))
    def cohorts(self):return {r['body']['mint']:r['body'] for r in self.j.rows('cohort')}
    def activation(self):
        r=next(self.j.rows('activation'),None);return r['ts'] if r else None
    def consider(self,facts,now,live=False,log_only=True):
        """Rank one current microbatch; one immutable anchor per mint across modes."""
        output=[]
        def op():
            if live and self.activation() is None:self.j.add('activation','activation',{'rules':RULES_SHA,'source':'fresh_owner_export'},now)
            existing=self.cohorts();eligible=[]
            for f in facts:
                mint=f['mint']
                if mint in existing:continue
                c=checks(f,now)
                self.j.add('filter_audit','filter:'+mint+':'+str(int(now//60))+':'+digest(c)[:12],{'mint':mint,'checks':c,'facts':f},now)
                if all(v=='PASS' for v in c.values()):eligible.append(f)
            eligible.sort(key=lambda f:(-(number(f['unique_buyers'])/number(f['unique_5m_ago'])-1),-number(f['unique_buyers']),f['mint']))
            recent=sum(1 for x in existing.values() if x['selection']=='ALERT' and now-3600<x['at']<=now)
            for f in eligible:
                if f['mint'] in existing:continue
                chosen=recent<6
                body={'mint':f['mint'],'at':now,'mc':str(number(f['mc'])),'selection':'ALERT' if chosen else 'CAP_SUPPRESSED','facts':f,'log_only':bool(log_only)}
                if self.j.add('cohort','cohort:'+f['mint'],body,now):output.append(body);existing[f['mint']]=body
                if chosen:recent+=1
        self.j.atomic(op);return output
