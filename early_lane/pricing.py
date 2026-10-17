"""Read-only on-chain Pump marks. No website price API, wallet or transaction.

Pyth PriceUpdateV2 field layout: official pyth-network/pyth-crosschain SDK.
Pump/PumpSwap layouts and PDA seeds: pinned official pump-public-docs IDL.
"""
import base64
import hashlib
import struct
import time
from decimal import Decimal as D
from core import digest,number
from pump import PUMP,AMM,SPL,TOKEN22,WSOL,b58,b58decode,EvidenceError
ORACLE='7UVimffxr9ow1uXYxsr4LHAcV58mLzhmwaeKvJ1pjLiE'
RECEIVER='rec5EKMGg6MxZYaMdyBfgwp4d5rB9T1VQH5pJv5LtFJ'
SOL_FEED=bytes.fromhex('ef0d8b6fda2ceba41da15d4095d1da392a0d2f8ed0c6c7bc0f4cfac8c280b56d')
CURVE_DISC=bytes([23,183,248,55,96,216,172,96])
POOL_DISC=bytes([241,154,109,4,17,177,109,188])
P=2**255-19
EDWARDS_D=(-121665*pow(121666,P-2,P))%P

def on_curve(raw):
    if len(raw)!=32:return False
    y=int.from_bytes(raw,'little')&((1<<255)-1)
    if y>=P:return False
    y2=y*y%P;den=(EDWARDS_D*y2+1)%P
    if den==0:return False
    x2=(y2-1)*pow(den,P-2,P)%P
    return x2==0 or pow(x2,(P-1)//2,P)==1

def pda(seeds,program):
    if len(seeds)>15 or any(len(x)>32 for x in seeds):raise EvidenceError('pda_seed_bound')
    owner=b58decode(program)
    if len(owner)!=32:raise EvidenceError('pda_program')
    for bump in range(255,-1,-1):
        raw=hashlib.sha256(b''.join(seeds)+bytes([bump])+owner+b'ProgramDerivedAddress').digest()
        if not on_curve(raw):return b58(raw)
    raise EvidenceError('pda_unavailable')

def addresses(mint):
    raw=b58decode(mint)
    if len(raw)!=32:raise EvidenceError('mint_address')
    authority=pda([b'pool-authority',raw],PUMP)
    return pda([b'bonding-curve',raw],PUMP),pda([b'pool',b'\0\0',b58decode(authority),raw,b58decode(WSOL)],AMM),authority

def raw_account(value,owner):
    if not value or value.get('owner') not in owner or value.get('executable') or value.get('data',[None,None])[1]!='base64':raise EvidenceError('account_owner_or_encoding')
    return base64.b64decode(value['data'][0],validate=True)

def oracle(value,now):
    raw=raw_account(value,(RECEIVER,))
    if len(raw)!=134 or raw[:8]!=hashlib.sha256(b'account:PriceUpdateV2').digest()[:8] or raw[40]!=1:raise EvidenceError('oracle_layout_or_verification')
    if raw[41:73]!=SOL_FEED:raise EvidenceError('oracle_wrong_feed')
    price,conf,exponent,at=struct.unpack_from('<qQiq',raw,73)
    if not -12<=exponent<=0 or price<=0 or conf>=price or not 0<=now-at<=60:raise EvidenceError('oracle_invalid_or_stale')
    # Full verification + feed + recency are mandatory. Confidence remains visible;
    # no new confidence threshold is added to the frozen admission rules.
    return number(price)*D(10)**exponent,at,str(number(conf)*D(10)**exponent)

def supply(value):
    raw=raw_account(value,(SPL,TOKEN22))
    if len(raw)<82 or raw[45]!=1:raise EvidenceError('mint_layout')
    n=int.from_bytes(raw[36:44],'little')
    if n<=0:raise EvidenceError('mint_supply')
    return n

def curve_mark(account,mint,supply_raw,sol_usd):
    raw=raw_account(account,(PUMP,))
    if len(raw)<81 or raw[:8]!=CURVE_DISC:raise EvidenceError('curve_layout')
    vt,vq,rt,rq,total=struct.unpack_from('<5Q',raw,8)
    if raw[48] not in (0,1) or not 0<supply_raw<=total or vt<=0 or vq<=0 or rt>vt:raise EvidenceError('curve_reserves_or_supply')
    if len(raw)>81 and raw[81]!=0:raise EvidenceError('mayhem_not_supported')
    if len(raw)>83 and (len(raw)<115 or raw[83:115]!=b'\0'*32):raise EvidenceError('non_sol_curve_not_supported')
    if raw[48]==1:return None
    return number(vq)*supply_raw/vt/D(10**9)*sol_usd

def pool_identity(value,mint,authority):
    raw=raw_account(value,(AMM,))
    if len(raw)<245 or raw[:8]!=POOL_DISC or int.from_bytes(raw[9:11],'little')!=0 or b58(raw[11:43])!=authority or b58(raw[43:75])!=mint or b58(raw[75:107])!=WSOL or raw[243]!=0:raise EvidenceError('pool_identity_or_mayhem')
    if len(raw)>245 and (len(raw)<261 or int.from_bytes(raw[245:261],'little',signed=True)!=0):raise EvidenceError('boost_pool_not_supported')
    return b58(raw[139:171]),b58(raw[171:203])

def vault(value,mint,owner):
    raw=raw_account(value,(SPL,TOKEN22))
    if len(raw)<165 or b58(raw[:32])!=mint or b58(raw[32:64])!=owner or raw[108]!=1:raise EvidenceError('vault_identity_or_state')
    return int.from_bytes(raw[64:72],'little')

def pool_mark(base,quote,mint,pool,supply_raw,sol_usd):
    b=vault(base,mint,pool);q=vault(quote,WSOL,pool)
    if b<=0:raise EvidenceError('empty_base_price_undefined')
    return number(q)*supply_raw/b/D(10**9)*sol_usd,number(q)*2/D(10**9)*sol_usd

class Marks:
    def __init__(self,rpc):self.rpc=rpc
    def read(self,rows,now=None):
        """One <=30-mint batch: same-slot curve/mint/oracle; optional AMM vaults.

        Feed discovery is supplied by the approved owner exporter. Market marks
        are independently read through the permitted RPC and bound to exact PDAs.
        """
        if len(rows)>30:raise ValueError('mark_batch_bound')
        clock=time.time if now is None else lambda:now
        out={};bound=[]
        for row in rows:
            mint=row['mint']
            try:bound.append((mint,*addresses(mint)))
            except ValueError:out[mint]={'pricing_issue':'invalid_mint'}
        if not bound:return out
        keys=[ORACLE]+[k for mint,curve,pool,authority in bound for k in (mint,curve,pool)]
        response=self.rpc.call('getMultipleAccounts',[keys,{'encoding':'base64','commitment':'confirmed'}])
        slot=response['context']['slot'];block_at=self.rpc.call('getBlockTime',[slot]);captured=clock()
        if block_at is None or not 0<=captured-block_at<=60:raise EvidenceError('rpc_context_not_fresh')
        values=response['value']
        if len(values)!=len(keys):raise EvidenceError('rpc_account_batch_incomplete')
        usd,oracle_at,confidence=oracle(values[0],captured);pending=[]
        for i,(mint,curve,pool,authority) in enumerate(bound):
            ma,ca,pa=values[1+3*i:4+3*i]
            try:
                s=supply(ma);mc=curve_mark(ca,mint,s,usd)
                if mc is None:
                    bv,qv=pool_identity(pa,mint,authority);pending.append((mint,pool,s,bv,qv));continue
                at=block_at
                out[mint]={'mc':str(mc),'market_at':at,'market_expires_at':min(block_at,oracle_at)+60,'liquidity':None,'pricing_provenance':{'source':'public_rpc_pump_curve_pyth','slot':slot,'captured_at':captured,'oracle_publish_at':oracle_at,'sol_usd':str(usd),'oracle_confidence_usd':confidence,'response_hash':digest(response)}}
            except (ValueError,KeyError,TypeError,IndexError) as exc:out[mint]={'pricing_issue':str(exc) if isinstance(exc,EvidenceError) else 'unsupported_or_incomplete_curve_mark'}
        if pending:
            # Refresh oracle and mint supply in the SAME response as both vaults.
            keys=[ORACLE]+[k for mint,pool,s,bv,qv in pending for k in (mint,bv,qv)]
            r=self.rpc.call('getMultipleAccounts',[keys,{'encoding':'base64','commitment':'confirmed','minContextSlot':slot}]);ts=self.rpc.call('getBlockTime',[r['context']['slot']]);current=clock()
            if ts is None or r['context']['slot']<slot or not 0<=current-ts<=60:raise EvidenceError('amm_rpc_context_not_fresh')
            u,oa,conf=oracle(r['value'][0],current)
            for i,(mint,pool,previous_supply,bv,qv) in enumerate(pending):
                try:
                    ma,base,quote=r['value'][1+3*i:4+3*i];s=supply(ma)
                    if s!=previous_supply:raise EvidenceError('supply_changed_between_pool_reads')
                    mc,liq=pool_mark(base,quote,mint,pool,s,u)
                    out[mint]={'mc':str(mc),'market_at':ts,'market_expires_at':min(ts,oa)+60,'liquidity':str(liq),'pricing_provenance':{'source':'public_rpc_pumpswap_vaults_pyth','slot':r['context']['slot'],'pool':pool,'response_hash':digest(r),'oracle_publish_at':oa,'sol_usd':str(u),'oracle_confidence_usd':conf}}
                except (ValueError,KeyError,TypeError,IndexError):out[mint]={'pricing_issue':'unsupported_or_incomplete_pool_mark'}
        return out
