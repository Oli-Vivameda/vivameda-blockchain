import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import canonical
from sources import Collector,SourceUnavailable,BudgetExceeded
from test_lane import NOW

class NetworkContracts(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.collector=Collector(Path(self.tmp.name)/'cache')
    def tearDown(self):self.collector.cache.close();self.tmp.cleanup()
    def test_rpc_429_persists_cooldown(self):
        class H:
            def get(self,*a,**kw):return dict(status=429,headers={'Retry-After':'900'},body=b'')
        c=self.collector;c.rpc.http=H();c.rpc.budget(2)
        with patch('sources.time.time',return_value=NOW):
            with self.assertRaises(SourceUnavailable):c.rpc.call('getHealth')
            with self.assertRaises(BudgetExceeded):c.rpc.call('getHealth')
        cooldown=json.loads(c.cache.execute("SELECT body FROM config WHERE key='cooldown'").fetchone()[0]);self.assertEqual(cooldown,NOW+900)
    def test_missing_transaction_does_not_advance_cursor(self):
        c=self.collector;c.rpc.budget(10)
        def rpc(method,params):
            if method=='getSignaturesForAddress':return [dict(signature='new',slot=1)]
            if method=='getTransaction':return None
            raise AssertionError(method)
        with patch.object(c.rpc,'call',side_effect=rpc):
            with self.assertRaises(SourceUnavailable):c.history('mint')
        state=json.loads(c.cache.execute('SELECT body FROM scan').fetchone()[0]);self.assertIsNone(state['cursor']);self.assertEqual(state['pending'][0]['signature'],'new')
    def test_cursor_gap_not_silently_accepted(self):
        c=self.collector;c.save_scan('mint',dict(cursor='lost',before=None,head=None,pending=[],paging_done=False,scan_at=None))
        with patch.object(c.rpc,'call',return_value=[dict(signature='new',slot=2)]):
            with self.assertRaisesRegex(SourceUnavailable,'cursor_gap'):c.history('mint')
    def test_social_only_successful_origin_links(self):
        class H:
            def get(self,url,**kw):
                if url.endswith('meta'):return dict(status=200,body=json.dumps(dict(twitter='https://evil.example/x',telegram='https://t.me/demo',website='https://example.org')).encode())
                return dict(status=200 if 't.me' in url else 403,url=url)
        self.collector.http=H();links=self.collector.social('https://example.org/meta');self.assertEqual([x['url'] for x in links],['https://t.me/demo'])

if __name__=='__main__':unittest.main()
