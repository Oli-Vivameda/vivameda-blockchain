"""Optional owner-provided credential-free Unix sender interface.

No Telegram credential is read by early lane. The owner must supply an existing
sender implementing this protocol; none is installed or assumed to exist.
"""
import html
import json
import os
from pathlib import Path
import socket
import stat
import struct
from alerts import RateLimited
from core import canonical

def configuration(path):
    p=Path(path);st=p.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_mode&0o022:raise ValueError('delivery_config_requires_root_owned_nonwritable_file')
    data=json.loads(p.read_text())
    if data.get('new_channel_confirmed'):
        if not str(data.get('channel','')).startswith('-100') or not str(data['channel'])[1:].isdigit() or not data.get('confirmed_at'):raise ValueError('confirmed_new_channel_required')
        if not Path(data.get('socket','')).is_absolute():raise ValueError('absolute_sender_socket_required')
    return data

class UnixSender:
    def __init__(self,path):self.path=path
    def send(self,channel,text,idempotency_key):
        p=Path(self.path);st=p.lstat()
        if not stat.S_ISSOCK(st.st_mode) or st.st_uid!=0 or st.st_mode&0o002:raise ValueError('trusted_sender_socket_required')
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
            s.settimeout(10);s.connect(str(p))
            pid,uid,gid=struct.unpack('3i',s.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            if uid!=0:raise ValueError('sender_peer_not_root')
            safe=html.escape(text);parts=safe.split('```');safe=''.join(part if i%2==0 else '<pre>'+part+'</pre>' for i,part in enumerate(parts))
            s.sendall((canonical({'protocol':'vivameda-early-lane-send-v1','channel':channel,'text':safe,'parse_mode':'HTML','idempotency_key':idempotency_key})+'\n').encode())
            raw=b''
            while b'\n' not in raw and len(raw)<=65536:
                chunk=s.recv(4096)
                if not chunk:raise ValueError('sender_response_truncated')
                raw+=chunk
            if len(raw)>65536:raise ValueError('sender_response_bound')
            response=json.loads(raw.split(b'\n',1)[0])
            if response.get('status')==429:raise RateLimited(max(1,float(response['retry_after'])))
            if response.get('status')!=200 or not response.get('receipt'):raise ValueError('sender_delivery_unconfirmed')
            return response['receipt']
