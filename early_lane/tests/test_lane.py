import copy
import datetime as dt
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import *
from outcomes import *
from alerts import message,flush,RateLimited
from exporter import readonly,collect,refresh,atomic
from sources import Collector,PublicHTTPS,SourceUnavailable,Rpc,retry_seconds
from pump import decode_tx,EvidenceError,PUMP

NOW=1800000000

def facts(mint='A',now=NOW):
    return dict(mint=mint,symbol='DEMO',created_at=now-600,mc='10000',market_at=now,
        curve_at=now,curve_authenticated=True,on_curve=True,graduated_at=None,curve_progress_pct=35,
        census_complete=True,creator_verified=True,dev_pct=2,first_blocks_complete=True,dev_first_pct=10,
        top_holder_pct=7,holders_at=now,history_complete=True,history_at=now,unique_buyers=30,
        unique_5m_ago=20,buys_5m=6,sells_5m=4,authorities_authenticated=True,authority_at=now,
        mint_revoked=True,freeze_revoked=True,socials=[dict(verified=True,checked_at=now,url='https://example.org')])

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name);self.j=Journal(self.path/'j.sqlite');self.lane=Lane(self.j)
    def tearDown(self):self.j.db.close();self.tmp.cleanup()
    def select(self,mint='A',now=NOW):return self.lane.consider([facts(mint,now)],now)[0]
    def obs(self,t,mc,liq=None,received=None):return record(self.lane,'A',NOW+t,mc,liq,NOW+t if received is None else NOW+received,str(t)+':'+str(mc),{'fixture':True})

class Predicates(Base):
    def test_all_pass(self):self.assertEqual(set(checks(facts(),NOW).values()),{'PASS'})
    def test_boundaries(self):
        for key,val,gate,expected in [('mc',8000,'market_cap','PASS'),('mc',25000,'market_cap','PASS'),('mc',7999,'market_cap','FAIL'),('mc',25001,'market_cap','FAIL'),('dev_pct',5,'developer','FAIL'),('dev_first_pct',15,'first_two_blocks','FAIL'),('top_holder_pct',8,'top_holder','PASS'),('top_holder_pct',8.01,'top_holder','FAIL'),('unique_buyers',24,'unique_buyers','FAIL'),('unique_5m_ago',21,'buyer_growth','FAIL'),('unique_5m_ago',0,'buyer_growth','UNKNOWN'),('sells_5m',5,'buy_share','FAIL'),('mint_revoked',False,'authorities','FAIL')]:
            with self.subTest(key=key,val=val):
                f=facts();f[key]=val;self.assertEqual(checks(f,NOW)[gate],expected)
    def test_missing_all_fields(self):
        for key in facts():
            f=facts();del f[key]
            c=checks(f,NOW)
            if key not in ('symbol','mint','graduated_at'):self.assertNotEqual(set(c.values()),{'PASS'},key)
    def test_nonfinite(self):
        for val in ['NaN','Infinity','-Infinity','not a number']:
            f=facts();f['mc']=val;self.assertEqual(checks(f,NOW)['market_cap'],'UNKNOWN')
    def test_stale_and_future(self):
        for key in ('market_at','holders_at','curve_at','history_at','authority_at'):
            for delta in (-61,1):
                f=facts();f[key]=NOW+delta;self.assertNotEqual(set(checks(f,NOW).values()),{'PASS'})
    def test_graduated_window(self):
        f=facts();f.update(on_curve=False,graduated_at=NOW-300);self.assertEqual(checks(f,NOW)['curve'],'PASS')
        f['graduated_at']-=1;self.assertEqual(checks(f,NOW)['curve'],'FAIL')
    def test_growth_needs_five_minutes(self):
        f=facts();f['created_at']=NOW-299;self.assertEqual(checks(f,NOW)['buyer_growth'],'FAIL')
    def test_missing_census(self):
        f=facts();f['census_complete']=False
        for key in ('developer','first_two_blocks','top_holder'):self.assertEqual(checks(f,NOW)[key],'UNKNOWN')
    def test_ranking_cap_and_separate_cohort(self):
        fs=[facts(str(i)) for i in range(8)]
        for i,f in enumerate(fs):f['unique_buyers']=30+i
        out=self.lane.consider(fs,NOW);self.assertEqual([c['mint'] for c in out[:6]],['7','6','5','4','3','2'])
        self.assertEqual([c['selection'] for c in out].count('CAP_SUPPRESSED'),2)
    def test_one_ever_and_no_promote(self):
        self.lane.consider([facts(str(i)) for i in range(7)],NOW)
        self.assertEqual(self.lane.consider([facts(str(i),NOW+4000) for i in range(7)],NOW+4000),[])
    def test_rolling_hour_boundary(self):
        self.lane.consider([facts(str(i)) for i in range(6)],NOW)
        self.assertEqual(self.lane.consider([facts('x',NOW+3599)],NOW+3599)[0]['selection'],'CAP_SUPPRESSED')
        self.assertEqual(self.lane.consider([facts('y',NOW+3600)],NOW+3600)[0]['selection'],'ALERT')
    def test_unknown_cannot_alert(self):
        f=facts();f['mc']=None;self.assertEqual(self.lane.consider([f],NOW),[])
    def test_activation_only_live(self):
        self.lane.consider([],NOW);self.assertIsNone(self.lane.activation())
        self.lane.consider([],NOW+1,live=True);self.assertEqual(self.lane.activation(),NOW+1)
    def test_restart_one_ever(self):
        self.select();second=Lane(Journal(self.path/'j.sqlite'));self.assertEqual(second.consider([facts()],NOW),[]);second.j.db.close()
    def test_update_delete_forbidden(self):
        for sql in ['UPDATE events SET body=body','DELETE FROM events']:
            with self.assertRaises(sqlite3.IntegrityError):self.j.db.execute(sql)
    def test_hash_chain_tamper(self):
        self.select();self.j.db.execute('DROP TRIGGER no_update');self.j.db.execute("UPDATE events SET body='{}' WHERE seq=2")
        with self.assertRaises(ValueError):self.j.verify()
    def test_atomic_rollback(self):
        def op():self.j.add('test','x',{});raise RuntimeError()
        with self.assertRaises(RuntimeError):self.j.atomic(op)
        self.assertEqual(list(self.j.rows('test')),[])

