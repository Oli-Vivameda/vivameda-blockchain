"""Offline gates for live collection isolation; no network or Telegram."""
import base64
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import test_evidence as f
import test_stream as sf
from test_lane import NOW,facts
from core import checks,canonical,Journal,Lane,RULES_SHA
from sources import SourceUnavailable,BudgetExceeded
from stream_capture import Capture
from stream_history import StreamCollector
from live_rpc import LaneRpc
from live_history import LiveCollector
from live_service import LiveRunner

class Budgets(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.c=LiveCollector(Path(self.tmp.name)/'cache',Path(self.tmp.name)/'stream','session')
        self.rpc=self.c.rpc;self.rpc.budget();self.sent=[]
        def get(*args,**kwargs):
            self.sent.append(json.loads(kwargs['body']))
            return dict(status=200,headers={},body=b'{"result":"ok"}')
        self.http=patch.object(self.rpc.http,'get',side_effect=get);self.http.start()
        self.clock=patch('sources.time.time',return_value=NOW);self.clock.start()
        self.sleep=patch('sources.time.sleep');self.sleep.start()
    def tearDown(self):
        self.sleep.stop();self.clock.stop();self.http.stop();self.c.cache.close();self.tmp.cleanup()
    def call(self,lane,n):
        self.rpc.lane=lane
        for _ in range(n):self.rpc.call('getHealth')
    def test_catchup_cannot_consume_live_or_market_quota(self):
        self.call('catchup',1)
        with self.assertRaisesRegex(BudgetExceeded,'catchup_rpc_budget'):self.call('catchup',1)
        self.call('live',7);self.call('market',4)
        self.assertEqual(len(self.sent),12);self.assertEqual(self.rpc.remaining,0)
        self.assertEqual(self.rpc.calls,dict(market=4,live=7,catchup=1))
    def test_live_cannot_borrow_unused_catchup_budget(self):
        self.call('live',7)
        with self.assertRaisesRegex(BudgetExceeded,'live_rpc_budget'):self.call('live',1)
        self.assertEqual(self.rpc.quotas['catchup'],1)
    def test_cycle_reset_does_not_reset_transport_cooldown(self):
        self.c.cache.execute("INSERT INTO config VALUES('cooldown',?)",(str(NOW+90),));self.c.cache.commit()
        self.rpc.budget();self.rpc.lane='live'
        with self.assertRaisesRegex(BudgetExceeded,'rpc_cooldown'):self.rpc.call('getHealth')
        self.assertFalse(self.sent)
    def test_retry_after_shared_across_workers(self):
        self.rpc.http.get.return_value=None
        self.rpc.http.get.side_effect=lambda *a,**kw:dict(status=429,headers={'Retry-After':'120'},body=b'{}')
        with self.assertRaisesRegex(SourceUnavailable,'rpc_throttled'):self.call('catchup',1)
        self.rpc.lane='live'
        with self.assertRaisesRegex(BudgetExceeded,'rpc_cooldown'):self.rpc.call('getHealth')
        self.assertEqual(self.rpc.http.get.call_count,1)
    def test_cannot_raise_budget(self):
        with self.assertRaises(ValueError):self.rpc.budget(13)
    def test_read_only_method_guard_retained(self):
        with self.assertRaisesRegex(SourceUnavailable,'read_only_rpc_method'):self.rpc.call('sendTransaction',[])
        self.assertFalse(self.sent)

class Sessions(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def capture(self,session):
        c=Capture(self.path/'stream',session);c.begin(NOW);c.ingest(dict(id=1,result=101),NOW);c.ingest(dict(id=2,result=102),NOW)
        return c
    def test_current_creation_discovered_without_authentication(self):
        cap=self.capture('current');cap.ingest(sf.notification(sf.creation_value()),NOW)
        c=LiveCollector(self.path/'cache',self.path/'stream','current')
        try:
            self.assertEqual(c.discoveries(NOW)[0]['mint'],f.MINT)
            self.assertEqual(c.cache.execute('SELECT COUNT(*) FROM metadata').fetchone()[0],0)
            self.assertEqual(c.cache.execute('SELECT COUNT(*) FROM stream_proofs').fetchone()[0],0)
        finally:c.cache.close();cap.close()
    def test_retained_prior_session_and_replayed_notification_not_live(self):
        cap=self.capture('old');cap.ingest(sf.notification(sf.creation_value()),NOW);cap.close()
        cap=self.capture('new');cap.ingest(sf.notification(sf.creation_value()),NOW)
        c=LiveCollector(self.path/'cache',self.path/'stream','new')
        try:self.assertEqual(c.discoveries(NOW),[])
        finally:c.cache.close();cap.close()
    def test_reconnection_retains_run_identity_without_granting_history(self):
        cap=self.capture('current');cap.ingest(sf.notification(sf.creation_value()),NOW);cap.disconnect('gap',NOW);cap.begin(NOW+1)
        c=LiveCollector(self.path/'cache',self.path/'stream','current')
        try:
            self.assertEqual(len(c.discoveries(NOW+1)),1)
            self.assertEqual(c.metrics['completed_histories'],0)
        finally:c.cache.close();cap.close()
    def test_live_and_catchup_scan_tables_separate(self):
        c=LiveCollector(self.path/'cache',self.path/'stream','current');c.live_mints={'live'}
        def pending(self,mint):
            self.cache.execute('INSERT INTO '+self.scan_table+' VALUES(?,?)',(mint,canonical(dict(cursor=None,pending=[{'signature':mint}],scan_at=NOW))))
            self.cache.commit();raise SourceUnavailable('pending')
        try:
            with patch.object(StreamCollector,'history',pending):
                for mint in ('live','old'):
                    with self.assertRaises(SourceUnavailable):c.history(mint)
            q=c.queue_summary(NOW+1)
            self.assertEqual(q['live']['pending_transactions'],1)
            self.assertEqual(q['catchup']['pending_transactions'],1)
            self.assertEqual(c.rpc.lane,'catchup')
        finally:c.cache.close()

    def test_retained_live_progress_uses_catchup_quota_after_restart(self):
        c=LiveCollector(self.path/'cache',self.path/'stream','old')
        c.cache.execute('INSERT INTO live_scan VALUES(?,?)',('mint',canonical(dict(cursor=None,pending=[{'signature':'s'}],scan_at=NOW))))
        c.cache.commit();c.cache.close()
        c=LiveCollector(self.path/'cache',self.path/'stream','new')
        try:
            self.assertEqual(c.select_lane('mint'),'catchup')
            self.assertEqual(c.rpc.lane,'catchup')
            self.assertEqual(c.scan_table,'live_scan')
            self.assertEqual(c.queue_summary(NOW)['catchup']['pending_transactions'],1)
            self.assertEqual(c.queue_summary(NOW)['live']['scans'],0)
        finally:c.cache.close()

class Assembly(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.fixture=f.Census();self.fixture.setUp()
        self.c=LiveCollector(Path(self.tmp.name)/'cache',Path(self.tmp.name)/'stream','current');self.c.live_mints={f.MINT};self.c.rpc.budget()
        self.market=copy.deepcopy(self.fixture.market);self.market['value'].append(None);self.calls=[]
        self.creation=copy.deepcopy(self.fixture.creation);self.rows=copy.deepcopy(self.fixture.rows)
        self.launch=facts(f.MINT);self.launch['creator']=f.USER
    def tearDown(self):self.c.cache.close();self.fixture.tearDown();self.tmp.cleanup()
    def rpc(self,method,params):
        self.calls.append(method);self.c.rpc.remaining-=1;self.c.rpc.quotas[self.c.rpc.lane]-=1
        if method=='getMultipleAccounts':return self.market
        if method=='getProgramAccounts':return self.fixture.census
        if method=='getBlocks':return [100,103,104]
        raise AssertionError(method)
    def run_enrich(self,history_error=None,social_error=None):
        history=patch.object(self.c,'history',side_effect=SourceUnavailable(history_error))if history_error else patch.object(self.c,'history',return_value=(self.rows,self.creation,NOW))
        social=patch.object(self.c,'social',side_effect=SourceUnavailable(social_error))if social_error else patch.object(self.c,'social',return_value=facts()['socials'])
        with history,social,patch.object(self.c.rpc,'call',side_effect=self.rpc),patch('evidence.addresses',return_value=(f.CURVE,f.key(8),f.key(9))),patch('live_history.time.time',return_value=NOW):
            return self.c.enrich(self.launch,NOW)
    def test_full_frozen_gates_with_single_account_pass(self):
        out=self.run_enrich();self.assertEqual(set(checks(out,NOW).values()),{'PASS'})
        self.assertEqual(self.calls.count('getMultipleAccounts'),1)
        self.assertEqual(self.calls.count('getProgramAccounts'),1)
        self.assertEqual(self.calls.count('getBlocks'),1)
    def test_history_failure_keeps_input_pass_fields_unknown(self):
        out=self.run_enrich(history_error='pending')
        for key in ('buyer_growth','buy_share','first_two_blocks','unique_buyers'):self.assertEqual(checks(out,NOW)[key],'UNKNOWN')
    def test_supply_gap_records_diagnostics_and_never_passes_census(self):
        self.fixture.census['value'].pop()
        out=self.run_enrich()
        self.assertEqual(out['collection_issues']['accounts'],'holder_supply_not_reconciled')
        self.assertNotEqual(out['provenance']['holder_reconciliation']['difference'],0)
        self.assertEqual(checks(out,NOW)['top_holder'],'UNKNOWN')
    def test_curve_supply_failure_specific_and_strict(self):
        self.creation['initial_supply']=999
        out=self.run_enrich()
        self.assertEqual(out['collection_issues']['curve'],'curve_supply_mismatch')
        self.assertEqual(checks(out,NOW)['curve'],'UNKNOWN')
    def test_social_failure_does_not_hide_other_evidence(self):
        out=self.run_enrich(social_error='metadata_unavailable')
        self.assertEqual(checks(out,NOW)['social'],'UNKNOWN')
        self.assertEqual(checks(out,NOW)['curve'],'PASS')
        self.assertEqual(checks(out,NOW)['developer'],'PASS')
    def test_creator_conflict_remains_blocked(self):
        self.creation['creator']=f.key(99)
        out=self.run_enrich()
        self.assertEqual(checks(out,NOW)['developer'],'UNKNOWN')
        self.assertIn('creation',out['collection_issues'])
    def test_exhausted_live_budget_does_not_consume_catchup_or_refresh_scheduler_age(self):
        self.c.rpc.quotas['live']=0
        out=self.c.enrich(self.launch,NOW)
        self.assertFalse(out['collection_attempted']);self.assertEqual(self.c.rpc.quotas['catchup'],1)
        self.assertEqual(checks(out,NOW)['buyer_growth'],'UNKNOWN')

class RunnerIsolation(unittest.TestCase):
    def test_existing_journal_clock_and_old_cache_bytes_unchanged(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d);j=Journal(p/'lane.sqlite3');Lane(j)
            j.atomic(lambda:j.add('activation','activation',{'at':NOW},NOW));before=j.verify();j.db.close()
            for name in ('rpc_cache.sqlite3','stream_rpc_cache.sqlite3'):(p/name).write_bytes(b'untouched prior cache')
            r=LiveRunner(p,'session')
            try:
                self.assertEqual(r.j.verify(),before)
                for name in ('rpc_cache.sqlite3','stream_rpc_cache.sqlite3'):self.assertEqual((p/name).read_bytes(),b'untouched prior cache')
            finally:
                r.j.db.close();r.collector.cache.close()
                for h in r.log.handlers[:]:h.close();r.log.removeHandler(h)
    def runner(self,p):
        return LiveRunner(p,'session')
    def test_union_discovery_deduplicates_without_turning_hint_into_pass(self):
        with tempfile.TemporaryDirectory()as d:
            r=self.runner(d)
            try:
                frame={'launches':[dict(mint='same',created_at=NOW-10)]}
                live=[dict(mint='same',created_at=NOW-10),dict(mint='stream',created_at=NOW-5)]
                with patch.object(r.collector,'discoveries',return_value=live):
                    result=r.prepare_launches(frame,NOW)
                self.assertEqual(len(result),2);self.assertEqual(r.collector.live_mints,{'same','stream'})
                self.assertTrue(all(checks(x,NOW)['buyer_growth']=='UNKNOWN'for x in result))
            finally:
                r.j.db.close();r.collector.cache.close()
                for h in r.log.handlers[:]:h.close();r.log.removeHandler(h)
    def test_shadow_cannot_enable_delivery(self):
        with tempfile.TemporaryDirectory()as d:
            r=self.runner(d)
            try:
                with self.assertRaisesRegex(ValueError,'shadow_only'):r.poll({},log_only=False)
                with self.assertRaisesRegex(ValueError,'shadow_only'):r.poll({},None,False,False)
            finally:
                r.j.db.close();r.collector.cache.close()
                for h in r.log.handlers[:]:h.close();r.log.removeHandler(h)
    def test_market_batch_reserves_catchup_capacity(self):
        with tempfile.TemporaryDirectory()as d:
            r=self.runner(d)
            try:
                r.collector.live_mints={str(i)for i in range(100)}
                watched={str(i):dict(mint=str(i),created_at=NOW-10)for i in range(110)}
                batch=r.market_batch(watched,{},NOW,lambda x:x['mint'])
                self.assertEqual(len(batch),30)
                self.assertEqual(sum(x['mint']not in r.collector.live_mints for x in batch),6)
            finally:
                r.j.db.close();r.collector.cache.close()
                for h in r.log.handlers[:]:h.close();r.log.removeHandler(h)
    def test_live_shadow_has_no_telegram_sender_or_delivery_switch(self):
        text=Path(__file__).resolve().parents[1].joinpath('live_shadow.py').read_text()
        self.assertNotIn('UnixSender',text);self.assertNotIn('flush(',text);self.assertIn('log_only=True',text)

if __name__=='__main__':unittest.main()
