"""Regressions for local-evidence draining and bounded collection scheduling."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import test_stream_history as hf
from test_stream_history import entry,TRADE,CREATE
from test_lane import NOW,facts
from pump import b58
from sources import SourceUnavailable
from service import Runner
from core import RULES_SHA,canonical

class Backlog(unittest.TestCase):
    def setUp(self):
        self.h=hf.History();self.h.setUp()
    def tearDown(self):self.h.tearDown()
    def test_cached_later_trade_and_failed_entries_not_blocked_by_missing_head(self):
        h=self.h;h.ingest();missing=entry(CREATE,100,NOW-600)
        failed=entry(b58(b'f'*64),102,error={'InstructionError':[0,'x']})
        state={'pending':[missing,entry(TRADE,101),failed]}
        h.c.compact_stream_pending('unused',{'pending':[]})
        import test_evidence as f
        h.c.compact_stream_pending(f.MINT,state)
        self.assertEqual(state['pending'],[missing]);self.assertEqual(h.calls,[])
        self.assertEqual(h.c.metrics['reused_stream_transactions'],1)
        self.assertEqual(h.c.metrics['failed_signatures_skipped'],1)
    def test_durable_replay_does_not_duplicate_local_rows(self):
        h=self.h;h.ingest()
        import test_evidence as f
        for _ in range(2):h.c.compact_stream_pending(f.MINT,{'pending':[entry(TRADE,101)]})
        self.assertEqual(h.c.cache.execute('SELECT COUNT(*) FROM tx').fetchone()[0],1)
        self.assertEqual(h.c.metrics['reused_stream_transactions'],1)
    def test_conflict_remains_pending_for_canonical_repair(self):
        h=self.h;h.ingest()
        h.capture.db.execute('UPDATE captured_transactions SET conflict=1');h.capture.db.commit()
        import test_evidence as f
        state={'pending':[entry(TRADE,101)]};h.c.compact_stream_pending(f.MINT,state)
        self.assertEqual(len(state['pending']),1);self.assertEqual(h.calls,[])
    def test_slot_mismatch_remains_pending(self):
        h=self.h;h.ingest()
        import test_evidence as f
        state={'pending':[entry(TRADE,102)]};h.c.compact_stream_pending(f.MINT,state)
        self.assertEqual(len(state['pending']),1)
    def test_missing_history_cannot_gain_proof_from_compaction(self):
        h=self.h;h.ingest()
        def limited(method,params):
            if method=='getSignaturesForAddress':return copy.deepcopy(h.page)
            raise SourceUnavailable('rpc_cycle_budget')
        with patch.object(h.c.rpc,'call',side_effect=limited):
            with self.assertRaisesRegex(SourceUnavailable,'rpc_cycle_budget'):h.history()
        self.assertEqual(h.c.cache.execute('SELECT COUNT(*) FROM stream_proofs').fetchone()[0],0)
        state=json.loads(h.c.cache.execute('SELECT body FROM stream_scan').fetchone()[0])
        self.assertEqual(state['pending'],[h.page[-1]])
    def test_scheduling_hint_does_not_authenticate_creation(self):
        h=self.h
        h.capture.db.execute('INSERT INTO creations VALUES(?,?,?,?)',('hint',NOW-1,1,'{}'))
        h.capture.db.commit()
        self.assertEqual(h.c.captured_births(NOW),{'hint'})
        self.assertEqual(h.c.cache.execute('SELECT COUNT(*) FROM metadata').fetchone()[0],0)

class Scheduling(unittest.TestCase):
    def test_birth_priority_reserves_every_fifth_poll_for_fair_work_without_dropping_launches(self):
        with tempfile.TemporaryDirectory()as d:
            with patch('service.shutil.disk_usage',return_value=type('Disk',(),{'free':10*1024**3})()):
                r=Runner(d,stream=True)
            try:
                seen=[]
                def enrich(launch,now):
                    seen.append(launch['mint']);r.collector.rpc.remaining=0
                    return dict(launch)
                frame={'schema':'early-lane-feed-v1','rules_sha256':RULES_SHA,'exported_at':NOW,
                    'source_live':True,'launches':[dict(mint='old',created_at=NOW-1000),dict(mint='birth',created_at=NOW-60)]}
                def marks(batch):
                    return {x['mint']:dict(mc='12000',market_at=NOW,market_expires_at=NOW+60)for x in batch}
                with patch('service.time.time',return_value=NOW),patch.object(r.collector,'captured_births',return_value={'birth'}),patch.object(r.collector,'enrich',side_effect=enrich),patch('service.Marks.read',side_effect=marks):
                    results=[r.poll(copy.deepcopy(frame),now=NOW)for _ in range(5)]
                self.assertEqual(seen,['birth']*4+['old'])
                self.assertTrue(all(x['launches_in_window']==2 for x in results))
                self.assertTrue(all(x['selected']==0 for x in results))
                self.assertEqual(results[-1]['scheduling'],'fair_round_robin')
                self.assertEqual(len(list(r.j.rows('launch'))),2)
            finally:
                r.j.db.close();r.collector.cache.close()
                for h in r.log.handlers[:]:h.close();r.log.removeHandler(h)