class Outcomes(Base):
    def test_nearest_tie_earlier(self):
        self.select();self.obs(290,20000);self.obs(310,30000);finalize(self.lane,NOW+420)
        c=next(self.j.rows('checkpoint'))['body'];self.assertEqual(c['observation']['observed_at'],NOW+290)
    def test_exact_tolerance(self):
        self.select();self.obs(420,20000);finalize(self.lane,NOW+420);self.assertEqual(next(self.j.rows('checkpoint'))['body']['status'],'OBSERVED')
    def test_outside_tolerance_missing(self):
        self.select();self.obs(421,20000);finalize(self.lane,NOW+421);self.assertEqual(next(self.j.rows('checkpoint'))['body']['status'],'MISSING')
    def test_late_backfill_not_used(self):
        self.select();self.obs(300,20000,received=421);finalize(self.lane,NOW+421);self.assertEqual(next(self.j.rows('checkpoint'))['body']['status'],'MISSING')
    def test_missing_immutable(self):
        self.select();finalize(self.lane,NOW+420);self.obs(300,20000,received=500);finalize(self.lane,NOW+500)
        self.assertEqual(len(list(self.j.rows('checkpoint'))),1);self.assertEqual(next(self.j.rows('checkpoint'))['body']['status'],'MISSING')
    def test_no_interpolation(self):
        self.select();self.obs(1,10000);self.obs(600,50000);finalize(self.lane,NOW+600);self.assertEqual(next(self.j.rows('checkpoint'))['body']['status'],'MISSING')
    def test_observed_peak_and_crossings(self):
        c=self.select();self.obs(100,30000);self.obs(200,100000);self.obs(400,50000);finalize(self.lane,NOW+500)
        r=individual(self.lane,c,NOW+500);self.assertEqual(r['time_to_peak_s'],200);self.assertEqual(r['first_observed_crossings']['2'],NOW+100);self.assertEqual(r['first_observed_crossings']['10'],NOW+200)
    def test_dead_strict_boundary(self):
        c=self.select();self.obs(100,3000);self.assertFalse(individual(self.lane,c,NOW+100)['dead']);self.obs(101,2999);self.assertTrue(individual(self.lane,c,NOW+101)['dead'])
    def test_missing_liquidity_not_dead(self):
        c=self.select();self.obs(10,10000);self.assertFalse(individual(self.lane,c,NOW+10)['dead'])
    def test_authenticated_zero_liquidity_dead(self):
        c=self.select();self.obs(10,10000,0);self.assertTrue(individual(self.lane,c,NOW+10)['dead'])
    def test_out_of_window_rejected(self):
        self.select();self.assertFalse(self.obs(-1,1));self.assertFalse(self.obs(86521,1))
    def test_24h_checkpoint_accepts_after_target_without_extending_peak(self):
        c=self.select();self.obs(86460,100000);finalize(self.lane,NOW+86520);r=individual(self.lane,c,NOW+86520)
        self.assertEqual(r['checkpoints'][-1]['status'],'OBSERVED');self.assertEqual(r['observed_peak_multiple'],'1');self.assertIsNone(r['first_observed_crossings']['10'])
    def test_duplicate_observation(self):
        self.select();self.assertTrue(self.obs(10,10000));self.assertFalse(self.obs(10,10000))
    def test_maturity_and_six_checkpoints(self):
        c=self.select()
        for h in HORIZONS:self.obs(h*60,20000)
        finalize(self.lane,NOW+86520);r=individual(self.lane,c,NOW+86520);self.assertTrue(r['mature']);self.assertTrue(r['checkpoint_covered'])
    def test_empty_rates_not_zero(self):self.assertIsNone(aggregate([])['observed_rates_all']['10'])
    def test_daily_cyprus_dst_and_dedup(self):
        for day in ('2026-10-24','2026-10-26'):
            with self.subTest(day=day):
                start=dt.datetime.fromisoformat(day+'T07:59:00').replace(tzinfo=CYPRUS).timestamp()
                self.lane.consider([],start-86400,live=True);self.assertIsNone(due_daily(self.lane,start))
                self.assertIsNotNone(due_daily(self.lane,start+60));self.assertIsNone(due_daily(self.lane,start+61))
    def test_review_date_maturity_and_no_changes(self):
        self.lane.consider([],NOW,live=True);self.assertIsNone(review(self.lane,NOW+14*86400-1));r=review(self.lane,NOW+14*86400)
        self.assertEqual(r['review'],'day14_provisional');self.assertIsNone(r['observed_ten_percent_benchmark_met']);self.assertIsNone(review(self.lane,NOW+14*86400));self.assertIsNone(review(self.lane,NOW+15*86400,True));self.assertIsNotNone(review(self.lane,NOW+15*86400+120,True))

