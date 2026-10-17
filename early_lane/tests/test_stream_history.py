import copy
import json
from pathlib import Path
import sqlite3
import struct
import tempfile
import unittest
from unittest.mock import patch
import test_evidence as f
from test_lane import NOW,facts
from test_stream import notification,trade_value
from core import canonical,checks
from pump import b58,b58decode,maps,decode_tx
from sources import SourceUnavailable
from stream_capture import Capture
from stream_history import StreamCollector

CREATE=b58(b'c'*64);TRADE=b58(b't'*64)
def entry(sig,slot=100,at=NOW,error=None):return dict(signature=sig,slot=slot,blockTime=at,err=error,confirmationStatus='finalized')
def creation_tx():
    _,_,e=maps();data=e['CreateEvent']+f.text('DEMO')+f.text('D')+f.text('https://example.org/meta')+b58decode(f.MINT)+b58decode(f.CURVE)+b58decode(f.USER)*2+struct.pack('<q',NOW-600)+b''.join(f.u64(x)for x in(1100,30,800,1000))
    ix=f.tx_instruction('create',dict(mint=f.MINT,user=f.USER,bonding_curve=f.CURVE),f.text('DEMO')+f.text('D')+f.text('https://example.org/meta')+b58decode(f.USER))
    tx=f.tx([ix],[data]);tx['blockTime']=NOW-600;tx['transaction']['signatures']=[CREATE];return tx

