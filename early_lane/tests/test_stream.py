import base64
from collections import deque
import copy
import hashlib
import json
from pathlib import Path
import socket
import struct
import tempfile
import types
import unittest
from unittest.mock import patch
import test_evidence as f
from test_lane import NOW
from core import checks,canonical
from pump import PUMP,b58,b58decode,maps,decode_tx
from stream_wire import PublicSocket,ProtocolError,Refused
from stream_events import normalize,StreamGap
from stream_capture import Capture

SIG=b58(b'1'*64)
def notification(value=None,slot=100):
    return dict(method='logsNotification',params=dict(subscription=101,result=dict(context=dict(slot=slot),value=value or trade_value())))
def trade_value(signature=SIG):
    t=f.Parser().trade();logs=copy.deepcopy(t['meta']['logMessages']);logs.insert(1,'Program log: Instruction: Buy')
    return dict(signature=signature,err=None,logs=logs)
def creation_value(signature=SIG):
    _,_,ev=maps();data=ev['CreateEvent']+f.text('DEMO')+f.text('D')+f.text('https://example.org/meta')+b58decode(f.MINT)+b58decode(f.CURVE)+b58decode(f.USER)*2+struct.pack('<q',NOW)+b''.join(f.u64(x)for x in(1100,30,800,1000))
    return dict(signature=signature,err=None,logs=['Program '+PUMP+' invoke [1]','Program log: Instruction: Create','Program data: '+base64.b64encode(data).decode(),'Program '+PUMP+' success'])
def frame(payload,op=1,final=True):
    n=len(payload);head=bytes([(128 if final else 0)|op,n])if n<126 else bytes([(128 if final else 0)|op,126])+struct.pack('!H',n)if n<65536 else bytes([(128 if final else 0)|op,127])+struct.pack('!Q',n)
    return head+payload

class FakeSocket:
    def __init__(self,chunks):self.chunks=deque(chunks);self.sent=[];self.closed=False
    def recv(self,n):
        if not self.chunks:return b''
        part=self.chunks.popleft()
        if isinstance(part,Exception):raise part
        if len(part)>n:self.chunks.appendleft(part[n:])
        return part[:n]
    def sendall(self,data):self.sent.append(data)
    def close(self):self.closed=True
    def settimeout(self,*args):pass

