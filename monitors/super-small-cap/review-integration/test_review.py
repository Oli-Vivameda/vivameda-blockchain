import copy, json, sqlite3, tempfile, unittest
from pathlib import Path
import review_worker as w

M='A'*32;P='B'*32;NOW=10000

def fixture():
    checks={k:{'status':'PASS','observed_at':NOW,'evidence_refs':['verified:'+k]} for k in w.CORE}
    evidence={k:{'text':k+' supplied fact'} for k in ['chart','participation','thesis','invalidation','case_failure','case_held_gain']}
    p={'mint':M,'pair':P,'chain':'solana','alert_ts':NOW-120,'observations':[{'mint':M,'pair':P,'ts':t,'price':1} for t in [NOW-90,NOW-45,NOW]],'market_cap':15000,'liquidity':3000,'cap_source':'provider_marketCap_not_fdv','screening':{'mint':M,'pair':P,'chain':'solana','checked_at':NOW,'checks':checks},'evidence':evidence,'comparable_pair_available':True}
    s={'decision':'FIRE_REVIEWED','setup':'developing_base','selections':{'chart_setup':['chart'],'participation_and_liquidity':['participation'],'thesis':['thesis'],'historical_failure':['case_failure','case_held_gain'],'invalidation':['invalidation']}}
    return p,s

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        (self.root/'review_config.json').write_text(json.dumps({'policy':w.POLICY,'telegram_delivery_enabled':True,'deadline_ts':None,'live_execution':False}))
        self.db=w.connect(self.root/'reviews.sqlite');self.addCleanup(self.db.close)
        self.p,self.s=fixture()
    def reviewed(self):return w.evaluate(self.p,self.s,NOW)
    def deliver(self,p=None,r=None,**kwargs):
        if p is None:p,r=self.reviewed()
        return w.dispatch(self.db,p,r,1,self.root,clock=lambda:NOW,screen_reader=lambda *a,**k:self.p['screening'],latest_reader=lambda *a:(15000,NOW),**kwargs)
    def test_fire_requires_separate_review(self):
        self.assertFalse(w.classify(self.p,NOW)['fire_message_eligible'])
        p,r=self.reviewed();self.assertTrue(r['fire_message_eligible'])
    def test_wait_cannot_be_promoted(self):
        self.s['decision']='EARLY_WATCH';p,r=self.reviewed();self.assertEqual(r['classification'],'EARLY_WATCH')
    def test_missing_comparators_stays_promising(self):
        self.p['comparable_pair_available']=False;p,r=self.reviewed();self.assertEqual(r['classification'],'PROMISING_SETUP');self.assertFalse(r['fire_message_eligible'])
    def test_missing_failure_reference_blocks_fire(self):
        self.s['selections']['historical_failure']=['case_held_gain'];p,r=self.reviewed();self.assertEqual(r['classification'],'PROMISING_SETUP')
    def test_unknown_core_blocks_fire(self):
        self.p['screening']['checks']['token_controls']['status']='UNKNOWN';p,r=self.reviewed();self.assertEqual(r['classification'],'EARLY_WATCH')
    def test_explicit_rejection_is_avoid(self):
        self.p['screening']['checks']['liquidity_control']['status']='REJECT';p,r=self.reviewed();self.assertEqual(r['classification'],'AVOID')
    def test_background_unknown_allowed_and_disclosed(self):
        p,r=self.reviewed();self.assertTrue(r['fire_message_eligible']);self.assertEqual(len(r['unknowns']),4)
    def test_gapped_chart(self):
        self.p['observations'][1]['ts']=NOW-1;self.p['observations'][0]['ts']=NOW-150;p,r=self.reviewed();self.assertFalse(r['fire_message_eligible'])
    def test_wrong_pair(self):
        self.p['observations'][1]['pair']='C'*32;p,r=self.reviewed();self.assertFalse(r['fire_message_eligible'])
    def test_model_cannot_invent_facts(self):
        self.s['selections']['thesis']=['invented_revenue'];self.assertRaises(ValueError,self.reviewed)
    def test_model_cannot_execute(self):
        self.s['execute']='buy';self.assertRaises(ValueError,self.reviewed)
    def test_wrong_semantic_section(self):
        self.s['selections']['chart_setup']=['thesis'];self.assertRaises(ValueError,self.reviewed)
    def test_duplicate_ref_schema(self):
        self.s['selections']['chart_setup']=[{}];self.assertRaises(ValueError,self.reviewed)
    def test_unknown_liquidity_no_fire(self):
        self.p['liquidity']=None;p,r=self.reviewed();self.assertFalse(r['fire_message_eligible'])
    def test_one_message_and_persistent_dedup(self):
        texts=[];self.assertEqual(self.deliver(sender=lambda t:texts.append(t) or 42),'sent')
        self.assertEqual(self.deliver(sender=lambda t:texts.append(t) or 43),'duplicate_suppressed');self.assertEqual(len(texts),1)
        self.assertTrue(texts[0].startswith('🔥 SUPER SMALL CAP — EXPERIMENTAL'))
        self.assertEqual(self.db.execute('SELECT message_id FROM delivery').fetchone()[0],42)
    def test_delivery_timeout_never_resends(self):
        def fail(t):raise TimeoutError()
        self.assertEqual(self.deliver(sender=fail),'delivery_unknown');self.assertEqual(self.deliver(sender=lambda t:42),'duplicate_suppressed')
    def test_delivery_disabled(self):
        cfg=json.loads((self.root/'review_config.json').read_text());cfg['telegram_delivery_enabled']=False;(self.root/'review_config.json').write_text(json.dumps(cfg))
        self.assertEqual(self.deliver(sender=lambda t:42),'delivery_disabled')
    def test_stop_marker(self):
        (self.root/'REVIEW_STOP').touch();self.assertEqual(self.deliver(sender=lambda t:42),'stopped')
    def test_new_reject_blocks_send(self):
        p,r=self.reviewed();self.p=copy.deepcopy(self.p);self.p['screening']['checks']['token_controls']['status']='REJECT'
        self.assertEqual(self.deliver(p,r,sender=lambda t:42),'evidence_changed_or_stale')
    def test_review_stale_before_send(self):
        p,r=self.reviewed();self.assertEqual(w.dispatch(self.db,p,r,1,self.root,sender=lambda t:42,clock=lambda:NOW+46,screen_reader=lambda *a,**k:self.p['screening']),'evidence_changed_or_stale')
    def test_current_cap_outside_band(self):
        p,r=self.reviewed();self.assertEqual(w.dispatch(self.db,p,r,1,self.root,sender=lambda t:42,clock=lambda:NOW,screen_reader=lambda *a,**k:self.p['screening'],latest_reader=lambda *a:(25000,NOW)),'current_band_or_price_unavailable')
    def test_protected_inventory_reads_only_mints(self):
        p=self.root/'scout.sqlite';c=sqlite3.connect(p);c.execute('CREATE TABLE pl_predictions(mint TEXT,secret_probability REAL)');c.execute('INSERT INTO pl_predictions VALUES(?,.9)',(M,));c.commit();c.close()
        self.assertEqual(w.protected_mints(p),{M})
    def test_missing_protected_inventory_fails_closed(self):
        p=self.root/'scout.sqlite';sqlite3.connect(p).close();self.assertRaises(ValueError,w.protected_mints,p)
    def test_read_query_budget_resets_after_model_wait(self):
        from unittest.mock import patch
        p=self.root/'capture.sqlite';sqlite3.connect(p).close();clock=[100.0]
        with patch.object(w.time,'monotonic',lambda:clock[0]):
            with w.readonly(p) as c:
                clock[0]=200.0
                row=c.execute('WITH RECURSIVE x(v) AS (SELECT 1 UNION ALL SELECT v+1 FROM x WHERE v<10000) SELECT sum(v) FROM x').fetchone()
                self.assertEqual(row[0],50005000)
    def test_agent_settings_literal_only(self):
        p=self.root/'agent.py';p.write_text("SYSTEM = '"+w.POLICY+"'\nMODEL='current-local-model'\nraise Exception('never execute')\n")
        self.assertEqual(w.agent_settings(p)['MODEL'],'current-local-model')
    def test_model_transport_uses_schema_and_bounded_local_endpoint(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,n):return json.dumps({'done':True,'message':{'content':json.dumps({'decision':'EARLY_WATCH','setup':'unresolved','refs':['chart','participation','invalidation']})}}).encode()
        class Opener:
            def open(self,req,timeout):
                self.request=req;self.timeout=timeout;return Response()
        op=Opener();result=w.model_review(self.p,{'MODEL':'installed-local-model','SYSTEM':w.POLICY},op)
        self.assertEqual(result['decision'],'EARLY_WATCH');self.assertEqual(op.request.full_url,'http://127.0.0.1:11434/api/chat');self.assertEqual(op.timeout,25)
        self.assertEqual(json.loads(op.request.data)['format']['type'],'object')
    def test_model_truncation_is_not_accepted(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,n):return json.dumps({'done':True,'done_reason':'length','message':{'content':'{}'}}).encode()
        class Opener:
            def open(self,*a,**k):return Response()
        self.assertRaises(ValueError,w.model_review,self.p,{'MODEL':'local','SYSTEM':w.POLICY},Opener())
    def test_run_complete_path(self):
        from importlib.util import spec_from_file_location,module_from_spec
        spec=spec_from_file_location('capture_fixture',Path(__file__).parent/'collector_fixture.py');module=module_from_spec(spec);spec.loader.exec_module(module)
        with module.connect(self.root/'capture.sqlite') as c:
            c.execute('INSERT INTO tokens VALUES(?,?,?)',(M,NOW-120,NOW));
            c.execute('INSERT INTO entries VALUES(?,?,?,?,?,?,?)',(M,P,NOW-120,1,15000,w.POLICY,'{}'))
            for t in [NOW-90,NOW-45,NOW]:c.execute('INSERT INTO observations VALUES(?,?,?,?,?,?,?)',(M,P,t,1,15000,3000,json.dumps({'cap_source':'provider_marketCap_not_fdv'})))
            c.commit()
        self.s['selections']['historical_failure']=['comparison_missing']
        report=w.run(self.root,clock=lambda:NOW,model=lambda *a:self.s,screen_reader=lambda *a,**k:self.p['screening'],sender=lambda t:42,exclusions=lambda:set(),settings_reader=lambda:{})
        # No manufactured comparable pair: real run records PROMISING, never sends.
        self.assertEqual(report['classification'],'PROMISING_SETUP');self.assertEqual(report['telegram_messages_sent'],0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM assessments').fetchone()[0],1)
    def test_run_fire_path_and_protected_comparator_exclusion(self):
        from collector_fixture import connect
        start=NOW-3700
        with connect(self.root/'capture.sqlite') as c:
            for mint,endpoint in [(M,1),('D'*32,2.2),('E'*32,.4)]:
                ts=NOW-120 if mint==M else start
                c.execute('INSERT INTO entries VALUES(?,?,?,?,?,?,?)',(mint,P,ts,1,15000,w.POLICY,'{}'))
                if mint==M:series=[(t,1) for t in [NOW-90,NOW-45,NOW]]
                else:series=[(ts+i,1+(endpoint-1)*i/3600) for i in range(0,3601,60)]
                for t,price in series:c.execute('INSERT INTO observations VALUES(?,?,?,?,?,?,?)',(mint,P,t,price,15000,3000,json.dumps({'cap_source':'provider_marketCap_not_fdv'})))
            c.commit()
            self.assertEqual(set(w.comparable(c,M,NOW,set(),3000)),{'held_gain','failure'})
            self.assertNotIn('failure',w.comparable(c,M,NOW,{'E'*32},3000))
        texts=[]
        report=w.run(self.root,clock=lambda:NOW,model=lambda *a:self.s,screen_reader=lambda *a,**k:self.p['screening'],sender=lambda t:texts.append(t) or 42,exclusions=lambda:set(),settings_reader=lambda:{})
        self.assertEqual(report['classification'],'FIRE_REVIEWED');self.assertEqual(report['telegram_messages_sent'],1);self.assertEqual(len(texts),1)

if __name__=='__main__':unittest.main()
