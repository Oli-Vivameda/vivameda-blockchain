"""Pump program-log decoding for shadow comparison, never screening admission."""
import base64
import re
from collections import Counter
from functools import lru_cache
from core import digest
from pump import PUMP,AMM,Reader,b58decode,maps,EvidenceError

class StreamGap(ValueError):pass
class MintGap(StreamGap):
    def __init__(self,reason,mints):self.mints=sorted(set(mints));super().__init__(reason)

def address(s,n=32):
    try:valid=len(b58decode(s))==n
    except ValueError:valid=False
    if not valid:raise StreamGap('invalid_address')
    return s

@lru_cache(maxsize=1)
def layout():return maps()

def normalize(value,observed_at):
    if not isinstance(value,dict)or set(('signature','err','logs'))-value.keys():raise StreamGap('notification_shape')
    signature=address(value['signature'],64);logs=value['logs']
    if not isinstance(logs,list)or len(logs)>4096 or any(not isinstance(x,str)for x in logs):raise StreamGap('log_shape')
    if value['err']is not None and not((isinstance(value['err'],dict)or isinstance(value['err'],str))and bool(value['err'])):raise StreamGap('invalid_failure_status')
    if value['err']is not None:return {'signature':signature,'failed':True,'creations':[],'trades':[],'source_hash':digest(value),'admissible_for_screening':False}
    pmap,_,events=layout();known={x['name'].replace('_','').lower()for x in pmap.values()};stack=[];payloads={};methods=[];all_methods=[];pump_seen=False;amm_seen=False
    for line in logs:
        if 'Log truncated'in line:raise StreamGap('logs_truncated')
        match=re.fullmatch(r'Program (\w+) invoke \[(\d+)\]',line)
        if match:
            if int(match[2])!=len(stack)+1:raise StreamGap('invocation_depth')
            stack.append(match[1]);pump_seen|=match[1]==PUMP;amm_seen|=match[1]==AMM;continue
        match=re.fullmatch(r'Program (\w+) (success|failed:.*)',line)
        if match:
            if not stack or stack.pop()!=match[1]:raise StreamGap('invocation_stack')
            continue
        if stack and stack[-1]==PUMP:
            if line.startswith('Program log: Instruction: '):
                method=line.split(': ',2)[2].replace('_','').lower()
                all_methods.append(method)
                if method not in known:raise StreamGap('unsupported_pump_method')
                if method.startswith(('buy','sell')):methods.append('buy'if method.startswith('buy')else'sell')
            elif line.startswith('Program data: '):
                try:data=base64.b64decode(line.split(': ',1)[1],validate=True)
                except ValueError as exc:raise StreamGap('event_encoding')from exc
                payloads[data]=True
    if stack:raise StreamGap('unterminated_invocation')
    creations=[];trades=[]
    try:
        for data in payloads:
            if data[:8]==events['CreateEvent']:
                r=Reader(data[8:]);name=r.text();symbol=r.text();uri=r.text();mint=r.key();curve=r.key();user=r.key();creator=r.key();stamp=r.i64();r.u64();r.u64();initial=r.u64();supply=r.u64()
                creations.append(dict(mint=mint,curve=curve,user=user,creator=creator,created_at=stamp,name=name,symbol=symbol,uri=uri,initial_curve_tokens=initial,initial_supply=supply,signature=signature))
            elif data[:8]==events['TradeEvent']:
                r=Reader(data[8:]);mint=r.key();quote=r.u64();qty=r.u64();side=r.take(1)[0];user=r.key();stamp=r.i64()
                if side not in(0,1):raise StreamGap('unsupported_trade_direction')
                trades.append(dict(mint=mint,user=user,side='buy'if side else'sell',at=stamp,qty=qty,quote_lamports=quote,event=digest(data.hex()),signature=signature))
    except (ValueError,KeyError,IndexError,TypeError)as exc:
        if isinstance(exc,StreamGap):raise
        raise StreamGap('event_layout')from exc
    if Counter(methods)!=Counter(t['side']for t in trades):raise StreamGap('trade_event_coverage')
    if len(creations)>8 or len(trades)>64:raise StreamGap('event_count_bound')
    scope={x['mint']for x in creations+trades}
    if any(c['initial_curve_tokens']<=0 or c['initial_supply']<c['initial_curve_tokens']for c in creations):raise MintGap('creation_reserves',scope)
    if any(t['qty']<=0 or t['quote_lamports']<=0 for t in trades):raise MintGap('non_economic_or_unsupported_trade',scope)
    for event in creations+trades:
        at=event.get('at',event.get('created_at'))
        if not 0<=observed_at-at<=60:raise MintGap('event_time_not_fresh',scope)
    return dict(signature=signature,failed=False,pump_seen=pump_seen,amm_seen=amm_seen,fast_path_safe=bool(methods)and not amm_seen and not creations and all(m.startswith(('buy','sell'))for m in all_methods),creations=creations,trades=trades,source_hash=digest(value),admissible_for_screening=False)
