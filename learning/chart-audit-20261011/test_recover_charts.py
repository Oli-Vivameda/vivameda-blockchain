import sqlite3
import unittest
import recover_charts as recovery

class RecoveryTests(unittest.TestCase):
    def source(self, rows):
        c=sqlite3.connect(':memory:');c.execute('CREATE TABLE snapshots(mint,ts,price,pair)')
        c.executemany('INSERT INTO snapshots VALUES(?,?,?,?)',rows);c.commit();return c

    def test_excludes_protected_and_future_samples(self):
        c=self.source([('ordinary',9900,1,'pool'),('ordinary',10100,999,'pool'),('protected',9900,999,'pool')])
        cases=[{'id':'a','mint':'ordinary','decision_ts':10000},{'id':'x','mint':'protected','decision_ts':10000}]
        rows,receipts,n=recovery.merge_samples([('test',c)],cases,{'protected'})
        self.assertEqual(rows,{'a':[(9900,1,'pool')]});self.assertEqual(n,0)

    def test_conflicting_sources_not_silently_chosen(self):
        sources=[('one',self.source([('ordinary',9900,1,'pool')])),('two',self.source([('ordinary',9900,2,'pool')]))]
        rows,_,n=recovery.merge_samples(sources,[{'id':'a','mint':'ordinary','decision_ts':10000}],set())
        self.assertEqual(rows['a'],[]);self.assertEqual(n,1)

    def test_missing_schema_remains_missing(self):
        c=sqlite3.connect(':memory:')
        rows,receipts,n=recovery.merge_samples([('missing',c)],[{'id':'a','mint':'ordinary','decision_ts':10000}],set())
        self.assertEqual(rows['a'],[]);self.assertNotEqual(receipts[0]['status'],'read_complete')

if __name__=='__main__':unittest.main()
