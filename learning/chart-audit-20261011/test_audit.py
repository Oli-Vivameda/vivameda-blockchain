import sqlite3
import unittest
import audit


class AuditTests(unittest.TestCase):
    def case(self):
        return {'id':'a','mint':'mint-a','symbol':'<test>','decision_ts':10000,'entry_mc':100,'entry_price':1}

    def checkpoint(self, **kw):
        x={'observed_ts':13600,'lateness':0,'multiple':.2,'coverage_ok':1,'max_gap':60}
        x.update(kw);return x

    def observations(self, first='target'):
        values=[100]*61
        if first=='target': values[10]=220;values[20]=40
        else: values[10]=40;values[20]=220
        values[-1]=20
        return [(10000+i*60,m,25000) for i,m in enumerate(values)]

    def test_spike_and_collapse_is_not_held_gain(self):
        x=audit.path_metrics(self.case(),self.observations(),self.checkpoint(),15000,60)
        self.assertTrue(x['eligible']);self.assertTrue(x['peak_then_collapse'])
        self.assertEqual(x['endpoint_class'],'LOST_HALF')
        self.assertEqual(x['observed_2x_vs_half_order'],'TARGET_FIRST')

    def test_stop_before_rebound(self):
        x=audit.path_metrics(self.case(),self.observations('stop'),self.checkpoint(),15000,60)
        self.assertEqual(x['observed_2x_vs_half_order'],'STOP_FIRST')

    def test_late_or_wrong_checkpoint_not_scored(self):
        for cp in [self.checkpoint(lateness=181,observed_ts=13781),
                   self.checkpoint(lateness=0,observed_ts=13601),
                   self.checkpoint(coverage_ok=0),self.checkpoint(multiple=float('nan'))]:
            self.assertFalse(audit.path_metrics(self.case(),self.observations(),cp,15000,60)['eligible'])

    def test_gap_is_not_repaired_by_summary_flag(self):
        obs=self.observations();obs=[r for r in obs if not 11200<=r[0]<=11500]
        self.assertFalse(audit.path_metrics(self.case(),obs,self.checkpoint(),15000,60)['eligible'])

    def test_future_extreme_is_not_used(self):
        obs=[(t,100,25000) for t,_,_ in self.observations()]+[(13660,100000,25000)]
        x=audit.path_metrics(self.case(),obs,self.checkpoint(multiple=1),15000,60)
        self.assertEqual(x['max_multiple'],1)
        self.assertEqual(x['observed_2x_vs_half_order'],'NEITHER')

    def test_pending_stays_pending(self):
        x=audit.path_metrics(self.case(),self.observations(),self.checkpoint(),13000,60)
        self.assertFalse(x['eligible']);self.assertEqual(x['reason'],'pending')

    def test_pre_call_future_sample_excluded(self):
        rows=[(9400+i*60,1+i*.001,'pool') for i in range(11)]
        a,status=audit.pre_features(rows,10000)
        b,_=audit.pre_features(rows+[(10060,1000,'pool')],10000)
        self.assertEqual(a,b);self.assertTrue(a)
        self.assertEqual(status,'saved_price_samples_pool_consistent')

    def test_mixed_pool_not_a_price_pattern(self):
        rows=[(9400+i*60,1+i*.001,'pool' if i<10 else 'other') for i in range(11)]
        x,status=audit.pre_features(rows,10000)
        self.assertFalse(x);self.assertIn('identity',status)

    def fixture(self):
        c=sqlite3.connect(':memory:')
        c.executescript('''
        CREATE TABLE launches(mint TEXT PRIMARY KEY,symbol TEXT,name TEXT,created_ts INTEGER);
        CREATE TABLE v2_cases(id TEXT,mint TEXT,decision_ts INTEGER,source TEXT,features TEXT,
            entry_price REAL,entry_mc REAL,entry_liq REAL,regime TEXT);
        CREATE TABLE pl_predictions(mint TEXT,body TEXT);
        CREATE TABLE pl_results(body TEXT);
        CREATE TABLE snapshots(mint TEXT,ts INTEGER,price REAL,pair TEXT);
        CREATE TABLE v2_observations(id TEXT,observed_ts INTEGER,mc REAL,liq REAL);
        CREATE TABLE v2_outcomes(id TEXT,horizon INTEGER,observed_ts INTEGER,lateness INTEGER,multiple REAL);
        CREATE TABLE v2_horizon_metrics(id TEXT,horizon INTEGER,observed_ts INTEGER,coverage_ok INTEGER,max_gap INTEGER);
        ''')
        for id,mint,ts,source in [('a','mint-a',10000,'ALERT'),('a2','mint-a',10100,'ALERT'),
                                  ('sealed','protected',10000,'ALERT'),('shadow','shadow',10000,'SHADOW')]:
            c.execute('INSERT INTO v2_cases VALUES(?,?,?,?,?,?,?,?,?)',(id,mint,ts,source,'{"band":0.2}',1,100,25000,'COMPRESSION'))
            c.execute('INSERT OR IGNORE INTO launches VALUES(?,?,?,?)',(mint,mint,mint,0))
        c.execute('INSERT INTO pl_predictions VALUES(?,?)',('protected','DO NOT READ'))
        c.executemany('INSERT INTO v2_observations VALUES(?,?,?,?)',[('a',t,m,l) for t,m,l in self.observations()])
        c.execute('INSERT INTO v2_outcomes VALUES(?,?,?,?,?)',('a',60,13600,0,.2))
        c.execute('INSERT INTO v2_horizon_metrics VALUES(?,?,?,?,?)',('a',60,13600,1,60))
        return c

    def test_exclusion_no_protected_body_or_outcomes_read(self):
        c=self.fixture()
        forbidden=[]
        def guard(action,table,column,db,trigger):
            if action==sqlite3.SQLITE_READ and (table=='pl_results' or table=='pl_predictions' and column!='mint'):
                forbidden.append((table,column));return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        c.set_authorizer(guard)
        report,charts=audit.load_audit(c,{'protected':{'result':'sent'},'missing':{'result':'sent'}},15000)
        self.assertEqual(forbidden,[])
        self.assertEqual(report['inventory']['audited_non_holdout_events'],2)
        self.assertEqual(report['inventory']['first_call_tokens'],1)
        self.assertEqual(report['inventory']['protected_alert_events_excluded'],1)
        self.assertEqual(report['horizon_summary']['60']['eligible'],1)
        self.assertEqual(len(charts),2)
        self.assertNotIn('"mint":"protected"',audit.canonical(report))

    def test_missing_exclusion_table_fails_closed(self):
        c=self.fixture();c.execute('DROP TABLE pl_predictions')
        with self.assertRaises(ValueError):audit.load_audit(c,{},15000)

    def test_svg_escapes_metadata_and_does_not_invent_candles(self):
        text=audit.svg_chart(self.case(),[],self.observations())
        self.assertIn('&lt;test&gt;',text);self.assertNotIn('<test>',text)
        self.assertIn('No retained samples',text);self.assertIn('NOT a price candle chart',text)


if __name__=='__main__':unittest.main()
