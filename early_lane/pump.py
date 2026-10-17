"""Read-only Pump evidence parser pinned to the official account/discriminator map."""
import base64
import json
from pathlib import Path
import struct
from core import digest
ALPHABET='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
PUMP='6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P'
AMM='pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA'
SPL='TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
TOKEN22='TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'
WSOL='So11111111111111111111111111111111111111112'
EVENT_TAG=bytes([228,69,165,46,81,203,154,29])

class EvidenceError(ValueError):pass

def b58decode(value):
    if not isinstance(value,str) or len(value)>65536:raise EvidenceError('base58_shape')
    n=0
    for c in value:n=n*58+ALPHABET.index(c)
    return b'\0'*(len(value)-len(value.lstrip('1')))+(n.to_bytes((n.bit_length()+7)//8,'big') if n else b'')

def b58(raw):
    zeros=len(raw)-len(raw.lstrip(b'\0'));n=int.from_bytes(raw,'big');out=''
    while n:n,r=divmod(n,58);out=ALPHABET[r]+out
    return '1'*zeros+out

def public(value):return isinstance(value,str) and len(b58decode(value))==32

class Reader:
    def __init__(self,data):self.data=data;self.p=0
    def take(self,n):
        if n<0 or self.p+n>len(self.data):raise EvidenceError('truncated_borsh')
        out=self.data[self.p:self.p+n];self.p+=n;return out
    def u64(self):return int.from_bytes(self.take(8),'little')
    def i64(self):return int.from_bytes(self.take(8),'little',signed=True)
    def key(self):return b58(self.take(32))
    def text(self):
        n=int.from_bytes(self.take(4),'little')
        if n>8192:raise EvidenceError('oversize_borsh_string')
        return self.take(n).decode('utf-8')

def maps():
    root=Path(__file__).resolve().parent
    pump=json.loads((root/'pump_layout.json').read_text());amm=json.loads((root/'amm_layout.json').read_text())
    return ({bytes(x['discriminator']):x for x in pump['instructions']},
            {bytes(x['discriminator']):x for x in amm['instructions']},
            {x['name']:bytes(x['discriminator']) for x in pump['events']})

def instructions(tx):
    msg=tx['transaction']['message'];keys=msg['accountKeys']
    names=[x['pubkey'] if isinstance(x,dict) else x for x in keys]
    all_ix=list(msg.get('instructions',[]))
    for group in tx['meta'].get('innerInstructions') or []:all_ix.extend(group['instructions'])
    out=[]
    for x in all_ix:
        y=dict(x)
        y['programId']=y.get('programId') or names[y['programIdIndex']]
        y['accounts']=[names[a] if isinstance(a,int) else a for a in y.get('accounts',[])]
        out.append(y)
    return out

def decode_tx(tx,mint,signature):
    if not tx:raise EvidenceError('transaction_unavailable')
    version=tx.get('version','legacy')
    if version!='legacy' and (type(version) is not int or version not in (0,1)):raise EvidenceError('unsupported_transaction_version')
    if tx['meta']['err'] is not None:return {'signature':signature,'slot':tx['slot'],'trades':[],'failed':True,'complete':True}
    if tx.get('blockTime') is None:raise EvidenceError('missing_block_time')
    pmap,amap,events=maps();ixs=instructions(tx);payloads={};methods=[];creation=None;migration=None;pool=None
    for ix in ixs:
        if ix['programId'] not in (PUMP,AMM):continue
        raw=b58decode(ix.get('data',''))
        if raw.startswith(EVENT_TAG):
            if ix['programId']==PUMP:payloads[raw[8:]]=True
            continue
        method=(pmap if ix['programId']==PUMP else amap).get(raw[:8])
        if method is None:raise EvidenceError('unsupported_pump_instruction')
        bound=dict(zip(method['accounts'],ix['accounts']));name=method['name'];base=bound.get('mint') or bound.get('base_mint')
        if base!=mint:continue
        if name.startswith('create') and name in ('create','create_v2'):
            r=Reader(raw[8:]);token_name=r.text();symbol=r.text();uri=r.text();creator=r.key()
            if creator!=bound.get('user'):raise EvidenceError('creator_not_original_signer')
            signers={k['pubkey'] for k in tx['transaction']['message']['accountKeys'] if isinstance(k,dict) and k.get('signer')}
            if creator not in signers:raise EvidenceError('creator_not_signer')
            creation={'mint':mint,'creator':creator,'curve':bound['bonding_curve'],'created_at':tx['blockTime'],'slot':tx['slot'],'name':token_name,'symbol':symbol,'uri':uri,'signature':signature}
        if name in ('migrate','migrate_v2'):
            migration=tx['blockTime'];pool=bound.get('pool')
        if name.startswith(('buy','sell')):
            if len(raw)<16 or int.from_bytes(raw[8:16],'little')<=0:raise EvidenceError('zero_swap_quantity')
            methods.append((ix['programId'],'buy' if name.startswith('buy') else 'sell',bound.get('user'),bound))
    # Only Pump program log data, not an arbitrary nested program's lookalike logs.
    stack=[]
    for line in tx['meta'].get('logMessages') or []:
        if line.startswith('Program ') and ' invoke [' in line:stack.append(line.split()[1])
        elif line.startswith('Program ') and (line.endswith(' success') or ' failed:' in line):
            if stack:stack.pop()
        elif line.startswith('Program data: ') and stack and stack[-1]==PUMP:
            payloads[base64.b64decode(line.split(': ',1)[1],validate=True)]=True
    trades=[]
    for data in payloads:
        if data[:8]==events.get('CreateEvent'):
            r=Reader(data[8:]);r.text();r.text();r.text();em=r.key();curve=r.key();r.key();creator=r.key();r.i64();r.u64();r.u64();initial=r.u64();supply=r.u64()
            if em==mint and creation:
                if curve!=creation['curve']:raise EvidenceError('create_event_curve_mismatch')
                if creator!=creation['creator']:raise EvidenceError('create_event_creator_mismatch')
                if initial<=0:raise EvidenceError('create_event_initial_reserves_unsupported')
                creation.update(initial_curve_tokens=initial,initial_supply=supply)
        if data[:8]==events.get('TradeEvent'):
            r=Reader(data[8:]);em=r.key();sol=r.u64();qty=r.u64();direction=r.take(1)[0];user=r.key();stamp=r.i64()
            if em!=mint:continue
            if direction not in (0,1) or qty<=0 or sol<=0:raise EvidenceError('unsupported_quote_or_trade_event')
            side='buy' if direction else 'sell'
            if not any(program==PUMP and s==side and u==user for program,s,u,_ in methods):raise EvidenceError('unbound_trade_event')
            if abs(stamp-tx['blockTime'])>30:raise EvidenceError('trade_time_mismatch')
            trades.append({'side':side,'user':user,'slot':tx['slot'],'at':tx['blockTime'],'qty':qty,'quote_lamports':sol,'event':digest(data.hex())})
    pump_methods=[x for x in methods if x[0]==PUMP]
    if len(trades)!=len(pump_methods):raise EvidenceError('trade_event_coverage_gap')
    # Pump AMM uses its authenticated account map and actual owner token deltas.
    for program,side,user,bound in methods:
        if program!=AMM:continue
        if sum(1 for x in methods if x[0]==AMM and x[2]==user)!=1:raise EvidenceError('ambiguous_amm_multi_swap')
        def balance(which):
            return sum(int(b['uiTokenAmount']['amount']) for b in tx['meta'].get(which,[]) if b.get('owner')==user and b['mint']==mint)
        delta=balance('postTokenBalances')-balance('preTokenBalances')
        if (side=='buy' and delta<=0) or (side=='sell' and delta>=0):raise EvidenceError('amm_swap_delta')
        trades.append({'side':side,'user':user,'slot':tx['slot'],'at':tx['blockTime'],'qty':abs(delta),'event':digest([signature,side,user])})
    return {'signature':signature,'slot':tx['slot'],'at':tx['blockTime'],'trades':trades,'creation':creation,'migration':migration,'pool':pool,'complete':True,'evidence_hash':digest(tx)}

def curve(account,mint,creation):
    if account.get('owner')!=PUMP or account.get('executable'):raise EvidenceError('curve_owner')
    if account['data'][1]!='base64':raise EvidenceError('curve_encoding')
    raw=base64.b64decode(account['data'][0],validate=True)
    if len(raw)<81 or raw[:8]!=bytes([23,183,248,55,96,216,172,96]):raise EvidenceError('curve_layout')
    r=Reader(raw[8:]);vtoken=r.u64();vquote=r.u64();real=r.u64();realquote=r.u64();supply=r.u64();complete=r.take(1)[0];creator=r.key()
    if complete not in (0,1):raise EvidenceError('curve_complete_flag')
    if creator!=creation['creator']:raise EvidenceError('curve_creator_mismatch')
    if supply!=creation.get('initial_supply'):raise EvidenceError('curve_supply_mismatch')
    if vtoken<=0:raise EvidenceError('curve_virtual_reserves')
    if len(raw)>81 and raw[81]!=0:raise EvidenceError('mayhem_not_supported')
    initial=creation.get('initial_curve_tokens')
    if not initial or not 0<=real<=initial:raise EvidenceError('curve_progress_unavailable')
    return {'on_curve':not bool(complete),'progress_pct':str((1-number(real)/number(initial))*100),'real_quote_lamports':realquote,'supply':supply}

# Kept at bottom to avoid importing production scanner modules with side effects.
from core import number
