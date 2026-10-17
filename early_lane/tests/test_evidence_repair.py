import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import test_evidence as fixture
from test_evidence import MINT, USER, key, tx, account
from test_lane import NOW, facts
from core import checks, canonical, Journal, Lane
from pump import decode_tx, EvidenceError
from sources import Collector, SourceUnavailable
from evidence import EvidenceCollector
from alerts import message

class Version(unittest.TestCase):
    def test_v1_successful_buy(self):
        value=fixture.Parser().trade();value['version']=1
        self.assertEqual(len(decode_tx(value,MINT,'s')['trades']),1)
    def test_unsupported_version_is_unknown(self):
        for v in (2,True,'1'):
            value=tx([]);value['version']=v
            with self.assertRaises(EvidenceError):decode_tx(value,MINT,'s')
    def test_rpc_fetch_supports_v1_and_resumes_pending(self):
        with tempfile.TemporaryDirectory()as d:
            c=Collector(Path(d)/'rpc');calls=[]
            c.save_scan(MINT,dict(cursor=None,before=None,head='s',pending=[dict(signature='s',slot=100)],paging_done=True,scan_at=NOW))
            def rpc(method,params):
                calls.append((method,params));return fixture.Parser().trade()
            with patch.object(c.rpc,'call',side_effect=rpc):
                with self.assertRaisesRegex(SourceUnavailable,'creation_provenance_missing'):c.history(MINT)
            self.assertEqual(calls[0][1][1]['maxSupportedTransactionVersion'],1)
            self.assertEqual(c.cache.execute('SELECT COUNT(*) FROM tx').fetchone()[0],1);c.cache.close()
    def test_large_signature_page_does_not_terminate_early(self):
        with tempfile.TemporaryDirectory()as d:
            c=Collector(Path(d)/'rpc');seen=[]
            def rpc(method,params):
                seen.append(params)
                if len(seen)==1:return [dict(signature=str(i),slot=i)for i in range(1000)]
                raise SourceUnavailable('next_page')
            with patch.object(c.rpc,'call',side_effect=rpc):
                with self.assertRaisesRegex(SourceUnavailable,'next_page'):c.history(MINT)
            self.assertEqual(seen[0][1]['limit'],1000);self.assertEqual(seen[1][1]['before'],'999');c.cache.close()

class Independent(unittest.TestCase):
    def setUp(self):
        self.base=fixture.Census();self.base.setUp();self.d=tempfile.TemporaryDirectory();self.c=EvidenceCollector(Path(self.d.name)/'rpc');self.c.rpc.budget(12)
        self.market=copy.deepcopy(self.base.market);self.market['value'].append(None)
        self.launch=facts(MINT);self.launch['creator']=USER
    def tearDown(self):self.c.cache.close();self.d.cleanup();self.base.tearDown()
    def rpc(self,method,params):
        self.c.rpc.remaining-=1
        if method=='getMultipleAccounts':return self.market
        if method=='getProgramAccounts':return self.base.census
        raise AssertionError(method)
    def run_enrich(self):
        with patch('evidence.addresses',return_value=(self.base.creation['curve'],key(8),key(9))),patch.object(self.c.rpc,'call',side_effect=self.rpc),patch.object(Collector,'history',side_effect=SourceUnavailable('history_backlog')),patch('evidence.time.time',return_value=NOW):return self.c.enrich(self.launch,NOW)
    def test_accounts_survive_history_backlog_without_passing_history(self):
        f=self.run_enrich();out=checks(f,NOW)
        self.assertEqual(out['authorities'],'PASS');self.assertEqual(out['top_holder'],'PASS')
        for k in ('buyer_growth','buy_share','first_two_blocks','unique_buyers'):self.assertEqual(out[k],'UNKNOWN')
        self.assertIn('history_backlog',f['collection_issues']['history'])
    def test_supply_gap_cannot_pass_holder_checks(self):
        self.base.census['value'].pop();f=self.run_enrich()
        self.assertEqual(checks(f,NOW)['top_holder'],'UNKNOWN');self.assertIn('holder_supply_not_reconciled',f['collection_issues']['accounts'])
    def test_stale_census_context_is_refused(self):
        self.base.census['context']['slot']=199
        self.assertEqual(checks(self.run_enrich(),NOW)['top_holder'],'UNKNOWN')
    def test_input_pass_fields_never_survive_failed_refresh(self):
        self.market['value'][0]=None;out=checks(self.run_enrich(),NOW)
        self.assertEqual(out['authorities'],'UNKNOWN');self.assertEqual(out['top_holder'],'UNKNOWN')
    def test_cached_creation_can_resolve_social_and_creator_while_history_pending(self):
        self.c.cache.execute('INSERT INTO metadata VALUES(?,?)',(MINT,canonical(self.base.creation)))
        with patch.object(self.c,'social',return_value=facts()['socials']):f=self.run_enrich()
        out=checks(f,NOW)
        for k in ('curve','developer','social'):self.assertEqual(out[k],'PASS')
        self.assertEqual(out['first_two_blocks'],'UNKNOWN')
    def test_creator_conflict_blocks_creator_and_social(self):
        self.c.cache.execute('INSERT INTO metadata VALUES(?,?)',(MINT,canonical(self.base.creation)));self.launch['creator']=key(99)
        with patch.object(self.c,'social')as social:f=self.run_enrich()
        social.assert_not_called();self.assertEqual(checks(f,NOW)['developer'],'UNKNOWN')
    def test_cached_accounts_expire_and_do_not_inherit_old_pass(self):
        self.run_enrich();self.market['value'][0]=None
        with patch('evidence.time.time',return_value=NOW+61),patch('evidence.addresses',return_value=(self.base.creation['curve'],key(8),key(9))),patch.object(self.c.rpc,'call',side_effect=self.rpc):f,issues=self.c.account_facts(self.launch)
        self.assertEqual(checks(f,NOW+61)['authorities'],'UNKNOWN');self.assertIn('accounts',issues)
    def test_alert_includes_dexscreener(self):
        self.assertIn('https://dexscreener.com/solana/'+MINT,message(dict(mint=MINT,at=NOW,mc='10000',facts=self.launch)))

