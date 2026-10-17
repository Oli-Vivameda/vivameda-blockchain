"""Exercise the real staging path against isolated activated study fixtures."""
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from core import Journal
import stream_stage as stage_module
from verify import verify

class ActivatedStage(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name)
        self.base=root/'runtime';self.state=root/'state';self.source=root/'source'
        for p in (self.base,self.state,self.source):p.mkdir(mode=0o755)
        (self.state/'process.lock').touch()
        self.journal=self.state/'lane.sqlite3';j=Journal(self.journal)
        j.atomic(lambda:j.add('activation','activation',{'at':1234.5},1234.5))
        j.atomic(lambda:j.add('cohort','cohort:fixture',{'mint':'fixture','at':1235},1235))
        j.db.close()
        data=b'print("offline staging fixture")\n';(self.source/'fixture.py').write_bytes(data)
        raw=(json.dumps({'sha256':{'fixture.py':hashlib.sha256(data).hexdigest()}},sort_keys=True)+'\n').encode()
        (self.source/'BUNDLE.json').write_bytes(raw);self.expected=hashlib.sha256(raw).hexdigest()
        self.calls=[];self.mutate=False
    def tearDown(self):self.tmp.cleanup()
    def run_command(self,args,**kwargs):
        self.calls.append(args)
        if args[0]=='systemctl':return SimpleNamespace(stdout='inactive\n',returncode=0)
        if self.mutate:
            j=Journal(self.journal);j.atomic(lambda:j.add('fixture','new-event',{},1236));j.db.close()
        return SimpleNamespace(returncode=0)
    def invoke(self):
        original_stat=Path.stat
        def controlled_stat(path,*args,**kwargs):
            s=original_stat(path,*args,**kwargs)
            if path==self.base:
                values=list(s);values[4]=0;return os.stat_result(values)
            return s
        def check(expected,root):
            if expected==stage_module.OLD:return {}
            return verify(expected,root)
        with ExitStack()as stack:
            stack.enter_context(patch.object(stage_module,'BASE',self.base));stack.enter_context(patch.object(stage_module,'STATE',self.state))
            stack.enter_context(patch.object(stage_module.os,'geteuid',return_value=0));stack.enter_context(patch.object(Path,'stat',controlled_stat))
            stack.enter_context(patch.object(stage_module,'verify',side_effect=check))
            return stage_module.stage(self.expected,self.source,self.run_command)
    def test_stages_activated_study_with_cohort_preserving_exact_journal(self):
        before=self.journal.read_bytes();result=self.invoke()
        self.assertTrue(result['staged']);self.assertTrue(result['journal_preserved']);self.assertEqual(result['activation'],1234.5)
        self.assertFalse(result['started']);self.assertFalse(result['enabled']);self.assertFalse(result['units_changed'])
        self.assertEqual(before,self.journal.read_bytes());verify(self.expected,self.base/self.expected)
        self.assertTrue(any('-m'in args and 'unittest'in args for args in self.calls))
        for args in self.calls:
            if args[0]=='systemctl':self.assertEqual(args[1],'show')
    def test_repeat_stage_verifies_release_without_mutation(self):
        self.invoke();before=self.journal.read_bytes();result=self.invoke()
        self.assertTrue(result['already_staged']);self.assertEqual(before,self.journal.read_bytes())
    def test_corrupt_chain_refuses_before_copy(self):
        c=sqlite3.connect(self.journal);c.execute('DROP TRIGGER no_update');c.execute("UPDATE events SET hash='corrupt' WHERE seq=1");c.commit();c.close()
        with self.assertRaisesRegex(ValueError,'existing_journal_corrupt'):self.invoke()
        self.assertFalse((self.base/self.expected).exists())
    def test_changed_journal_during_staging_refuses_start(self):
        self.mutate=True
        with self.assertRaisesRegex(ValueError,'journal_changed_do_not_start'):self.invoke()
        for args in self.calls:
            if args[0]=='systemctl':self.assertEqual(args[1],'show')
    def test_missing_journal_is_not_created(self):
        self.journal.unlink()
        with self.assertRaisesRegex(ValueError,'existing_state_required'):self.invoke()
        self.assertFalse(self.journal.exists());self.assertFalse((self.base/self.expected).exists())
    def test_read_only_snapshot_returns_activation_and_cohort_count(self):
        before=self.journal.read_bytes();state=stage_module.journal_state(self.journal)
        self.assertEqual(state['events'],2);self.assertEqual(state['activation'],1234.5);self.assertEqual(state['cohorts'],1)
        self.assertEqual(before,self.journal.read_bytes())
