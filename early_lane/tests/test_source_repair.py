import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Journal,Lane
from upgrade import ensure_stopped,journal_state,preflight
from sources import Collector,SourceUnavailable
from test_lane import NOW,facts
from service import Runner
from pricing import Marks

class Repair(unittest.TestCase):
    def test_upgrade_preflight_blocks_without_live_prices(self):
        rpc=types.SimpleNamespace(budget=lambda n:None)
        with patch.object(Marks,'read',return_value={}):
            with self.assertRaises(ValueError):preflight({'launches':[facts()]},rpc)
    def test_upgrade_preflight_requires_observed_marks(self):
        rpc=types.SimpleNamespace(budget=lambda n:None)
        with patch.object(Marks,'read',return_value={'A':{'mc':'10000'}}):
            result=preflight({'launches':[facts()]},rpc);self.assertEqual(result['authenticated_market_marks'],1)
    def test_upgrade_refuses_running_units(self):
        def run(*a,**kw):return types.SimpleNamespace(stdout='active\n')
        with self.assertRaises(ValueError):ensure_stopped(run)
    def test_upgrade_allows_inactive_units(self):
        ensure_stopped(lambda *a,**kw:types.SimpleNamespace(stdout='inactive\n'))
    def test_upgrade_does_not_reset_journal(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'j';j=Journal(path);lane=Lane(j);before=list(j.rows());state=journal_state(path);self.assertIsNone(state['activation']);self.assertEqual(list(j.rows()),before)
            lane.consider([],NOW,live=True)
            with self.assertRaises(ValueError):journal_state(path)
            j.db.close()
    def test_upgrade_detects_tampered_journal(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'j';j=Journal(p);Lane(j);j.db.execute('DROP TRIGGER no_update');j.db.execute("UPDATE events SET hash='wrong'")
            with self.assertRaises(ValueError):journal_state(p)
            j.db.close()
    def test_json_rpc_rate_limit_has_persisted_cooldown(self):
        class H:
            def get(self,*a,**k):return dict(status=200,headers={'Retry-After':'180'},body=json.dumps({'error':{'code':429,'message':'Too many requests'}}).encode())
        with tempfile.TemporaryDirectory() as d:
            c=Collector(Path(d)/'cache',H());c.rpc.budget(1)
            with self.assertRaises(SourceUnavailable):c.rpc.call('getHealth')
            row=c.cache.execute("SELECT body FROM config WHERE key='cooldown'").fetchone();self.assertIsNotNone(row);c.cache.close()
    def test_no_prices_does_not_activate_observational_clock(self):
        from core import RULES_SHA
        with tempfile.TemporaryDirectory() as d:
            r=Runner(d);frame=dict(schema='early-lane-feed-v1',rules_sha256=RULES_SHA,exported_at=NOW,source_live=True,launches=[],observations=[])
            with patch('service.time.time',return_value=NOW),patch.object(Marks,'read',return_value={}):
                result=r.poll(frame,NOW);self.assertEqual(result['fresh_market_marks'],0);self.assertIsNone(r.lane.activation())
            r.j.db.close();r.collector.cache.close()

if __name__=='__main__':unittest.main()
