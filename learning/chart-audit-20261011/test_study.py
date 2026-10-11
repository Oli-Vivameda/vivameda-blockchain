import unittest
import study

class StudyTests(unittest.TestCase):
    def rows(self):return [(9400+i*60,1+i*.001,'pool') for i in range(11)]

    def test_future_price_does_not_change_pre_call_features(self):
        self.assertEqual(study.price_features(self.rows(),10000),study.price_features(self.rows()+[(10060,999,'pool')],10000))

    def test_same_window_for_longer_retained_history(self):
        self.assertEqual(study.price_features(self.rows(),10000),study.price_features([(9000,999,'pool')]+self.rows(),10000))

    def test_edges_gaps_and_pool_identity_are_checked(self):
        for rows in [self.rows()[3:],self.rows()[:-3],[(t,p,'other' if i==5 else pool) for i,(t,p,pool) in enumerate(self.rows())],self.rows()[:3]+self.rows()[7:]]:
            self.assertEqual(study.price_features(rows,10000),{})

    def test_flat_chart_finite(self):
        x=study.price_features([(t,1,pool) for t,p,pool in self.rows()],10000)
        self.assertEqual(x['range10'],0);self.assertEqual(x['drawdown10'],0);self.assertEqual(x['position10'],.5)

    def case(self,id,mint,primary,eligible,endpoint):
        return {'id':id,'mint':mint,'symbol':mint,'primary':primary,'decision_ts':10000,'regime':'COMPRESSION','entry_mc':100,'entry_liq':100,
            'features':{'buy_ratio':.8},'horizons':{'1440':{'eligible':eligible,'endpoint_class':endpoint,'peak_then_collapse':False}}}

    def test_first_calls_only_missing_outcomes_not_failures(self):
        cases=[self.case('a','a',True,True,'HELD_GAIN'),self.case('b','a',False,True,'LOST_HALF'),self.case('c','c',True,False,None)]
        recovery={'cases':[{'id':c['id'],'saved_pre_price_samples':self.rows()} for c in cases]}
        r=study.study({'cases':cases,'inventory':{}},recovery)
        self.assertEqual(r['first_call_tokens'],2);self.assertEqual(r['complete_chart_and_24h_outcome'],1)
        self.assertEqual(r['all_groups']['held_2x']['n'],1);self.assertEqual(r['all_groups']['lost_half_without_2x']['n'],0)

    def test_missing_buy_evidence_does_not_qualify_screen(self):
        c=self.case('a','a',True,True,'HELD_GAIN');c['features']={'buy_ratio':None}
        r=study.study({'cases':[c],'inventory':{}},{'cases':[{'id':'a','saved_pre_price_samples':self.rows()}]})
        self.assertEqual(r['illustrative_post_hoc_screen']['selected'],0)

if __name__=='__main__':unittest.main()