class UpgradeAndReadiness(unittest.TestCase):
    def test_real_two_hour_pricing_receipt_cannot_pass_screening(self):
        from service import rollout_gate
        gate=rollout_gate(7201.42,898,889,19.48,31.79,0)
        self.assertTrue(gate['transport_rollout_pass']);self.assertFalse(gate['live_rollout_pass'])
    def test_complete_evidence_and_transport_both_required(self):
        from service import rollout_gate
        self.assertTrue(rollout_gate(7201,10,10,30,30,1)['screening_rollout_pass'])
        self.assertFalse(rollout_gate(100,10,10,30,30,1)['screening_rollout_pass'])
        self.assertFalse(rollout_gate(7201,10,10,130,30,1)['screening_rollout_pass'])
    def test_upgrade_preserves_activated_journal_and_cohort(self):
        from evidence_upgrade import journal_state
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'journal';j=Journal(p);lane=Lane(j);lane.consider([facts()],NOW,live=True)
            before=list(j.rows());state=journal_state(p)
            self.assertEqual(state['activation'],NOW);self.assertEqual(state['cohorts'],1);self.assertEqual(before,list(j.rows()));j.db.close()
    def test_upgrade_checks_transient_rpc_shadow_is_stopped(self):
        from evidence_upgrade import ensure_stopped
        from types import SimpleNamespace
        def run(args,**kw):return SimpleNamespace(stdout='active' if args[2].endswith('-rollout-rpc2.service')else'inactive')
        with self.assertRaisesRegex(ValueError,'rollout-rpc2'):ensure_stopped(run)

class SharedDestination(unittest.TestCase):
    def config(self,**kw):
        import stat
        from types import SimpleNamespace
        from transport import configuration
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'config';p.write_text(json.dumps(dict(channel='123456789',reuse_scanner_channel=True,new_channel_confirmed=True,confirmed_at=NOW,socket='/run/early.sock',**kw)))
            with patch('transport.Path.lstat',return_value=SimpleNamespace(st_mode=stat.S_IFREG|0o640,st_uid=0)):return configuration(p)
    def test_explicit_shared_private_destination_supported_without_sending(self):self.assertTrue(self.config()['new_channel_confirmed'])
    def test_private_destination_without_shared_opt_in_rejected(self):
        from transport import configuration
        import stat
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'config';p.write_text(json.dumps(dict(channel='123456789',new_channel_confirmed=True,confirmed_at=NOW,socket='/run/early.sock')))
            with patch('transport.Path.lstat',return_value=SimpleNamespace(st_mode=stat.S_IFREG|0o640,st_uid=0)):
                with self.assertRaises(ValueError):configuration(p)
    def test_one_shot_test_config_does_not_authorize_delivery(self):
        from transport import configuration
        import stat
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'config';p.write_text(json.dumps(dict(channel='123456789',reuse_scanner_channel=True,new_channel_confirmed=False,confirmed_at=None,socket='/run/early.sock')))
            with patch('transport.Path.lstat',return_value=SimpleNamespace(st_mode=stat.S_IFREG|0o640,st_uid=0)):self.assertFalse(configuration(p)['new_channel_confirmed'])

if __name__=='__main__':unittest.main()
