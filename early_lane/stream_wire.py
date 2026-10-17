"""Bounded RFC6455 client for the fixed public read-only Solana PubSub endpoint."""
import base64
import hashlib
import json
import os
import socket
import ssl
import struct
import time
from sources import retry_seconds
from pump import PUMP,AMM

class ProtocolError(ValueError):pass
class Refused(OSError):
    def __init__(self,status,delay):self.status=status;self.retry_after=delay;super().__init__('public_websocket_refused')

class PublicSocket:
    LIMIT=4*1024*1024
    def __init__(self):self.sock=None;self.buffer=bytearray();self.fragment=bytearray();self.fragmenting=False;self.frame_started=None
    def connect(self):
        raw=socket.create_connection(('api.mainnet-beta.solana.com',443),timeout=10)
        try:self.sock=ssl.create_default_context().wrap_socket(raw,server_hostname='api.mainnet-beta.solana.com')
        except BaseException:raw.close();raise
        try:
            key=base64.b64encode(os.urandom(16)).decode()
            request='GET / HTTP/1.1\r\nHost: api.mainnet-beta.solana.com\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Key: '+key+'\r\nUser-Agent: Vivameda-Early-Lane-Shadow/1\r\n\r\n'
            self.sock.sendall(request.encode());header=bytearray();deadline=time.monotonic()+10
            while not header.endswith(b'\r\n\r\n'):
                if time.monotonic()>deadline:raise ProtocolError('handshake_deadline')
                b=self.sock.recv(1)
                if not b:raise OSError('handshake_closed')
                header.extend(b)
                if len(header)>16384:raise ProtocolError('handshake_bound')
            lines=header.decode('ascii').split('\r\n');status=int(lines[0].split()[1]);headers={}
            for line in lines[1:]:
                if ':'in line:
                    k,v=line.split(':',1);k=k.lower()
                    if k in headers:raise ProtocolError('duplicate_handshake_header')
                    headers[k]=v.strip()
            if status!=101:raise Refused(status,retry_seconds(headers))
            want=base64.b64encode(hashlib.sha1((key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
            if headers.get('sec-websocket-accept')!=want or headers.get('upgrade','').lower()!='websocket'or'upgrade'not in[x.strip()for x in headers.get('connection','').lower().split(',')]:raise ProtocolError('invalid_upgrade')
            self.sock.settimeout(2);return self
        except BaseException:self.close();raise
    def close(self):
        if self.sock:self.sock.close();self.sock=None
    def _send(self,data,opcode=1):
        n=len(data)
        if n>self.LIMIT:raise ProtocolError('client_message_bound')
        mask=os.urandom(4);head=bytes([128|opcode,128|n])if n<126 else bytes([128|opcode,254])+struct.pack('!H',n)if n<65536 else bytes([128|opcode,255])+struct.pack('!Q',n)
        self.sock.sendall(head+mask+bytes(c^mask[i%4]for i,c in enumerate(data)))
    def subscribe(self,ident,program=None):
        if type(ident)is not int or ident<=0:raise ProtocolError('request_id')
        if program is not None and program not in(PUMP,AMM):raise ProtocolError('program_not_allowed')
        method='logsSubscribe'if program else'rootSubscribe';params=[{'mentions':[program]},{'commitment':'confirmed'}]if program else[]
        self._send(json.dumps({'jsonrpc':'2.0','id':ident,'method':method,'params':params}).encode())
    def ping(self):self._send(b'',9)
    def _ensure(self,n):
        while len(self.buffer)<n:
            if self.frame_started is not None and time.monotonic()-self.frame_started>15:raise ProtocolError('frame_deadline')
            data=self.sock.recv(min(65536,n-len(self.buffer)))
            if not data:raise OSError('websocket_closed')
            self.buffer.extend(data)
    def _frame(self):
        if self.frame_started is None:self.frame_started=time.monotonic()
        self._ensure(2);a,b=self.buffer[:2];final=bool(a&128);opcode=a&15;n=b&127;offset=2
        if a&112 or b&128:raise ProtocolError('reserved_or_masked_server_frame')
        if n==126:self._ensure(4);n=struct.unpack('!H',self.buffer[2:4])[0];offset=4
        elif n==127:self._ensure(10);n=struct.unpack('!Q',self.buffer[2:10])[0];offset=10
        if n>self.LIMIT:raise ProtocolError('server_message_bound')
        if opcode>=8 and(not final or n>125):raise ProtocolError('invalid_control_frame')
        self._ensure(offset+n);payload=bytes(self.buffer[offset:offset+n]);del self.buffer[:offset+n];self.frame_started=None
        return final,opcode,payload
    def receive(self):
        while True:
            final,opcode,payload=self._frame()
            if opcode==8:raise OSError('server_close')
            if opcode==9:self._send(payload,10);continue
            if opcode==10:continue
            if opcode==1:
                if self.fragmenting:raise ProtocolError('nested_fragment')
                if final:return json.loads(payload.decode('utf-8'))
                self.fragment=bytearray(payload);self.fragmenting=True
            elif opcode==0:
                if not self.fragmenting:raise ProtocolError('orphan_fragment')
                if len(self.fragment)+len(payload)>self.LIMIT:raise ProtocolError('fragment_bound')
                self.fragment.extend(payload)
                if final:
                    data=bytes(self.fragment);self.fragment.clear();self.fragmenting=False;return json.loads(data.decode('utf-8'))
            else:raise ProtocolError('unsupported_opcode')
