"""Transport-injected delivery queue. No credentials, network or Telegram API client.

A separately reviewed existing authenticated sender can be injected AFTER destination
confirmation. This release never acquires tokens/keys or sends from service/tests.
"""
from tickets import render
from journal import SKIP_REASONS

class RateLimited(Exception):
    def __init__(self,retry_after):self.retry_after=retry_after

def flush(j,transport,config,now):
    if not config.get('destination_confirmed') or not config.get('destination'):
        raise ValueError('destination_unconfirmed')
    sent=[]
    rate_until=max((a.get('next_try',0) for a in j.state(now)['attempts'].values() if a.get('reason')=='rate_limit'),default=0)
    if now<rate_until:return sent
    for ident,ticket in j.state(now)['tickets'].items():
        state=j.state(now)
        if ident in state['delivered']:continue
        previous=state['attempts'].get(ident,{})
        if now<previous.get('next_try',0):continue
        text=render(ticket,now)
        if not state['enabled']:
            text='WITHDRAWN: cumulative realized loss limit reached.\n'+text
        elif state['daily_loss']>=15 and not ticket['review_only']:
            text='REVIEW ONLY, daily limit reached\n'+text
        try:
            receipt=transport.send(config['destination'],text,ticket['buttons'],idempotency_key=ident)
        except RateLimited as exc:
            j.transaction(lambda:j.append('delivery_attempt',f'delivery:{ident}:{now}',{'ticket':ident,'next_try':now+max(1,exc.retry_after),'reason':'rate_limit'},now))
            break  # Telegram-wide cooldown; no drops or rapid send retries.
        except Exception:
            j.transaction(lambda:j.append('delivery_attempt',f'delivery:{ident}:{now}',{'ticket':ident,'next_try':now+30,'reason':'transport_error_ambiguous_delivery'},now))
            break
        else:
            j.transaction(lambda:j.append('delivered','delivered:'+ident,{'ticket':ident,'receipt':str(receipt)},now));sent.append(ident)
    return sent

def callback(j,callback_id,ticket,action,owner_authenticated=False,reason=None,now=None):
    if not owner_authenticated:raise ValueError('unauthenticated_callback')
    if action=='SKIP' and reason is None:
        return {'prompt':'One short reason','choices':list(SKIP_REASONS)}
    return j.button(callback_id,ticket,action,reason,now)

# Optional adapter for a separately approved EXISTING authenticated sender. The
# desk neither reads tokens nor implements a new credential-bearing bot service.
import json
import os
from pathlib import Path
import socket
import stat
import struct
from common import canonical

def load_confirmed(path):
    p=Path(path);s=p.lstat()
    if not stat.S_ISREG(s.st_mode) or s.st_uid!=0 or s.st_mode & 0o022:
        raise ValueError('delivery_config_must_be_root_owned_not_writable_by_others')
    c=json.loads(p.read_text())
    if c.get('destination_confirmed') is not True or not c.get('confirmed_at') or not c.get('destination') or not c.get('owner_id') or not c.get('socket'):
        raise ValueError('destination_and_existing_sender_not_confirmed')
    return c

class UnixTransport:
    """Root-peer, size-bounded Unix JSON bridge. Protocol must deduplicate send key.

    Requires an already authorized credential-bearing sender exposing this contract.
    No such sender is installed by this project; unavailable means no delivery.
    """
    def __init__(self,path):self.path=path
    def request(self,body):
        p=Path(self.path);s=p.lstat()
        if not stat.S_ISSOCK(s.st_mode) or s.st_uid!=0 or s.st_mode & 0o002:
            raise ValueError('untrusted_sender_socket')
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
            client.settimeout(5);client.connect(str(p))
            _,uid,_=struct.unpack('3i',client.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            if uid!=0:raise ValueError('sender_peer_not_root')
            client.sendall((canonical(body)+'\n').encode());data=b''
            while b'\n' not in data and len(data)<=262144:
                part=client.recv(16384)
                if not part:break
                data+=part
            if len(data)>262144 or b'\n' not in data:raise ValueError('sender_response_shape')
            result=json.loads(data.split(b'\n')[0])
            if result.get('retry_after') is not None:raise RateLimited(float(result['retry_after']))
            if result.get('ok') is not True:raise ValueError('sender_refused')
            return result
    def send(self,destination,text,buttons,idempotency_key):
        return self.request(dict(op='send_ticket',destination=destination,text=text,buttons=buttons,idempotency_key=idempotency_key)).get('receipt')
    def updates(self):
        return self.request({'op':'owner_updates'}).get('updates',[])

    def prompt_skip(self,destination,ticket,callback_id):
        return self.request(dict(op='send_skip_reasons',destination=destination,ticket=ticket,choices=list(SKIP_REASONS),idempotency_key='skip-prompt:'+callback_id))
