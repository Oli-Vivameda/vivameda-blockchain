import json
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from transport import UnixSender
from alerts import RateLimited
ROOT=Path(__file__).resolve().parents[1]

class FakeSocket:
    def __init__(self,response,uid=0):self.response=response;self.uid=uid;self.wire=b''
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def settimeout(self,*a):pass
    def connect(self,*a):pass
    def getsockopt(self,*a):return struct.pack('3i',10,self.uid,0)
    def sendall(self,data):self.wire=data
    def recv(self,*a):return json.dumps(self.response).encode()+b'\n'

class Contracts(unittest.TestCase):
    def send(self,response,uid=0):
        fake=FakeSocket(response,uid)
        with patch('transport.Path.lstat',return_value=types.SimpleNamespace(st_mode=stat.S_IFSOCK|0o660,st_uid=0)),patch('transport.socket.socket',return_value=fake):
            result=UnixSender('/run/reviewed.sock').send('-100123','A < B\n```\nmint\n```','event-key')
        return result,fake
    def test_sender_protocol_html_and_idempotency(self):
        result,fake=self.send(dict(status=200,receipt='receipt'));self.assertEqual(result,'receipt');wire=json.loads(fake.wire)
        self.assertEqual(wire['idempotency_key'],'event-key');self.assertEqual(wire['parse_mode'],'HTML');self.assertIn('A &lt; B',wire['text']);self.assertIn('<pre>',wire['text'])
    def test_sender_rate_limit_propagates(self):
        with self.assertRaises(RateLimited):self.send(dict(status=429,retry_after=600))
    def test_untrusted_peer_rejected(self):
        with self.assertRaisesRegex(ValueError,'peer_not_root'):self.send(dict(status=200,receipt='r'),uid=994)
    def test_no_receipt_not_success(self):
        with self.assertRaises(ValueError):self.send(dict(status=200))
    def test_owner_wrong_bundle_stops_before_project_imports(self):
        run=subprocess.run([sys.executable,'-B',str(ROOT/'owner.py'),'--expected-bundle','0'*64,'export','--','--output','/does/not/exist'],capture_output=True,text=True)
        self.assertNotEqual(run.returncode,0);self.assertIn('no protected data opened',run.stderr)

if __name__=='__main__':unittest.main()