class Wire(unittest.TestCase):
    def ws(self,*chunks):w=PublicSocket();w.sock=FakeSocket(chunks);return w
    def test_text_json(self):self.assertEqual(self.ws(frame(b'{"a":1}')).receive(),{'a':1})
    def test_extended_length_16(self):self.assertEqual(len(self.ws(frame(json.dumps('a'*200).encode())).receive()),200)
    def test_extended_length_64(self):self.assertEqual(len(self.ws(frame(json.dumps('a'*66000).encode())).receive()),66000)
    def test_fragment_and_ping(self):
        w=self.ws(frame(b'{"a":',final=False)+frame(b'hello',9)+frame(b'1}',0));self.assertEqual(w.receive(),{'a':1});self.assertEqual(w.sock.sent[0][0]&15,10)
    def test_timeout_preserves_partial_frame(self):
        b=frame(b'{"a":1}');w=self.ws(b[:5],socket.timeout(),b[5:])
        with self.assertRaises(socket.timeout):w.receive()
        self.assertEqual(w.receive(),{'a':1})
    def test_timeout_preserves_fragment_sequence(self):
        w=self.ws(frame(b'{"a":',final=False),socket.timeout(),frame(b'1}',0))
        with self.assertRaises(socket.timeout):w.receive()
        self.assertEqual(w.receive(),{'a':1})
    def test_masked_server_refused(self):
        with self.assertRaises(ProtocolError):self.ws(b'\x81\x80').receive()
    def test_bound_checked_before_reading_large_body(self):
        with self.assertRaises(ProtocolError):self.ws(b'\x81\x7f'+struct.pack('!Q',PublicSocket.LIMIT+1)).receive()
    def test_bad_control_fragment_refused(self):
        with self.assertRaises(ProtocolError):self.ws(frame(b'',9,False)).receive()
    def test_orphan_fragment_refused(self):
        with self.assertRaises(ProtocolError):self.ws(frame(b'1',0)).receive()
    def test_nested_fragment_refused(self):
        with self.assertRaises(ProtocolError):self.ws(frame(b'{',final=False)+frame(b'{}')).receive()
    def test_binary_refused(self):
        with self.assertRaises(ProtocolError):self.ws(frame(b'1',2)).receive()
    def test_close_disconnects(self):
        with self.assertRaises(OSError):self.ws(frame(b'',8)).receive()
    def test_sends_only_fixed_readonly_subscriptions(self):
        w=self.ws();w.subscribe(1,PUMP);w.subscribe(2)
        for wire in w.sock.sent:
            n=wire[1]&127;offset=2
            if n==126:n=struct.unpack('!H',wire[2:4])[0];offset=4
            mask=wire[offset:offset+4];data=wire[offset+4:];value=json.loads(bytes(x^mask[i%4]for i,x in enumerate(data)));self.assertIn(value['method'],('logsSubscribe','rootSubscribe'));self.assertEqual(len(data),n)
        with self.assertRaises(ProtocolError):w.subscribe(3,'unapproved')
    def test_http_429_preserves_retry_after(self):
        fake=FakeSocket([b'HTTP/1.1 429 Too Many Requests\r\nRetry-After: 180\r\n\r\n'])
        with patch('stream_wire.socket.create_connection',return_value=fake),patch('stream_wire.ssl.create_default_context')as ctx:
            ctx.return_value.wrap_socket.return_value=fake
            with self.assertRaises(Refused)as caught:PublicSocket().connect()
        self.assertEqual(caught.exception.retry_after,180);self.assertTrue(fake.closed)
    def test_invalid_upgrade_accept_refused(self):
        fake=FakeSocket([b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: wrong\r\n\r\n'])
        with patch('stream_wire.socket.create_connection',return_value=fake),patch('stream_wire.ssl.create_default_context')as ctx:
            ctx.return_value.wrap_socket.return_value=fake
            with self.assertRaises(ProtocolError):PublicSocket().connect()

    def test_frame_total_deadline_is_bounded(self):
        w=self.ws(frame(b'{}'));w.frame_started=1
        with patch('stream_wire.time.monotonic',return_value=17):
            with self.assertRaisesRegex(ProtocolError,'frame_deadline'):w.receive()

class Events(unittest.TestCase):
    def test_trade_parity_with_existing_authenticated_decoder(self):
        event=normalize(trade_value(),NOW)['trades'][0];reference=decode_tx(f.Parser().trade(),f.MINT,SIG)['trades'][0]
        for k in ('user','side','at','qty','quote_lamports','event'):self.assertEqual(event[k],reference[k])
    def test_creation_provisional_not_admitted(self):
        c=normalize(creation_value(),NOW);self.assertEqual(c['creations'][0]['mint'],f.MINT);self.assertFalse(c['admissible_for_screening'])
    def test_failed_transaction_has_no_events(self):
        v=trade_value();v['err']={'InstructionError':[1,'Custom']};self.assertEqual(normalize(v,NOW)['trades'],[]);self.assertFalse(normalize(v,NOW)['admissible_for_screening'])
    def test_invalid_failure_status_is_gap(self):
        v=trade_value();v['err']=False
        with self.assertRaises(StreamGap):normalize(v,NOW)
    def test_spoofed_other_program_event_cannot_match_buy(self):
        v=trade_value();v['logs'][0]='Program '+f.key(9)+' invoke [1]';v['logs'][-1]='Program '+f.key(9)+' success';self.assertEqual(normalize(v,NOW)['trades'],[])
    def test_missing_economic_event_is_gap(self):
        v=trade_value();v['logs']=[x for x in v['logs']if not x.startswith('Program data:')]
        with self.assertRaisesRegex(StreamGap,'trade_event_coverage'):normalize(v,NOW)
    def test_unknown_pump_method_is_gap(self):
        v=trade_value();v['logs'][1]='Program log: Instruction: FutureSwap'
        with self.assertRaises(StreamGap):normalize(v,NOW)
    def test_truncated_log_is_gap(self):
        v=trade_value();v['logs'].insert(1,'Log truncated')
        with self.assertRaises(StreamGap):normalize(v,NOW)
    def test_nested_program_does_not_spoof_event(self):
        v=trade_value();v['logs'].insert(2,'Program '+f.key(9)+' invoke [2]');v['logs'].insert(4,'Program '+f.key(9)+' success')
        with self.assertRaisesRegex(StreamGap,'trade_event_coverage'):normalize(v,NOW)
    def test_future_or_stale_event_is_gap(self):
        for at in(NOW-1,NOW+61):
            with self.assertRaises(StreamGap):normalize(trade_value(),at)
    def test_invalid_signature_refused(self):
        v=trade_value();v['signature']='not-a-signature'
        with self.assertRaises(StreamGap):normalize(v,NOW)
    def test_wrong_invocation_stack_refused(self):
        v=trade_value();v['logs'][-1]='Program '+f.key(9)+' success'
        with self.assertRaises(StreamGap):normalize(v,NOW)

    def test_unsupported_zero_quote_gap_is_scoped_and_never_counted(self):
        from stream_events import MintGap
        t=f.Parser().trade(sol=0);logs=t['meta']['logMessages'];logs.insert(1,'Program log: Instruction: Buy')
        with self.assertRaises(MintGap)as err:normalize(dict(signature=SIG,err=None,logs=logs),NOW)
        self.assertEqual(err.exception.mints,[f.MINT])

    def test_scoped_error_covers_every_mint_in_atomic_notification(self):
        from stream_events import MintGap
        logs=f.Parser().trade(sol=0)['meta']['logMessages'];raw=base64.b64decode(logs[1].split(': ',1)[1]);other=raw[:8]+b58decode(f.key(99))+struct.pack('<Q',10)+raw[48:]
        logs.insert(1,'Program log: Instruction: Buy');logs.insert(-1,'Program log: Instruction: Buy');logs.insert(-1,'Program data: '+base64.b64encode(other).decode())
        with self.assertRaises(MintGap)as err:normalize(dict(signature=SIG,err=None,logs=logs),NOW)
        self.assertEqual(set(err.exception.mints),{f.MINT,f.key(99)})

class Store(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name);self.c=Capture(self.path);self.c.begin(NOW-10)
    def tearDown(self):self.c.close();self.tmp.cleanup()
    def ready(self):
        self.c.ingest(dict(id=1,result=101),NOW-9);self.c.ingest(dict(id=2,result=102),NOW-9)
    def test_requires_both_subscription_acknowledgments(self):
        self.assertFalse(self.c.report()['subscription_ready']);self.c.ingest(dict(id=1,result=101),NOW);self.assertFalse(self.c.report()['subscription_ready']);self.c.ingest(dict(id=2,result=102),NOW);self.assertTrue(self.c.report()['subscription_ready'])
    def test_duplicate_ack_refused(self):
        self.ready()
        with self.assertRaises(StreamGap):self.c.ingest(dict(id=1,result=101),NOW)
    def test_wrong_subscription_cannot_write_events(self):
        self.ready();m=notification();m['params']['subscription']=999
        with self.assertRaises(StreamGap):self.c.ingest(m,NOW)
        self.assertEqual(self.c.report()['trades'],0)
    def test_trade_idempotency_persists_restart(self):
        self.ready();m=notification();self.c.ingest(m,NOW);self.c.ingest(m,NOW);self.assertEqual(self.c.report()['trades'],1);self.c.close();self.c=Capture(self.path);self.c.begin(NOW+1);self.ready();self.c.ingest(m,NOW+1);self.assertEqual(self.c.report()['retained_trades'],1)
    def test_conflicting_duplicate_refused(self):
        self.ready();m=notification();self.c.ingest(m,NOW);m['params']['result']['value']['logs'].insert(2,'Program log: harmless extra line')
        with self.assertRaisesRegex(StreamGap,'conflicting_signature'):self.c.ingest(m,NOW)
    def test_reconnect_opens_new_generation_and_clears_readiness(self):
        self.ready();old=self.c.get('generation');self.c.begin(NOW);self.assertGreater(self.c.get('generation'),old);self.assertFalse(self.c.get('ready'))
    def test_gap_is_durable_hash_chained_audit(self):
        self.c.gap('test_gap',NOW);g=self.c.get('generation');self.assertTrue(list(self.c.audit.rows('stream_gap')));self.c.audit.verify();self.c.close();self.c=Capture(self.path);self.assertEqual(self.c.get('generation'),g)
    def test_shadow_events_never_pass_history_gates(self):
        self.ready();self.c.ingest(notification(),NOW);self.assertFalse(self.c.report()['admissible_for_screening']);self.assertFalse((self.path/'lane.sqlite3').exists());event=json.loads(self.c.db.execute('SELECT body FROM trades').fetchone()[0]);out=checks(event,NOW)
        for k in('unique_buyers','buyer_growth','first_two_blocks'):self.assertEqual(out[k],'UNKNOWN')
    def test_cache_retention_does_not_delete_audit(self):
        self.ready();self.c.ingest(notification(),NOW);before=self.c.audit.verify();self.c.prune(NOW+1861);self.assertEqual(self.c.report()['retained_trades'],0);self.assertEqual(self.c.audit.verify(),before)
    def test_root_monotonicity(self):
        self.ready();self.c.ingest(dict(method='rootNotification',params=dict(subscription=102,result=100)),NOW)
        with self.assertRaises(StreamGap):self.c.ingest(dict(method='rootNotification',params=dict(subscription=102,result=99)),NOW)
    def reference(self):
        c=dict(mint=f.MINT,curve=f.CURVE,creator=f.USER,created_at=NOW,signature=SIG,initial_supply=1000,initial_curve_tokens=800)
        rows=[dict(signature=SIG,complete=True,creation=c,trades=decode_tx(f.Parser().trade(),f.MINT,SIG)['trades'])]
        return rows,c,NOW
    def test_fresh_full_rpc_recovery_audited_not_promoted(self):
        self.ready();self.c.ingest(notification(),NOW);ref=self.reference();body=self.c.recover(f.MINT,types.SimpleNamespace(history=lambda mint:ref),NOW);self.assertEqual(body['stream_rows_compared'],1);self.assertFalse(body['admissible_for_screening']);self.assertTrue(list(self.c.audit.rows('gap_recovery')))
    def test_stale_rpc_cannot_recover(self):
        rows,c,at=self.reference()
        with self.assertRaises(StreamGap):self.c.recover(f.MINT,types.SimpleNamespace(history=lambda mint:(rows,c,at-61)),NOW)
        self.assertFalse(list(self.c.audit.rows('gap_recovery')))
    def test_snapshot_before_gap_cannot_recover(self):
        self.c.gap('gap',NOW+1)
        with self.assertRaises(StreamGap):self.c.recover(f.MINT,types.SimpleNamespace(history=lambda mint:self.reference()),NOW+2)
    def test_incomplete_rpc_rows_cannot_recover(self):
        rows,c,at=self.reference();rows[0]['error']='unsupported'
        with self.assertRaises(StreamGap):self.c.recover(f.MINT,types.SimpleNamespace(history=lambda mint:(rows,c,at)),NOW)
    def test_rpc_trade_mismatch_cannot_recover(self):
        self.ready();self.c.ingest(notification(),NOW);rows,c,at=self.reference();rows[0]['trades'][0]['qty']+=1
        with self.assertRaisesRegex(StreamGap,'stream_rpc_mismatch'):self.c.recover(f.MINT,types.SimpleNamespace(history=lambda mint:(rows,c,at)),NOW)
    def test_cooldown_survives_reopen(self):
        with self.c.db:self.c.put('cooldown',NOW+180)
        self.c.close();self.c=Capture(self.path);self.assertEqual(self.c.get('cooldown'),NOW+180)

    def test_recovery_covers_only_snapshot_not_future_stream(self):
        self.ready();self.c.ingest(notification(),NOW);self.c.recover(f.MINT,types.SimpleNamespace(history=lambda mint:self.reference()),NOW)
        self.assertEqual(self.c.coverage(f.MINT,NOW+1)['covered_through'],NOW);self.assertEqual(self.c.coverage(f.MINT,NOW+61)['status'],'RECOVERY_STALE')
    def test_new_gap_invalidates_old_recovery(self):
        self.ready();self.c.recover(f.MINT,types.SimpleNamespace(history=lambda mint:self.reference()),NOW);self.c.gap('new_gap',NOW+1)
        self.assertEqual(self.c.coverage(f.MINT,NOW+1)['status'],'GAP_NEEDS_RPC')
    def test_creator_conflict_cannot_be_recovered(self):
        self.ready();self.c.ingest(notification(creation_value()),NOW);rows,c,at=self.reference();c['creator']=f.key(99)
        with self.assertRaisesRegex(StreamGap,'creation_conflict'):self.c.recover(f.MINT,types.SimpleNamespace(history=lambda mint:(rows,c,at)),NOW)

    def test_mint_gap_does_not_invalidate_unrelated_creation(self):
        self.ready();self.c.ingest(notification(creation_value()),NOW);g=self.c.get('generation');self.c.gap('unsupported_quote',NOW,[f.key(99)])
        self.assertEqual(self.c.get('generation'),g);self.assertEqual(self.c.coverage(f.MINT,NOW)['status'],'CAPTURED_UNVERIFIED');self.assertEqual(self.c.coverage(f.key(99),NOW)['status'],'GAP_NEEDS_RPC')
    def test_scoped_gap_invalidates_older_rpc_proof(self):
        self.ready();self.c.recover(f.MINT,types.SimpleNamespace(history=lambda mint:self.reference()),NOW);self.c.gap('unsupported_quote',NOW+1,[f.MINT]);self.assertEqual(self.c.coverage(f.MINT,NOW+1)['status'],'GAP_NEEDS_RPC')
    def test_old_rpc_snapshot_cannot_recover_scoped_gap(self):
        self.ready();self.c.gap('unsupported_quote',NOW+1,[f.MINT])
        with self.assertRaises(StreamGap):self.c.recover(f.MINT,types.SimpleNamespace(history=lambda mint:self.reference()),NOW+2)

class Worker(unittest.TestCase):
    def test_retry_after_prevents_reconnects_within_bounded_run(self):
        from stream_capture import run
        class Clock:
            elapsed=0
            def mono(self):return self.elapsed
            def wall(self):return NOW+self.elapsed
            def sleep(self,n):self.elapsed+=n
        clock=Clock()
        with tempfile.TemporaryDirectory()as d,patch('stream_capture.time.monotonic',side_effect=clock.mono),patch('stream_capture.time.time',side_effect=clock.wall),patch('stream_capture.time.sleep',side_effect=clock.sleep),patch('stream_capture.shutil.disk_usage',return_value=types.SimpleNamespace(free=5*1024**3)),patch('stream_capture.PublicSocket')as ws:
            ws.return_value.connect.side_effect=Refused(429,180);result=run(d,10)
            self.assertEqual(result['attempts'],1);self.assertEqual(result['telegram_sent'],0);self.assertFalse(result['admissible_for_screening']);self.assertEqual(ws.return_value.connect.call_count,1)
            c=Capture(d);self.assertEqual(c.get('cooldown'),NOW+180);c.close()

if __name__=='__main__':unittest.main()
