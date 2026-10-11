"""Independent free profile discovery and private shadow evidence; no Telegram/trading."""
import argparse, hashlib, json, math, re, sqlite3, time, urllib.request
from pathlib import Path
from classifier import POLICY

STATE=Path('/var/lib/vivameda-super-small-cap')
ADDRESS=re.compile(r'[1-9A-HJ-NP-Za-km-z]{32,44}')
MAX_BYTES=512*1024*1024

def number(x):return type(x) in (int,float) and math.isfinite(x)
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('redirect refused')
def fetch(path):
    # Only fixed provider endpoints and validated token addresses reach this function.
    if not (path=='token-profiles/latest/v1' or path.startswith('tokens/v1/solana/')):raise ValueError('endpoint')
    request=urllib.request.Request('https://api.dexscreener.com/'+path,headers={'User-Agent':'Vivameda-Super-Small-Cap/1.0'})
    with urllib.request.build_opener(NoRedirect).open(request,timeout=8) as r:
        raw=r.read(1024*1024+1)
        if len(raw)>1024*1024:raise ValueError('response cap')
    return json.loads(raw),hashlib.sha256(raw).hexdigest()

def connect(path):
    c=sqlite3.connect(path,timeout=2)
    c.executescript('''
    CREATE TABLE IF NOT EXISTS tokens(mint TEXT PRIMARY KEY,discovered_at INTEGER,refreshed_at INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS observations(mint TEXT,pair TEXT,received_at INTEGER,price REAL,mc REAL,liq REAL,body TEXT,PRIMARY KEY(mint,pair,received_at));
    CREATE TABLE IF NOT EXISTS entries(mint TEXT PRIMARY KEY,pair TEXT,decision_ts INTEGER,price REAL,mc REAL,policy TEXT,body TEXT);
    CREATE TABLE IF NOT EXISTS runs(ts INTEGER PRIMARY KEY,body TEXT);
    ''');return c

def ingest(c,rows,now,response_hash):
    count=0
    if not isinstance(rows,list):raise ValueError('pair response')
    for r in rows:
        if not isinstance(r,dict) or r.get('chainId')!='solana':continue
        mint=r.get('baseToken',{}).get('address','');pair=r.get('pairAddress','')
        if not isinstance(mint,str) or not isinstance(pair,str) or not ADDRESS.fullmatch(mint) or not ADDRESS.fullmatch(pair):continue
        if not c.execute('SELECT 1 FROM tokens WHERE mint=?',(mint,)).fetchone():continue
        try:price=float(r.get('priceUsd'))
        except (ValueError,TypeError):continue
        mc=r.get('marketCap');liq=(r.get('liquidity') or {}).get('usd')
        if not number(price) or price<=0 or not number(mc) or mc<=0:continue
        body={'source':'dexscreener_pair','response_sha256':response_hash,'received_at':now,'provider_event_time':None,
              'txns_m5':r.get('txns',{}).get('m5'),'volume_m5':r.get('volume',{}).get('m5'),
              'organic_buyers':'UNKNOWN','executable_exit':'UNKNOWN','cap_source':'provider_marketCap_not_fdv'}
        raw=json.dumps(body,sort_keys=True,allow_nan=False)
        c.execute('INSERT OR IGNORE INTO observations VALUES(?,?,?,?,?,?,?)',(mint,pair,now,price,mc,liq if number(liq) else None,raw));count+=1
        if 10000<=mc<=20000:
            entry=dict(body,classification='DISCOVERY',trigger='SUPER_SMALL_CAP',experimental=True,fire_message_eligible=False)
            c.execute('INSERT OR IGNORE INTO entries VALUES(?,?,?,?,?,?,?)',(mint,pair,now,price,mc,POLICY,json.dumps(entry,sort_keys=True)))
    return count

def cycle(c,now,provider=fetch,clock=None):
    clock=clock or (time.time if provider is fetch else lambda:now)
    requests=0;errors=[];samples=0
    try:
        # Once per minute: latest profiles are partial discovery, never a complete launch universe.
        previous=c.execute('SELECT max(ts) FROM runs WHERE ts<=?',(now,)).fetchone()[0]
        if previous is None or now//60!=previous//60:
            rows,_=provider('token-profiles/latest/v1');requests+=1;received=int(clock())
            if not isinstance(rows,list):raise ValueError('profile response')
            for r in rows[:200]:
                if not isinstance(r,dict):continue
                mint=r.get('tokenAddress','')
                if r.get('chainId')=='solana' and isinstance(mint,str) and ADDRESS.fullmatch(mint):
                    c.execute('INSERT OR IGNORE INTO tokens(mint,discovered_at) VALUES(?,?)',(mint,received))
        # Retain losers too. Follow newly discovered candidates for 24h, bounded fair rotation.
        mints=[r[0] for r in c.execute('SELECT mint FROM tokens WHERE discovered_at>=? ORDER BY refreshed_at,discovered_at,mint LIMIT 30',(now-86400,))]
        if mints:
            rows,digest=provider('tokens/v1/solana/'+','.join(mints));requests+=1;received=int(clock())
            samples=ingest(c,rows,received,digest)
            c.executemany('UPDATE tokens SET refreshed_at=? WHERE mint=?',[(received,m) for m in mints])
    except Exception as exc:errors.append(type(exc).__name__)
    report={'checked_at':now,'policy':POLICY,'mode':'SHADOW','trigger':'SUPER_SMALL_CAP','deadline_ts':None,
            'coverage':'profiled Solana tokens; partial discovery and bounded polling',
            'provider_requests_completed':requests,'samples_saved':samples,'errors':errors,
            'tokens_known':c.execute('SELECT count(*) FROM tokens').fetchone()[0],
            'band_entries':c.execute('SELECT count(*) FROM entries').fetchone()[0],
            'telegram_messages_sent':0,'live_execution':False,'weights_updated':False}
    c.execute('INSERT OR REPLACE INTO runs VALUES(?,?)',(now,json.dumps(report,sort_keys=True)));c.commit();return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--once',action='store_true');a=p.parse_args()
    if not STATE.is_dir():raise ValueError('Owner installation required')
    if (STATE/'STOP').exists():print(json.dumps({'mode':'STOPPED'}));return
    if sum(f.stat().st_size for f in STATE.glob('*.sqlite*'))>=MAX_BYTES:raise ValueError('storage cap; preserve history and pause')
    with connect(STATE/'capture.sqlite') as c:report=cycle(c,int(time.time()))
    # Service process writes private status; only aggregates are printed.
    (STATE/'status.json').write_text(json.dumps(report,sort_keys=True)+'\n')
    print(json.dumps(report,sort_keys=True))
if __name__=='__main__':main()
