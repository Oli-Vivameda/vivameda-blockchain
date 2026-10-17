"""Offline portable policy tests. No credentials, network or runtime state."""
import io
from pathlib import Path
import sqlite3
import sys
import types
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
# Public layout: notifications/tests/test_policy.py.
try:import mute
except ImportError:
 sys.path.insert(0,str(Path(__file__).resolve().parent));import mute
SOURCE="""def telegram_send(text):
    raise AssertionError('network forbidden')
def notify(text):
    telegram_send(text)
def collect():
    return 'observation preserved'
"""
class Policy(unittest.TestCase):
 def test_changed_source_refused(self):
  with self.assertRaises(ValueError):mute.patch('watch',SOURCE+'\n',mute.sha(SOURCE.encode()))
 def test_watch_suppressed_without_changing_capture(self):
  n={};exec(mute.patch('watch',SOURCE,mute.sha(SOURCE.encode())),n)
  with patch('sys.stdout',new=io.StringIO()):self.assertFalse(n['notify']('fixture'))
  self.assertEqual(n['collect'](),'observation preserved')
 def test_watch_state_writes_require_review(self):
  source=SOURCE.replace('    telegram_send(text)','    store.execute(text)\n    telegram_send(text)')
  with self.assertRaisesRegex(ValueError,'state_write_requires_review'):mute.rewrite('watch',source)
 def test_pool_queue_suppression_never_fakes_receipt(self):
  source="""def drain(store,sender,now):
    sender.send('forbidden')
def observe():
    return 'still collecting'
"""
  n={};exec(mute.patch('pool',source,mute.sha(source.encode())),n)
  db=sqlite3.connect(':memory:');db.execute('CREATE TABLE outbox(status TEXT,expires REAL,message_id TEXT)')
  db.execute("INSERT INTO outbox VALUES('pending',200,NULL)");db.execute("INSERT INTO outbox VALUES('pending',1,NULL)")
  store=types.SimpleNamespace(db=db,commit=db.commit)
  n['drain'](store,None,100)
  self.assertEqual(db.execute('SELECT status,message_id FROM outbox').fetchall(),[('suppressed_owner',None),('expired',None)])
  self.assertEqual(n['observe'](),'still collecting');db.close()
 def test_prediction_suppression_reports_zero_sent(self):
  source="""def dispatch(root,scan,research,sender=None,now=None):
    return sender('forbidden')
def startup(root,sender=None):
    return sender('forbidden')
"""
  writes=[];n={'time':types.SimpleNamespace(time=lambda:123),'s':types.SimpleNamespace(write_json=lambda *args:writes.append(args[-1]))}
  exec(mute.patch('prediction',source,mute.sha(source.encode())),n)
  r=n['dispatch']('fixture',{},{});self.assertEqual(r['sent'],0);self.assertEqual(r['state'],'suppressed_owner')
  self.assertFalse(n['startup']('fixture')['startup_sent']);self.assertEqual(len(writes),1)
if __name__=='__main__':unittest.main()
