"""Compact messages and confirmed-destination transport interface; no bot tokens."""
import datetime as dt
from decimal import Decimal as D
from core import FOOTER,number,canonical

def message(c,now=None):
    f=c['facts'];mint=c['mint'];age=(c['at']-f['created_at'])/60
    growth=(number(f['unique_buyers'])/number(f['unique_5m_ago'])-1)*100
    buys=number(f['buys_5m']);share=buys/(buys+number(f['sells_5m']))*100
    lines=[f"{str(f.get('symbol') or '?')[:24]} | {mint[:6]}…{mint[-5:]} | {age:.1f}m | ${number(c['mc']):,.0f} | curve {number(f['curve_progress_pct']):.0f}%",
           '```\n'+mint+'\n```',
           f"Dev {number(f['dev_pct']):.1f}% | dev+first2 {number(f['dev_first_pct']):.1f}% | top {number(f['top_holder_pct']):.1f}%",
           f"Buyers {f['unique_buyers']} (+{growth:.0f}%/5m) | buys {share:.0f}%",
           ' '.join(x['url'] for x in f['socials'][:3]),
           'https://dexscreener.com/solana/'+mint,
           'https://pump.fun/coin/'+mint,
           'https://axiom.trade/t/'+mint,
           'https://gmgn.ai/sol/token/'+mint,FOOTER]
    if now is not None and now-c['at']>60:lines.insert(0,f'LATE {int(now-c["at"])}s — refresh current data')
    return '\n'.join(lines)

def daily_message(data):
    a=data['alerts'];s=data['suppressed'];n=a['count'];counts=a['crossings']
    return '\n'.join([f"Early lane {data.get('day','14-day review')} | {n} selected alerts",
        '2x/3x/5x/10x: '+ '/'.join(str(counts[str(m)]) for m in (2,3,5,10)),
        f"Dead: {a['dead']} | mature/covered {a['mature']}/{a['mature_checkpoint_covered']} | median observed peak {a['median_observed_time_to_peak_s']}s",
        f"Suppressed: {s['count']} | observed 10x rate {s['observed_rates_all']['10']} | mature/covered {s['mature']}/{s['mature_checkpoint_covered']}",
        'Small sample. Observed peak multiples, not realized profit. Missing/immature outcomes remain incomplete.'])

class RateLimited(Exception):
    def __init__(self,retry_after):self.retry_after=retry_after

def flush(lane,transport,confirmation,now):
    if not confirmation.get('confirmed_at') or not confirmation.get('new_channel_confirmed') or not confirmation.get('channel'):
        raise ValueError('new_channel_unconfirmed')
    attempts={r['body']['id']:r['body'] for r in lane.j.rows('send_attempt')}
    if any(now<a['retry_at'] and a.get('rate_limit') for a in attempts.values()):return []
    sent={r['body']['id'] for r in lane.j.rows('sent')};out=[]
    events=[]
    for c in lane.cohorts().values():
        if c['selection']=='ALERT' and not c.get('log_only',True) and c['at']>=confirmation['confirmed_at']:events.append(('alert:'+c['mint'],message(c,now)))
    for kind in ('daily','review'):
        for r in lane.j.rows(kind):
            if r['ts']>=confirmation['confirmed_at']:events.append((r['key'],daily_message(r['body'])))
    for ident,text in events:
        if ident in sent or now<attempts.get(ident,{}).get('retry_at',0):continue
        try:receipt=transport.send(confirmation['channel'],text,idempotency_key=ident)
        except RateLimited as exc:
            lane.j.atomic(lambda:lane.j.add('send_attempt',f'attempt:{ident}:{now}',{'id':ident,'retry_at':now+max(1,exc.retry_after),'rate_limit':True},now));break
        except Exception:
            lane.j.atomic(lambda:lane.j.add('send_attempt',f'attempt:{ident}:{now}',{'id':ident,'retry_at':now+30,'ambiguous_delivery':True},now));break
        else:
            lane.j.atomic(lambda:lane.j.add('sent','sent:'+ident,{'id':ident,'receipt':str(receipt)},now));out.append(ident)
    return out
