import copy
import unittest
import classification as c

class ClassificationTests(unittest.TestCase):
    def packet(self):
        p={'mint':'mint','pair':'pool','chain':'solana','alert_ts':9800,
           'observations':[{'mint':'mint','pair':'pool','ts':9400+i*60,'price':1-i*.002} for i in range(11)],
           'screening':{'mint':'mint','pair':'pool','checked_at':10000,'checks':{k:{'status':'PASS','observed_at':10000,'evidence_refs':['screen']} for k in c.CORE}},
           'evidence':{'chart':{'observed_at':10000},'participation':{},'thesis':{},'failure':{},'invalidation':{}}}
        r={'kind':'independent','decision':'FIRE_REVIEWED','mint':'mint','pair':'pool','reviewed_at':10000,'policy':c.POLICY,'thesis_status':'SUPPORTED'}
        for k,ref in [('chart_setup','chart'),('participation_and_liquidity','participation'),('thesis','thesis'),('historical_failure','failure'),('invalidation','invalidation')]:
            r[k]={'text':'Evidence-backed assessment','evidence_refs':[ref]}
        r['based_on_sha256']=c.evidence_hash(p);p['independent_review']=r
        return p

    def test_scanner_pass_does_not_earn_fire(self):
        p=self.packet();del p['independent_review'];r=c.classify(p,10000)
        self.assertEqual(r['classification'],'DISCOVERY');self.assertFalse(r['fire_message_eligible'])

    def test_declining_chart_and_background_unknowns_are_allowed(self):
        r=c.classify(self.packet(),10000)
        self.assertEqual(r['classification'],'FIRE_REVIEWED');self.assertEqual(len(r['unknowns']),4)

    def test_core_reject_wins_over_review(self):
        p=self.packet();p['screening']['checks'][c.CORE[0]]['status']='REJECT'
        self.assertEqual(c.classify(p,10000)['classification'],'AVOID')

    def test_unknown_core_is_watch(self):
        p=self.packet();p['screening']['checks'][c.CORE[0]]['status']='UNKNOWN'
        self.assertEqual(c.classify(p,10000)['classification'],'EARLY_WATCH')

    def test_changed_or_stale_review_cannot_promote(self):
        p=self.packet();p['independent_review']['reviewed_at']=9000
        self.assertNotEqual(c.classify(p,10000)['classification'],'FIRE_REVIEWED')
        p=self.packet();p['observations'][-1]['price']=2
        self.assertNotEqual(c.classify(p,10000)['classification'],'FIRE_REVIEWED')

    def test_missing_failure_case_or_invalidation_cannot_promote(self):
        for name in ('historical_failure','invalidation','thesis','participation_and_liquidity'):
            p=self.packet();del p['independent_review'][name]
            self.assertEqual(c.classify(p,10000)['classification'],'PROMISING_SETUP')

    def test_no_new_observation_no_fire(self):
        p=self.packet();p['alert_ts']=10000;p['independent_review']['based_on_sha256']=c.evidence_hash(p)
        self.assertEqual(c.classify(p,10000)['classification'],'PROMISING_SETUP')

    def test_gaps_future_samples_and_pool_changes_cannot_promote(self):
        a=self.packet();a['observations']=a['observations'][:3]+a['observations'][7:]
        b=self.packet();b['observations'][-1]['ts']=10001
        d=self.packet();d['observations'][-1]['pair']='different'
        for p in (a,b,d):self.assertEqual(c.classify(p,10000)['classification'],'EARLY_WATCH')

    def test_repeat_decision_never_requests_duplicate_fire(self):
        for kwargs in ({'previous_label':'FIRE_REVIEWED'},{'fire_already_delivered':True}):
            r=c.classify(self.packet(),10000,**kwargs)
            self.assertEqual(r['classification'],'FIRE_REVIEWED');self.assertFalse(r['fire_message_eligible'])

    def test_unresolved_evidence_refs_block_fire(self):
        p=self.packet();p['independent_review']['thesis']['evidence_refs']=['invented']
        self.assertEqual(c.classify(p,10000)['classification'],'PROMISING_SETUP')

    def test_no_mutation_or_probability_invention(self):
        p=self.packet();before=copy.deepcopy(p);r=c.classify(p,10000)
        self.assertEqual(p,before);self.assertIsNone(r['validated_100x_probability']);self.assertFalse(r['live_execution'])

    def test_evidenced_thesis_failure_is_avoid(self):
        p=self.packet();r=p['independent_review'];r['decision']='AVOID';r['thesis_failure']={'text':'Observed thesis failure','evidence_refs':['chart']}
        self.assertEqual(c.classify(p,10000)['classification'],'AVOID')

if __name__=='__main__':unittest.main()