class Delivery(Base):
    def select(self,mint='A',now=NOW):return self.lane.consider([facts(mint,now)],now,log_only=False)[0]
    def test_shadow_never_delivered_even_if_config_predates_it(self):
        self.lane.consider([facts()],NOW)
        self.assertEqual(flush(self.lane,None,self.config(),NOW),[])
    def config(self):return dict(channel='new-channel',new_channel_confirmed=True,confirmed_at=NOW-1)
    def test_required_fields_and_footer(self):
        c=self.select();m=message(c);self.assertIn(FOOTER,m)
        for x in ('DEMO','dev+first2','Buyers','https://pump.fun/coin/','https://axiom.trade/t/','https://gmgn.ai/sol/token/','```'):self.assertIn(x,m)
    def test_late_ticket(self):self.assertTrue(message(self.select(),NOW+61).startswith('LATE'))
    def test_unconfirmed_never_sends(self):
        with self.assertRaises(ValueError):flush(self.lane,None,{},NOW)
    def test_no_retroactive_shadow(self):
        self.select();self.assertEqual(flush(self.lane,None,{**self.config(),'confirmed_at':NOW+1},NOW+2),[])
    def test_success_once(self):
        class T:
            def send(self,*a,**k):return 'receipt'
        self.select();self.assertEqual(flush(self.lane,T(),self.config(),NOW),['alert:A']);self.assertEqual(flush(self.lane,None,self.config(),NOW+1),[])
    def test_rate_limit_queued_and_global(self):
        class T:
            def send(self,*a,**k):raise RateLimited(120)
        self.select();self.assertEqual(flush(self.lane,T(),self.config(),NOW),[]);self.assertEqual(flush(self.lane,None,self.config(),NOW+119),[]);self.assertEqual(list(self.j.rows('sent')),[])

