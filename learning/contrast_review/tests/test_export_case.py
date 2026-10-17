"""Synthetic SQLite fixtures only. No production database or network access."""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import export_case as e
A='A'*43+'1'; B='B'*43+'1'

class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'fixture.sqlite';self.db=sqlite3.connect(self.path)
        self.addCleanup(self.db.close)
        self.db.executescript('''
          CREATE TABLE pl_predictions(mint TEXT,body TEXT,model_probability REAL);
          CREATE TABLE pl_results(body TEXT);
          CREATE TABLE launches(mint TEXT,symbol TEXT,name TEXT,created_ts INTEGER,first_seen INTEGER,pinned_pair TEXT);
          CREATE TABLE v2_cases(mint TEXT,id TEXT,decision_ts INTEGER,source TEXT,score INTEGER,level INTEGER,regime TEXT,entry_price REAL,entry_mc REAL,entry_liq REAL,features TEXT);
          CREATE TABLE snapshots(mint TEXT,ts INTEGER,pair TEXT,price REAL,mc REAL,liq REAL,vol_m5 REAL,vol_h1 REAL,buys_m5 INTEGER,sells_m5 INTEGER,buys_h1 INTEGER,sells_h1 INTEGER,pc_m5 REAL,pc_h1 REAL);
          CREATE TABLE prealert_reviews(mint TEXT,level INTEGER,checked_at INTEGER,policy TEXT,verdict TEXT,review TEXT);
        ''');self.db.commit()
    def case(self,mint=A,ts=1000,source='ALERT',ident='first'):
        self.db.execute('INSERT INTO v2_cases VALUES(?,?,?,?,?,?,?,?,?,?,?)',(mint,ident,ts,source,9,1,'RECLAIM',.0001,100000,30000,'{"probability":0.99}'))
        self.db.execute('INSERT INTO launches VALUES(?,?,?,?,?,?)',(mint,'FIX','Fixture',0,0,'fixture_pair'));self.db.commit()
    def snap(self,ts,mc=100000):
        self.db.execute('INSERT INTO snapshots VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(A,ts,'fixture_pair',.0001,mc,30000,1000,6000,6,4,60,40,10,20));self.db.commit()
    def run_export(self):return e.audit(self.path,[A,B],now=5000)
    def review(self,checked=999,observed=999,mint=A):
        body={'mint':mint,'chain':'solana','pair':'fixture_pair','checks':{k:{'status':'PASS','observed_at':observed,'evidence_refs':['fixture'], 'details':{'pct':2.0,'model_probability':.9}} for k in e.CHECKS}}
        self.db.execute('INSERT INTO prealert_reviews VALUES(?,?,?,?,?,?)',(A,1,checked,'fixture','PASS',json.dumps(body)));self.db.commit()
    def test_frozen_membership_stops_before_case_data(self):
        self.db.execute('INSERT INTO pl_predictions VALUES(?,?,?)',(A,'DO_NOT_READ',.99));self.db.commit()
        self.case();result=self.run_export()['cases'][0]
        self.assertEqual(result,{'mint':A,'status':'EXCLUDED_FROZEN_NO_CASE_DATA_READ'})
    def test_absent_membership_table_fails_closed(self):
        self.db.execute('DROP TABLE pl_predictions');self.db.commit()
        with self.assertRaises(ValueError):self.run_export()
    def test_authorizer_blocks_labels_probabilities_features_and_writes(self):
        self.db.set_authorizer(e.authorizer)
        for query in ('SELECT body FROM pl_predictions','SELECT model_probability FROM pl_predictions','SELECT body FROM pl_results','SELECT features FROM v2_cases',"INSERT INTO pl_results VALUES('x')"):
            with self.assertRaises(sqlite3.DatabaseError):self.db.execute(query)
    def test_database_bytes_unchanged(self):
        self.case();before=hashlib.sha256(self.path.read_bytes()).hexdigest();self.run_export()
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),before)
    def test_earliest_alert_ignores_shadow_and_later_alert(self):
        self.case(ts=900,source='SHADOW',ident='shadow');self.case(ts=1200,ident='later');self.case(ts=1000,ident='first')
        self.assertEqual(self.run_export()['cases'][0]['first_retained_alert']['id'],'first')
    def test_postalert_review_cannot_be_backfilled(self):
        self.case();self.review(checked=1001)
        self.assertEqual(self.run_export()['cases'][0]['screening_asof_alert']['status'],'NO_RETAINED_ASOF_REVIEW')
    def test_fresh_identity_bound_checks_pass_and_strip_probabilities(self):
        self.case();self.review();result=self.run_export()['cases'][0]['screening_asof_alert']
        self.assertTrue(result['identity_bound']);self.assertEqual(result['checks']['token_controls']['status'],'PASS')
        self.assertNotIn('probability',json.dumps(result))
    def test_future_stale_or_wrong_identity_is_unknown(self):
        self.case()
        for at,mint in ((1001,A),(600,A),(999,B)):
            self.db.execute('DELETE FROM prealert_reviews');self.review(observed=at,mint=mint)
            result=self.run_export()['cases'][0]['screening_asof_alert']
            self.assertEqual(result['checks']['token_controls']['status'],'UNKNOWN')
    def test_no_interpolation_or_predeadline_endpoint_fill(self):
        self.case();self.snap(1000);self.snap(1299,200000);self.snap(1481,220000)
        result=self.run_export()['cases'][0]
        self.assertEqual(result['timed_endpoints_minutes']['5']['status'],'missing')
        self.assertAlmostEqual(result['asof_snapshot_features']['buy_share_m5'],.6)
    def test_endpoint_at_deadline_and_180_second_boundary(self):
        self.case();self.snap(1000);self.snap(1480,200000)
        result=self.run_export()['cases'][0]['timed_endpoints_minutes']['5']
        self.assertEqual(result['multiple'],2);self.assertEqual(result['lateness'],180);self.assertFalse(result['coverage_ok'])
    def test_missing_asof_snapshot_stays_missing(self):
        self.case();self.snap(1001)
        self.assertIsNone(self.run_export()['cases'][0]['asof_snapshot_features'])
    def test_export_bound_fails_instead_of_truncating_outcomes(self):
        self.case()
        self.db.executemany('INSERT INTO snapshots VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',[(A,ts,'fixture_pair',1,1,1,1,1,1,1,1,1,1,1) for ts in range(1000,3049)]);self.db.commit()
        with self.assertRaises(ValueError):self.run_export()
    def test_exact_two_mints_required(self):
        for mints in ([A],[A,A],[A,"';drop table"]):
            with self.assertRaises(ValueError):e.audit(self.path,mints)
    def test_bad_hash_refuses_before_production_open(self):
        result=subprocess.run([sys.executable,str(Path(e.__file__)),'--expected-sha256','0'*64,'--mint',A,'--mint',B],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0);self.assertIn('hash_mismatch_no_database_opened',result.stderr)

if __name__=='__main__':unittest.main()