class History(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name);self.capture=Capture(self.path/'stream');self.capture.begin(NOW-1)
        self.capture.ingest(dict(id=1,result=101),NOW);self.capture.ingest(dict(id=2,result=102),NOW)
        self.c=StreamCollector(self.path/'rpc',self.path/'stream');self.c.rpc.budget(100)
        self.calls=[];self.page=[entry(TRADE,101),entry(CREATE,100,NOW-600)];self.origin=creation_tx();self.trade=f.Parser().trade();self.trade['slot']=101;self.trade['transaction']['signatures']=[TRADE]
        def rpc(method,params):
            self.calls.append((method,params))
            if method=='getSignaturesForAddress':return copy.deepcopy(self.page)
            if method=='getTransaction':return copy.deepcopy(self.origin if params[0]==CREATE else self.trade)
            raise AssertionError(method)
        self.rpc=patch.object(self.c.rpc,'call',side_effect=rpc);self.rpc.start();self.clock=patch('stream_history.time.time',return_value=NOW);self.clock.start()
    def tearDown(self):self.clock.stop();self.rpc.stop();self.c.cache.close();self.capture.close();self.tmp.cleanup()
    def ingest(self):self.capture.ingest(notification(trade_value(TRADE),101),NOW)
    def history(self):return self.c.history(f.MINT)
    def test_reuses_trade_fetches_original_creation_only(self):
        self.ingest();rows,c,at=self.history();self.assertEqual(c['creator'],f.USER);self.assertEqual(at,NOW);self.assertEqual(sum(x[0]=='getTransaction'for x in self.calls),1);self.assertEqual(self.c.metrics['reused_stream_transactions'],1)
        self.assertEqual(rows[1]['trades'][0]['at'],NOW)
    def test_missing_trade_repaired_once_durably(self):
        self.history();self.assertEqual(self.c.metrics['canonical_repairs'],2)
        self.page=[entry(TRADE,101),entry(CREATE,100,NOW-600)];self.history();self.assertEqual(self.c.metrics['canonical_repairs'],2)
    def test_conflicting_notification_uses_finalized_transaction(self):
        self.ingest();v=trade_value(TRADE);v['logs'].insert(2,'Program log: changed')
        with self.assertRaises(ValueError):self.capture.ingest(notification(v,101),NOW)
        self.history();self.assertEqual(self.c.metrics['reused_stream_transactions'],0);self.assertEqual(self.c.metrics['canonical_repairs'],2)
    def test_conflict_after_cached_fast_path_repaired_before_next_proof(self):
        self.ingest();self.history();v=trade_value(TRADE);v['logs'].insert(2,'Program log: changed')
        with self.assertRaises(ValueError):self.capture.ingest(notification(v,101),NOW)
        self.history();self.assertEqual(self.c.metrics['canonical_repairs'],2)
    def test_failed_signatures_do_not_cost_transaction_calls(self):
        bad=b58(b'f'*64);self.page.insert(0,entry(bad,102,error={'InstructionError':[0,'x']}));self.ingest();rows,_,_=self.history();self.assertTrue(rows[-1]['failed']);self.assertEqual(self.c.metrics['canonical_repairs'],1)
    def test_unknown_failure_status_refused(self):
        self.page[0]['err']=False
        with self.assertRaisesRegex(SourceUnavailable,'signature_status'):self.history()
    def test_confirmed_is_not_finalized(self):
        self.page[0]['confirmationStatus']='confirmed'
        with self.assertRaises(SourceUnavailable):self.history()
    def test_missing_status_refused(self):
        del self.page[0]['err']
        with self.assertRaises(SourceUnavailable):self.history()
    def test_duplicate_signature_page_refused(self):
        self.page.append(self.page[-1])
        with self.assertRaises(SourceUnavailable):self.history()
    def test_out_of_order_slots_refused(self):
        self.page.reverse()
        with self.assertRaises(SourceUnavailable):self.history()
    def test_invalid_signature_refused(self):
        self.page[0]['signature']='wrong'
        with self.assertRaises(SourceUnavailable):self.history()
    def test_wrong_canonical_signature_refused(self):
        self.origin['transaction']['signatures']=[TRADE]
        with self.assertRaisesRegex(SourceUnavailable,'transaction_identity'):self.history()
    def test_wrong_canonical_slot_refused(self):
        self.origin['slot']=99
        with self.assertRaises(SourceUnavailable):self.history()
    def test_conflicting_success_status_refused(self):
        self.origin['meta']['err']={'x':1}
        with self.assertRaises(SourceUnavailable):self.history()
    def test_wrong_canonical_time_refused(self):
        self.origin['blockTime']-=1
        with self.assertRaises(SourceUnavailable):self.history()
    def test_creator_not_signer_blocks_full_history(self):
        self.origin['transaction']['message']['accountKeys'][0]['signer']=False
        with self.assertRaisesRegex(SourceUnavailable,'incomplete_trade_history'):self.history()
    def test_missing_creation_blocks_full_history(self):
        self.page=self.page[:1];self.ingest()
        with self.assertRaisesRegex(SourceUnavailable,'creation_provenance'):self.history()
    def test_zero_trade_is_not_repaired_into_pass(self):
        self.trade=f.Parser().trade(sol=0);self.trade['slot']=101;self.trade['transaction']['signatures']=[TRADE]
        with self.assertRaisesRegex(SourceUnavailable,'incomplete_trade_history'):self.history()
    def test_stream_slot_mismatch_falls_back(self):
        self.capture.ingest(notification(trade_value(TRADE),102),NOW);self.history();self.assertEqual(self.c.metrics['canonical_repairs'],2)
    def test_missing_stream_time_uses_canonical(self):
        self.ingest();self.page[0]['blockTime']=None;self.history();self.assertEqual(self.c.metrics['canonical_repairs'],2)
    def test_stream_timestamp_parity_uses_rpc_block_time(self):
        self.ingest();self.page[0]['blockTime']=NOW-1;self.trade['blockTime']=NOW-1;rows,_,_=self.history();self.assertEqual(rows[1]['trades'][0]['at'],NOW-1)
    def test_stale_completed_scan_advances_cursor_without_proof(self):
        self.ingest()
        original=self.c.canonical_transaction
        def slow(e):
            out=original(e);self.clock.stop();self.clock=patch('stream_history.time.time',return_value=NOW+61);self.clock.start();return out
        with patch.object(self.c,'canonical_transaction',side_effect=slow):
            with self.assertRaisesRegex(SourceUnavailable,'audit_stale'):self.history()
        self.assertEqual(self.c.cache.execute('SELECT COUNT(*) FROM stream_proofs').fetchone()[0],0)
        self.history();self.assertEqual(self.c.metrics['completed_histories'],1)
    def test_incremental_cursor_missing_refused(self):
        self.ingest();self.history();self.page=[entry(b58(b'n'*64),102)]
        with self.assertRaisesRegex(SourceUnavailable,'cursor_gap'):self.history()
    def test_prune_removes_orphan_scans(self):
        self.ingest();self.history();self.c.prune(set());self.assertEqual(self.c.cache.execute('SELECT COUNT(*) FROM stream_scan').fetchone()[0],0)
    def test_shared_canonical_body_rechecked_against_audit_time(self):
        self.c.canonical_transaction(entry(CREATE,100,NOW-600))
        with self.assertRaisesRegex(SourceUnavailable,'block_time_conflict'):
            self.c.canonical_transaction(entry(CREATE,100,NOW-599))
    def test_repair_wait_is_durable(self):
        self.c.cache.execute('INSERT INTO repair VALUES(?,?,?,?,?,NULL)',(CREATE,100,'PENDING',1,NOW+120));self.c.cache.commit()
        with self.assertRaisesRegex(SourceUnavailable,'repair_wait'):self.history()
    def test_complete_stream_history_through_all_frozen_gates(self):
        from sources import Collector
        census=f.Census();census.setUp()
        try:
            users=[f.key(i+10)for i in range(30)];self.page=[]
            _,_,ev=maps()
            for i,user in enumerate(users):
                stamp=NOW-301 if i<20 else NOW-1;sig=b58(bytes([i+1])*64);slot=103+i
                data=ev['TradeEvent']+b58decode(f.MINT)+f.u64(10)+f.u64(100)+b'\x01'+b58decode(user)+struct.pack('<q',stamp)
                tx=f.tx([f.tx_instruction('buy',dict(mint=f.MINT,user=user),f.u64(100)+f.u64(10))],[data]);logs=tx['meta']['logMessages'];logs.insert(1,'Program log: Instruction: Buy')
                self.capture.ingest(notification(dict(signature=sig,err=None,logs=logs),slot),stamp)
                self.page.append(entry(sig,slot,stamp))
            self.page.reverse();self.page.append(entry(CREATE,100,NOW-600))
            def rpc(method,params):
                if method=='getSignaturesForAddress':return copy.deepcopy(self.page)
                if method=='getTransaction':return self.origin
                if method=='getBlocks':return [100,103,104]
                if method=='getMultipleAccounts':return census.market
                if method=='getProgramAccounts':return census.census
                raise AssertionError(method)
            launch=facts(f.MINT);launch['creator']=f.USER
            with patch.object(self.c.rpc,'call',side_effect=rpc),patch.object(self.c,'social',return_value=facts()['socials']):
                out=Collector.enrich(self.c,launch,NOW)
            self.assertEqual(checks(out,NOW),dict.fromkeys(checks(out,NOW),'PASS'))
            self.assertEqual(self.c.metrics['reused_stream_transactions'],30)
            self.assertEqual(self.c.metrics['canonical_repairs'],1)
        finally:census.tearDown()
    def test_frozen_gate_input_cannot_bypass_history(self):
        launch=facts(f.MINT)
        with patch.object(self.c,'account_facts',return_value=(dict(mint=f.MINT,created_at=NOW),{})),patch.object(self.c,'history',side_effect=SourceUnavailable('missing')):
            out=self.c.enrich(launch,NOW)
        for key in('unique_buyers','buyer_growth','first_two_blocks'):self.assertEqual(checks(out,NOW)[key],'UNKNOWN')