class ExportAndSources(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name);self.db=self.path/'protected.sqlite';c=sqlite3.connect(self.db)
        c.executescript('CREATE TABLE launches(mint,created_ts,creator,name,symbol,protocol,token_program,pump_pool,first_seen,last_pump_seen,last_trade_ts,current_mc,complete,pinned_pair); CREATE TABLE snapshots(mint,ts,pair,price,mc,liq);CREATE TABLE pl_results(secret);CREATE TABLE pl_predictions(secret);')
        c.execute('INSERT INTO launches VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',('A',(NOW-600)*1000,'dev','demo','D','pump',None,None,NOW*1000,NOW*1000,NOW*1000,10000,0,None));c.commit();c.close()
    def tearDown(self):self.tmp.cleanup()
    def test_export_never_redates_cached_mc(self):
        c=readonly(self.db);frame=collect(c,NOW);self.assertIsNone(frame['launches'][0]['mc']);c.close()
    def test_db_unchanged_and_protected_tables_denied(self):
        before=hashlib.sha256(self.db.read_bytes()).hexdigest();c=readonly(self.db)
        for sql in ('SELECT * FROM pl_results','SELECT * FROM pl_predictions','UPDATE launches SET current_mc=0','PRAGMA user_version=3','CREATE TABLE evil(x)'):
            with self.assertRaises(sqlite3.DatabaseError):c.execute(sql).fetchall()
        collect(c,NOW);c.close();self.assertEqual(before,hashlib.sha256(self.db.read_bytes()).hexdigest())
    def test_zero_cache_liquidity_unknown(self):
        c=sqlite3.connect(self.db);c.execute('INSERT INTO snapshots VALUES(?,?,?,?,?,?)',('A',NOW,None,None,10000,0));c.commit();c.close()
        c=readonly(self.db);frame=collect(c,NOW);self.assertEqual(frame['launches'][0]['mc'],10000);self.assertIsNone(frame['observations'][0]['liquidity']);c.close()
    def test_public_rpc_method_allowlist_and_budget(self):
        c=Collector(self.path/'rpc.sqlite');c.rpc.budget(0)
        for method in ('sendTransaction','getTransaction'):
            with self.assertRaises(SourceUnavailable):c.rpc.call(method)
        c.cache.close()
    def test_private_destinations_denied(self):
        for url in ('http://example.org','https://user:password@example.org','https://example.org:444','https://127.0.0.1'):
            with self.subTest(url=url),self.assertRaises(SourceUnavailable):PublicHTTPS().get(url)
    def test_retry_after_not_clamped_early(self):self.assertEqual(retry_seconds({'Retry-After':'7200'}),7200);self.assertEqual(retry_seconds({'Retry-After':'garbage'}),60)
    def test_atomic_symlink_refused(self):
        p=self.path/'out';p.symlink_to(self.db)
        with self.assertRaises(ValueError):atomic(p,{})
    def test_feed_usd_alias_conflict_unknown(self):
        class H:
            def get(self,*a,**k):return dict(status=200,headers={},body=json.dumps([dict(mint='A',created_timestamp=(NOW-600)*1000,market_cap_usd=10000,usd_market_cap=20000)]).encode())
        c=readonly(self.db);frame=collect(c,NOW);c.close()
        with patch('exporter.time.time',return_value=NOW):refresh(frame,H())
        self.assertIsNone(frame['launches'][0]['mc'])
    def test_failed_tx_not_a_buy(self):
        r=decode_tx({'meta':{'err':{'InstructionError':[0,'failed']}},'slot':1,'blockTime':1},'A','s');self.assertEqual(r['trades'],[])

if __name__=='__main__':unittest.main()
