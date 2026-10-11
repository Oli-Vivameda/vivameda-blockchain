import copy, json, sqlite3, unittest
import classifier as k
import collector as c

M='1'*32;P='2'*32
def packet():
    p={'mint':M,'pair':P,'chain':'solana','alert_ts':900,'market_cap':15000,'cap_source':'provider_marketCap_not_fdv',
       'observations':[{'mint':M,'pair':P,'ts':t,'price':1-(t-900)*.0001} for t in [900,930,960,990]],
       'screening':{'mint':M,'pair':P,'checked_at':1000,'checks':{n:{'status':'PASS','observed_at':1000,'evidence_refs':['screen']} for n in k.CORE}},
       'evidence':{x:{'source':'test'} for x in ['screen','chart','flow','thesis','failure','risk']}}
    r={'kind':'independent','decision':'FIRE_REVIEWED','mint':M,'pair':P,'reviewed_at':1000,'policy':k.POLICY,'thesis_status':'SUPPORTED'}
    for name,ref in [('chart_setup','chart'),('participation_and_liquidity','flow'),('thesis','thesis'),('historical_failure','failure'),('invalidation','risk')]:r[name]={'text':'supported fixture','evidence_refs':[ref]}
    r['based_on_sha256']=k.evidence_hash(p);p['independent_review']=r;return p

class ClassificationTests(unittest.TestCase):
    def test_independent_short_review(self):
        p=packet();original=copy.deepcopy(p);r=k.classify(p,1000)
        self.assertEqual(r['classification'],'FIRE_REVIEWED');self.assertEqual(p,original)
        self.assertIsNone(r['validated_100x_probability'])
    def test_scanner_alone(self):
        p=packet();del p['independent_review'];self.assertFalse(k.classify(p,1000)['fire_message_eligible'])
    def test_band_and_cap_hash(self):
        for cap in [9999,20001,None,float('nan')]:
            p=packet();p['market_cap']=cap;self.assertFalse(k.classify(p,1000)['fire_message_eligible'])
        p=packet();p['market_cap']=16000;self.assertFalse(k.classify(p,1000)['fire_message_eligible'])
    def test_missing_core_and_rejection(self):
        p=packet();p['screening']['checks']['token_controls']['status']='UNKNOWN';self.assertEqual(k.classify(p,1000)['classification'],'EARLY_WATCH')
        p['screening']['checks']['token_controls']['status']='REJECT';self.assertEqual(k.classify(p,1000)['classification'],'AVOID')
    def test_gaps_future_identity(self):
        for mutate in [lambda p:p['observations'][-1].update(ts=1001),lambda p:p['observations'][-1].update(pair='x'),lambda p:p.update(observations=p['observations'][:2])]:
            p=packet();mutate(p);self.assertFalse(k.classify(p,1000)['fire_message_eligible'])
    def test_failure_and_dedup(self):
        p=packet();del p['independent_review']['historical_failure'];self.assertFalse(k.classify(p,1000)['fire_message_eligible'])
        self.assertFalse(k.classify(packet(),1000,fire_already_delivered=True)['fire_message_eligible'])

class CollectorTests(unittest.TestCase):
    def setUp(self):self.db=c.connect(':memory:');self.db.execute('INSERT INTO tokens VALUES(?,?,?)',(M,800,0))
    def row(self,mc=15000):return {'chainId':'solana','baseToken':{'address':M},'pairAddress':P,'priceUsd':'0.000015','marketCap':mc,'liquidity':{'usd':1000}}
    def test_band_entry_immutable(self):
        c.ingest(self.db,[self.row()],1000,'a');c.ingest(self.db,[self.row(18000)],1015,'b')
        self.assertEqual(self.db.execute('SELECT count(*) FROM observations').fetchone()[0],2)
        self.assertEqual(self.db.execute('SELECT mc FROM entries').fetchone()[0],15000)
    def test_fdv_not_substituted(self):
        r=self.row(None);r['fdv']=15000;self.assertEqual(c.ingest(self.db,[r],1000,'a'),0)
    def test_identity_foreign_mint(self):
        for r in [dict(self.row(),chainId='ethereum'),dict(self.row(),pairAddress='bad'),dict(self.row(),baseToken={'address':'3'*32})]:self.assertEqual(c.ingest(self.db,[r],1000,'a'),0)
    def test_failures_retained_outside_band(self):
        c.ingest(self.db,[self.row()],1000,'a');c.ingest(self.db,[self.row(100)],1100,'b')
        self.assertEqual(self.db.execute('SELECT count(*) FROM observations').fetchone()[0],2)
    def test_no_fabricated_buyers(self):
        c.ingest(self.db,[self.row()],1000,'a');body=json.loads(self.db.execute('SELECT body FROM observations').fetchone()[0]);self.assertEqual(body['organic_buyers'],'UNKNOWN')
    def test_provider_failure_visible(self):
        def fail(_):raise TimeoutError()
        r=c.cycle(self.db,1000,fail);self.assertEqual(r['errors'],['TimeoutError']);self.assertEqual(r['telegram_messages_sent'],0)
    def test_fixed_provider_budget(self):
        seen=[]
        def provider(path):
            seen.append(path)
            return ([{'chainId':'solana','tokenAddress':M}] if path=='token-profiles/latest/v1' else [self.row()]),'hash'
        r=c.cycle(self.db,1000,provider);self.assertLessEqual(len(seen),2);self.assertEqual(r['mode'],'SHADOW')
        self.assertIsNone(r['deadline_ts']);self.assertEqual(r['band_entries'],1)
    def test_receipt_time_after_fetch(self):
        def provider(path):return ([] if path=='token-profiles/latest/v1' else [self.row()]),'hash'
        c.cycle(self.db,1000,provider,clock=lambda:1010)
        self.assertEqual(self.db.execute('SELECT received_at FROM observations').fetchone()[0],1010)
        self.assertEqual(self.db.execute('SELECT decision_ts FROM entries').fetchone()[0],1010)

if __name__=='__main__':unittest.main()
