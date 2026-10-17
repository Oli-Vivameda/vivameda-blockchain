"""Permitted-source clients. No credentials, trading methods, paid fallback or proxies."""
import base64
import http.client
import ipaddress
import json
from pathlib import Path
import socket
import sqlite3
import ssl
import time
import urllib.parse
from collections import Counter
from core import canonical,digest,number
from pump import decode_tx,curve,EvidenceError,SPL,TOKEN22,PUMP,AMM,public

def retry_seconds(headers):
    value=next((v for k,v in headers.items() if k.lower()=='retry-after'),'60')
    try:
        delay=float(value)
        if not number(delay).is_finite():return 60
        return max(60,delay)
    except (ValueError,TypeError):
        try:
            from email.utils import parsedate_to_datetime
            return max(60,parsedate_to_datetime(value).timestamp()-time.time())
        except Exception:return 60

class SourceUnavailable(ValueError):pass
class BudgetExceeded(SourceUnavailable):pass

class PublicHTTPS:
    def get(self,url,limit=524288,method='GET',body=None,redirects=2):
        for _ in range(redirects+1):
            u=urllib.parse.urlsplit(url)
            if u.scheme!='https' or not u.hostname or u.username or u.password or u.port not in (None,443):raise SourceUnavailable('public_https_only')
            addresses={x[4][0] for x in socket.getaddrinfo(u.hostname,443,type=socket.SOCK_STREAM)}
            if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):raise SourceUnavailable('nonpublic_destination')
            # Pin the vetted address; TLS still validates the original hostname.
            host=u.hostname;address=sorted(addresses)[0];context=ssl.create_default_context()
            class Pinned(http.client.HTTPSConnection):
                def connect(self):
                    s=socket.create_connection((address,443),timeout=10)
                    self.sock=context.wrap_socket(s,server_hostname=host)
            c=Pinned(host,timeout=10,context=context)
            try:
                c.request(method,urllib.parse.urlunsplit(('', '', u.path or '/',u.query,'')),body=body,headers={'User-Agent':'Vivameda-Early-Lane/1.0','Content-Type':'application/json','Accept':'application/json,text/html'})
                r=c.getresponse();status=r.status;headers=dict(r.getheaders());data=r.read(limit+1)
                if len(data)>limit:raise SourceUnavailable('response_bound')
                if status in (301,302,303,307,308):
                    if body is not None:raise SourceUnavailable('rpc_redirect_refused')
                    location=r.getheader('Location')
                    if not location:raise SourceUnavailable('redirect_without_location')
                    url=urllib.parse.urljoin(url,location);continue
                return {'status':status,'headers':headers,'body':data,'url':url}
            finally:c.close()
        raise SourceUnavailable('redirect_bound')

class Rpc:
    ALLOWED={'getHealth','getAccountInfo','getMultipleAccounts','getProgramAccounts','getSignaturesForAddress','getTransaction','getBlocks','getSlot','getBlockTime'}
    def __init__(self,cache,http=None):
        self.cache=cache;self.http=http or PublicHTTPS();self.remaining=0
    def budget(self,n=12):self.remaining=n
    def call(self,method,params=None):
        if method not in self.ALLOWED:raise SourceUnavailable('read_only_rpc_method')
        if self.remaining<=0:raise BudgetExceeded('rpc_cycle_budget')
        row=self.cache.execute("SELECT body FROM config WHERE key='cooldown'").fetchone();cool=float(json.loads(row[0])) if row else 0
        if time.time()<cool:raise BudgetExceeded('rpc_cooldown')
        if self.remaining>0:self.remaining-=1
        # One call/second, one connection; no endpoint/IP cycling.
        row=self.cache.execute("SELECT body FROM config WHERE key='last_rpc'").fetchone();last=float(json.loads(row[0])) if row else 0
        wait=last+1-time.time()
        if wait>0:time.sleep(min(wait,1))
        self.cache.execute("INSERT OR REPLACE INTO config VALUES('last_rpc',?)",(canonical(time.time()),));self.cache.commit()
        req=canonical({'jsonrpc':'2.0','id':1,'method':method,'params':params or []}).encode()
        response=self.http.get('https://api.mainnet-beta.solana.com',limit=8*1024*1024,method='POST',body=req,redirects=0)
        if response['status'] in (403,429):
            delay=retry_seconds(response['headers'])
            self.cache.execute("INSERT OR REPLACE INTO config VALUES('cooldown',?)",(canonical(time.time()+delay),));self.cache.commit();raise SourceUnavailable('rpc_throttled_or_blocked')
        if response['status']!=200:raise SourceUnavailable('rpc_http')
        value=json.loads(response['body'])
        if 'error' in value:
            error=value['error'];code=error.get('code') if isinstance(error,dict) else None
            message=str(error.get('message','')).lower() if isinstance(error,dict) else ''
            if code in (429,-32429,-32005) or 'too many requests' in message or 'rate limit' in message:
                delay=retry_seconds(response['headers'])
                self.cache.execute("INSERT OR REPLACE INTO config VALUES('cooldown',?)",(canonical(time.time()+delay),));self.cache.commit()
                raise SourceUnavailable('rpc_throttled_or_overloaded')
            raise SourceUnavailable('rpc_method_unavailable:'+str(code))
        return value['result']

