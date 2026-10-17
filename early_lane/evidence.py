"""Independent account checks survive history backlog; all frozen gates still apply."""
import copy
import base64
import json
import time
from collections import Counter
from core import digest,number
from pump import PUMP,AMM,SPL,TOKEN22,curve,EvidenceError
from pricing import addresses,raw_account,CURVE_DISC,pool_identity
from sources import Collector,SourceUnavailable

NORMALIZED=('census_complete','creator_verified','first_blocks_complete','history_complete','authorities_authenticated','curve_authenticated','mint_revoked','freeze_revoked','dev_pct','dev_first_pct','top_holder_pct','unique_buyers','unique_5m_ago','buys_5m','sells_5m','socials','holders_at','history_at','authority_at','curve_at','on_curve','graduated_at','curve_progress_pct','collection_issue','collection_issues','provenance')

def clean(launch):
    return {k:v for k,v in launch.items()if k not in NORMALIZED}

class EvidenceCollector(Collector):
    def account_facts(self,launch):
        """Fresh mint + complete holder census, without waiting for trade history."""
        f=clean(launch);mint=f['mint'];f['provenance']={};issues={};self.account_snapshot=None
        if not hasattr(self,'account_cache'):self.account_cache={}
        cached=self.account_cache.get(mint)
        if cached and 0<=time.time()-cached['at']<=40:
            self.account_snapshot=copy.deepcopy(cached['snapshot'])
            f.update(copy.deepcopy(cached['facts']));return f,{}
        try:
            cv,pool,authority=addresses(mint)
            market=self.rpc.call('getMultipleAccounts',[[mint,cv,pool],{'encoding':'jsonParsed','commitment':'confirmed'}])
            if len(market['value'])!=3:raise SourceUnavailable('account_snapshot_incomplete')
            ma,ca,pa=market['value'];info=ma['data']['parsed']['info']
            if not ma or ma['owner'] not in (SPL,TOKEN22) or ma.get('executable'):raise SourceUnavailable('unsupported_token_program')
            supply=int(info['supply'])
            if supply<=0 or not info.get('isInitialized'):raise SourceUnavailable('mint_supply')
            ext=info.get('extensions',[])
            if ma['owner']==TOKEN22 and 'extensions'not in info:raise SourceUnavailable('token_extensions_unknown')
            if any(x.get('extension')not in ('metadataPointer','tokenMetadata')for x in ext):raise SourceUnavailable('unsupported_token_extensions')
            at=time.time();f.update(authorities_authenticated=True,authority_at=at,mint_revoked=info.get('mintAuthority','unknown')is None,freeze_revoked=info.get('freezeAuthority','unknown')is None)
            self.account_snapshot={'market':market,'mint':mint,'curve':cv,'holders':None,'supply':supply,'at':at}
            # Exclusion is bound to the exact PDA and on-chain account owner/layout.
            raw=raw_account(ca,(PUMP,))
            if len(raw)<81 or raw[:8]!=CURVE_DISC:raise SourceUnavailable('curve_identity_unavailable')
            excluded={cv}
            if raw[48]not in (0,1):raise SourceUnavailable('curve_complete_flag')
            if raw[48]==1:
                pool_identity(pa,mint,authority);excluded.add(pool)
            census=self.rpc.call('getProgramAccounts',[ma['owner'],{'encoding':'jsonParsed','commitment':'confirmed','withContext':True,'minContextSlot':market['context']['slot'],'filters':[{'memcmp':{'offset':0,'bytes':mint}}]}])
            if not isinstance(census,dict)or census.get('context',{}).get('slot',-1)<market['context']['slot']or not isinstance(census.get('value'),list):raise SourceUnavailable('census_context_missing_or_stale')
            holders=Counter();total=0
            for row in census['value']:
                account=row['account'];parsed=account['data']['parsed'];i=parsed['info']
                if account['owner']!=ma['owner']or parsed['type']!='account'or i['mint']!=mint or i['tokenAmount']['decimals']!=info['decimals']:raise SourceUnavailable('census_account_identity')
                amount=int(i['tokenAmount']['amount'])
                if amount<0:raise SourceUnavailable('negative_token_balance')
                total+=amount;holders[i['owner']]+=amount
            if total!=supply:
                f['provenance']['holder_reconciliation']={'mint_supply':supply,'census_total':total,'difference':total-supply,'accounts':len(census['value']),'mint_slot':market['context']['slot'],'census_slot':census['context']['slot']}
                raise SourceUnavailable('holder_supply_not_reconciled')
            self.account_snapshot.update(holders=holders,at=time.time())
            f.update(census_complete=True,holders_at=time.time(),top_holder_pct=str(max((number(v)/supply*100 for k,v in holders.items()if k not in excluded),default=number(0))))
            f['provenance'].update(account_snapshot_hash=digest(market),holder_census_hash=digest(census),source_slots=[market['context']['slot'],census['context']['slot']])
            fields={k:copy.deepcopy(v) for k,v in f.items()if k in NORMALIZED}
            self.account_cache[mint]={'at':time.time(),'facts':fields,'snapshot':copy.deepcopy(self.account_snapshot)}
        except (OSError,ValueError,KeyError,TypeError,IndexError,TimeoutError)as exc:
            issues['accounts']=str(exc)[:100]if isinstance(exc,ValueError)else type(exc).__name__
        return f,issues

    def cached_creation_facts(self,f):
        """A decoded creation may already exist while later trades are still pending."""
        row=self.cache.execute('SELECT body FROM metadata WHERE mint=?',(f['mint'],)).fetchone()
        if not row:return
        c=json.loads(row[0]);snap=self.account_snapshot
        if abs(c['created_at']-f['created_at'])>120:raise SourceUnavailable('launch_creation_time_conflict')
        if f.get('creator')and f['creator']!=c['creator']:raise SourceUnavailable('creator_identity_conflict')
        f.update(created_at=c['created_at'],creator=c['creator'],creator_verified=True,uri=c['uri'],name=c.get('name',f.get('name')),symbol=c.get('symbol',f.get('symbol')))
        # Reuse only successfully observed links younger than 60 seconds. A failed
        # refresh never preserves an older PASS from the input launch or cache.
        if not hasattr(self,'social_cache'):self.social_cache={}
        old=self.social_cache.get(c['uri'])
        if old and 0<=time.time()-old['at']<=50:f['socials']=old['links']
        else:
            self.social_cache.pop(c['uri'],None)
            links=self.social(c['uri']);f['socials']=links
            self.social_cache[c['uri']]={'at':time.time(),'links':links}
        if snap and snap['mint']==f['mint']and snap['curve']==c['curve']and 0<=time.time()-snap['at']<=60:
            mark=curve(snap['market']['value'][1],f['mint'],c)
            f.update(curve_authenticated=True,curve_at=snap['at'],on_curve=mark['on_curve'],curve_progress_pct=mark['progress_pct'])
            if snap['holders']is not None:
                f['dev_pct']=str(number(snap['holders'][c['creator']])/snap['supply']*100)
        f['provenance']['creation_signature']=c['signature']

    def enrich(self,launch,now=None):
        f,issues=self.account_facts(launch)
        # History is bounded per candidate; leave state durable for the next pass.
        remaining=self.rpc.remaining;cap=min(8,max(0,remaining));self.rpc.remaining=cap
        try:history=super().enrich(clean(launch),now)
        finally:self.rpc.remaining=remaining-(cap-self.rpc.remaining)
        if history.get('collection_issue'):issues['history']=history['collection_issue']
        provenance={**f.get('provenance',{}),**history.get('provenance',{})}
        f.update(history);f['provenance']=provenance
        try:self.cached_creation_facts(f)
        except (OSError,ValueError,KeyError,TypeError,IndexError,TimeoutError)as exc:
            issues['creation_or_social']=str(exc)[:100]if isinstance(exc,ValueError)else type(exc).__name__
        # No incomplete history may claim buyer growth or first-block membership.
        f['collection_issues']=issues
        if issues:f['collection_issue']=';'.join(k+':'+v for k,v in issues.items())[:300]
        return f

    def prune(self,active):
        super().prune(active)
        if hasattr(self,'account_cache'):self.account_cache={k:v for k,v in self.account_cache.items()if k in active}
        if hasattr(self,'social_cache'):self.social_cache={k:v for k,v in self.social_cache.items()if 0<=time.time()-v['at']<=50}