class CaptureRepair(unittest.TestCase):
    def test_missing_event_queues_signature_not_entire_mint(self):
        with tempfile.TemporaryDirectory()as d:
            c=Capture(d);c.begin(NOW);c.ingest(dict(id=1,result=101),NOW);c.ingest(dict(id=2,result=102),NOW)
            value=trade_value(TRADE);value['logs']=[x for x in value['logs']if not x.startswith('Program data:')]
            with self.assertRaises(ValueError):c.ingest(notification(value,101),NOW)
            row=c.db.execute('SELECT signature,reason FROM transaction_gaps').fetchone();self.assertEqual(tuple(row),(TRADE,'trade_event_coverage'));c.close()
    def test_shadow_has_no_sender_import_or_delivery_switch(self):
        text=Path(__file__).resolve().parents[1].joinpath('stream_shadow.py').read_text();self.assertNotIn('UnixSender',text);self.assertNotIn('flush(',text);self.assertIn('log_only=True',text)

class Staging(unittest.TestCase):
    def test_nonroot_staging_refused(self):
        from stream_stage import stage
        with patch('stream_stage.os.geteuid',return_value=1000):
            with self.assertRaisesRegex(ValueError,'owner_root'):stage('x')
    def test_no_start_enable_or_unit_writes(self):
        root=Path(__file__).resolve().parents[1]
        text=(root/'stream_stage.py').read_text()
        self.assertNotIn("'start'",text);self.assertNotIn("'enable'",text);self.assertNotIn('daemon-reload',text);self.assertNotIn('delivery.json',text)
    def test_runner_uses_separate_cache_and_preserves_activation(self):
        from service import Runner
        from core import Journal
        with tempfile.TemporaryDirectory()as d:
            j=Journal(Path(d)/'lane.sqlite3');j.atomic(lambda:j.add('activation','activation',{'at':NOW},NOW));before=j.verify();j.db.close()
            with patch('service.shutil.disk_usage',return_value=type('Disk',(),{'free':10*1024**3})()):r=Runner(d,stream=True)
            self.assertIsInstance(r.collector,StreamCollector);self.assertEqual(next(r.j.rows('activation'))['ts'],NOW);self.assertTrue((Path(d)/'stream_rpc_cache.sqlite3').exists())
            r.j.db.close();r.collector.cache.close()
            for h in r.log.handlers[:]:h.close();r.log.removeHandler(h)