class Collector:
    def __init__(self,path,http=None):
        self.cache=sqlite3.connect(path);self.cache.row_factory=sqlite3.Row
        self.cache.executescript('''CREATE TABLE IF NOT EXISTS tx(mint TEXT,sig TEXT,slot INTEGER,body TEXT,PRIMARY KEY(mint,sig));
        CREATE TABLE IF NOT EXISTS scan(mint TEXT PRIMARY KEY,body TEXT);
        CREATE TABLE IF NOT EXISTS config(key TEXT PRIMARY KEY,body TEXT);
        CREATE TABLE IF NOT EXISTS metadata(mint TEXT PRIMARY KEY,body TEXT);''')
        self.http=http or PublicHTTPS();self.rpc=Rpc(self.cache,self.http)
    def save_scan(self,mint,state):self.cache.execute('INSERT OR REPLACE INTO scan VALUES(?,?)',(mint,canonical(state)));self.cache.commit()
    def history(self,mint):
        row=self.cache.execute('SELECT body FROM scan WHERE mint=?',(mint,)).fetchone()
        s=json.loads(row[0]) if row else {'cursor':None,'before':None,'head':None,'pending':[],'paging_done':False,'scan_at':None}
        # Complete the prior scan first, then the next poll catches up from its head.
        while not s['paging_done']:
            options={'limit':1000,'commitment':'confirmed'}
            if s['before']:options['before']=s['before']
            page=self.rpc.call('getSignaturesForAddress',[mint,options])
            if s['head'] is None:s['head']=page[0]['signature'] if page else s['cursor'];s['scan_at']=time.time()
            boundary=next((i for i,x in enumerate(page) if x['signature']==s['cursor']),None)
            selected=page[:boundary] if boundary is not None else page
            s['pending'].extend(x for x in selected if not self.cache.execute('SELECT 1 FROM tx WHERE mint=? AND sig=?',(mint,x['signature'])).fetchone())
            if boundary is not None or len(page)<1000:
                if s['cursor'] and boundary is None:raise SourceUnavailable('rpc_history_cursor_gap')
                s['paging_done']=True
            else:s['before']=page[-1]['signature']
            if len(s['pending'])>10000:raise SourceUnavailable('transaction_backlog_bound')
            self.save_scan(mint,s)
        s['pending'].sort(key=lambda r:(r['slot'],r['signature']))
        while s['pending']:
            entry=s['pending'][0]
            tx=self.rpc.call('getTransaction',[entry['signature'],{'encoding':'jsonParsed','commitment':'confirmed','maxSupportedTransactionVersion':1}])
            if tx is None:raise SourceUnavailable('transaction_gap_retry')
            try:parsed=decode_tx(tx,mint,entry['signature'])
            except (ValueError,KeyError,TypeError,IndexError) as exc:parsed={'signature':entry['signature'],'slot':entry['slot'],'error':str(exc)[:100]}
            self.cache.execute('INSERT OR IGNORE INTO tx VALUES(?,?,?,?)',(mint,entry['signature'],entry['slot'],canonical(parsed)))
            if parsed.get('creation'):
                self.cache.execute('INSERT OR REPLACE INTO metadata VALUES(?,?)',(mint,canonical(parsed['creation'])))
            self.cache.commit();s['pending'].pop(0);self.save_scan(mint,s)
        stamp=s['scan_at'];s={'cursor':s['head'],'head':None,'before':None,'pending':[],'paging_done':False,'scan_at':None};self.save_scan(mint,s)
        rows=[json.loads(x[0]) for x in self.cache.execute('SELECT body FROM tx WHERE mint=? ORDER BY slot,sig',(mint,))]
        if any('error' in x for x in rows):raise SourceUnavailable('unsupported_or_incomplete_trade_history')
        creation=next((x['creation'] for x in rows if x.get('creation')),None)
        if not creation:raise SourceUnavailable('creation_provenance_missing')
        return rows,creation,stamp
    def social(self,uri):
        if uri.startswith('ipfs://'):uri='https://ipfs.io/ipfs/'+uri[7:]
        data=self.http.get(uri,limit=262144)
        if data['status']!=200:raise SourceUnavailable('metadata_unavailable')
        meta=json.loads(data['body']);links=[]
        for name in ('twitter','telegram','website'):
            url=meta.get(name)
            if not isinstance(url,str) or not url:continue
            u=urllib.parse.urlsplit(url)
            if name=='twitter' and (u.hostname or '').lower() not in ('x.com','www.x.com','twitter.com','www.twitter.com'):continue
            if name=='telegram' and (u.hostname or '').lower() not in ('t.me','telegram.me','www.t.me'):continue
            try:
                result=self.http.get(url,limit=65536,method='HEAD')
                if result['status']==405:result=self.http.get(url,limit=65536)
                resolved=urllib.parse.urlsplit(result.get('url',url))
                if any(part.lower() in ('login','signin','sign-in','captcha','challenge') for part in resolved.path.split('/')):continue
                if 200<=result['status']<300:links.append({'url':url,'resolved_url':result['url'],'verified':True,'checked_at':time.time(),'status':result['status']})
            except (OSError,ValueError,TimeoutError):continue
        return links
    def enrich(self,launch,now=None):
        now=time.time() if now is None else now
        f=dict(launch);mint=f['mint']
        # Incoming launch rows cannot carry a previous normalized PASS through a
        # failed refresh. Only evidence collected in this call may satisfy gates.
        for field in ('census_complete','creator_verified','first_blocks_complete','history_complete','authorities_authenticated','curve_authenticated','mint_revoked','freeze_revoked','dev_pct','dev_first_pct','top_holder_pct','unique_buyers','unique_5m_ago','buys_5m','sells_5m','socials','holders_at','history_at','authority_at','curve_at','on_curve','graduated_at','curve_progress_pct'):
            f.pop(field,None)
        f['provenance']={}
        try:
            rows,creation,history_at=self.history(mint)
            if abs(creation['created_at']-f['created_at'])>120:raise SourceUnavailable('launch_creation_time_conflict')
            if f.get('creator') and f['creator']!=creation['creator']:raise SourceUnavailable('creator_identity_conflict')
            f.update(created_at=creation['created_at'],creator=creation['creator'],creator_verified=True,uri=creation['uri'])
            now=history_at
            trades=[t for row in rows for t in row.get('trades',[])]
            # Successful trades beyond current decision time cannot enter a lookback.
            trades=[t for t in trades if creation['created_at']<=t['at']<=now]
            blocks=self.rpc.call('getBlocks',[creation['slot'],creation['slot']+32,{'commitment':'confirmed'}])
            if len(blocks)<2 or blocks[0]!=creation['slot']:raise SourceUnavailable('first_two_produced_blocks_missing')
            first=set(t['user'] for t in trades if t['side']=='buy' and t['slot'] in blocks[:2]);first.add(creation['creator'])
            buys=set(t['user'] for t in trades if t['side']=='buy');before=set(t['user'] for t in trades if t['side']=='buy' and t['at']<=now-300)
            window=[t for t in trades if now-300<t['at']<=now]
            f.update(history_complete=True,history_at=history_at,unique_buyers=len(buys),unique_5m_ago=len(before),buys_5m=sum(t['side']=='buy' for t in window),sells_5m=sum(t['side']=='sell' for t in window),first_blocks_complete=True)
            market=self.rpc.call('getMultipleAccounts',[[mint,creation['curve']],{'encoding':'jsonParsed','commitment':'confirmed'}])
            ma=market['value'][0]
            if not ma or ma['owner'] not in (SPL,TOKEN22):raise SourceUnavailable('unsupported_token_program')
            info=ma['data']['parsed']['info'];supply=int(info['supply'])
            if supply<=0 or not info.get('isInitialized'):raise SourceUnavailable('mint_supply')
            extensions=info.get('extensions',[])
            if ma['owner']==TOKEN22 and 'extensions' not in info:raise SourceUnavailable('token_extensions_unknown')
            if any(x.get('extension') not in ('metadataPointer','tokenMetadata') for x in extensions):raise SourceUnavailable('unsupported_token_extensions')
            f.update(authorities_authenticated=True,authority_at=time.time(),mint_revoked=info.get('mintAuthority','unknown') is None,freeze_revoked=info.get('freezeAuthority','unknown') is None)
            # Curve account uses raw base64 even when mint uses jsonParsed.
            ca=market['value'][1];cv=curve(ca,mint,creation)
            migrations=[r for r in rows if r.get('migration') is not None]
            latest=max(migrations,key=lambda r:r['migration']) if migrations else None
            f.update(curve_authenticated=True,curve_at=time.time(),on_curve=cv['on_curve'],graduated_at=latest['migration'] if latest else None,curve_progress_pct=cv['progress_pct'])
            excluded={creation['curve']}
            if not cv['on_curve']:
                if not latest or not latest.get('pool'):raise SourceUnavailable('graduation_provenance_missing')
                pool=self.rpc.call('getAccountInfo',[latest['pool'],{'encoding':'base64','commitment':'confirmed'}])['value']
                if not pool or pool.get('owner')!=AMM:raise SourceUnavailable('graduated_pool_unknown')
                raw=base64.b64decode(pool['data'][0],validate=True)
                from pump import b58
                if len(raw)<243 or raw[:8]!=bytes([241,154,109,4,17,177,109,188]) or b58(raw[43:75])!=mint:raise SourceUnavailable('graduated_pool_identity')
                excluded.add(latest['pool'])
            census=self.rpc.call('getProgramAccounts',[ma['owner'],{'encoding':'jsonParsed','commitment':'confirmed','withContext':True,'minContextSlot':market['context']['slot'],'filters':[{'memcmp':{'offset':0,'bytes':mint}}]}])
            if not isinstance(census,dict) or not isinstance(census.get('value'),list):raise SourceUnavailable('census_context_missing')
            holders=Counter();total=0
            for row in census['value']:
                account=row['account'];parsed=account['data']['parsed']
                if account['owner']!=ma['owner'] or parsed['type']!='account':raise SourceUnavailable('census_account_type')
                i=parsed['info']
                if i['mint']!=mint or i['tokenAmount']['decimals']!=info['decimals']:raise SourceUnavailable('census_mint_or_decimals')
                amount=int(i['tokenAmount']['amount'])
                if amount<0:raise SourceUnavailable('negative_token_balance')
                total+=amount;holders[i['owner']]+=amount
            if total!=supply:raise SourceUnavailable('holder_supply_not_reconciled')
            f.update(census_complete=True,holders_at=time.time(),dev_pct=str(number(holders[creation['creator']])/supply*100),
                     dev_first_pct=str(sum(number(holders[x]) for x in first)/supply*100),top_holder_pct=str(max((number(v)/supply*100 for k,v in holders.items() if k not in excluded),default=number(0))))
            f['socials']=self.social(creation['uri'])
            f['provenance']={'creation_signature':creation['signature'],'trade_history_hash':digest(rows),'holder_census_hash':digest(census),'mint_curve_hash':digest(market),'source_slots':[market['context']['slot'],census['context']['slot']]}
        except (OSError,ValueError,KeyError,TypeError,IndexError,TimeoutError) as exc:
            f['collection_issue']=str(exc)[:100] if isinstance(exc,ValueError) else type(exc).__name__
        return f
    def prune(self,active):
        # Mutable RPC cache is not the append-only outcome journal. Retain creation
        # metadata but discard old trade-cache rows after the watch window.
        for row in self.cache.execute('SELECT DISTINCT mint FROM tx').fetchall():
            if row[0] not in active:self.cache.execute('DELETE FROM tx WHERE mint=?',(row[0],));self.cache.execute('DELETE FROM scan WHERE mint=?',(row[0],))
        self.cache.commit()
