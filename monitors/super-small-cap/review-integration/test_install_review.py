import os,tempfile,unittest
from pathlib import Path
import install_review as i

class InstallTests(unittest.TestCase):
    def test_bundle_binds_all_files(self):
        self.assertEqual(len(i.bundle()),64);self.assertIn('install_review.py',i.FILES);self.assertIn('helper_hashes.json',i.FILES)
    def test_hash_mismatch_precedes_mutation(self):
        self.assertRaises(ValueError,i.main,['--install','--expected-sha256','wrong'])
    def test_existing_agent_and_collector_are_protected(self):
        paths={str(p) for p in i.protected_paths()};self.assertIn(str(i.AGENT),paths);self.assertIn('/opt/vivameda-super-small-cap/collector.py',paths)
    def test_symlink_target_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'alias';p.symlink_to(Path(d)/'missing');self.assertRaises(ValueError,i.safe,p)
    def test_runtime_directory_under_private_umask(self):
        with tempfile.TemporaryDirectory() as d:
            previous=os.umask(0o077)
            try:
                p=Path(d)/'runtime';i.runtime_directory(p)
                self.assertEqual(p.stat().st_mode&0o777,0o755)
                p.chmod(0o700);i.runtime_directory(p)
                self.assertEqual(p.stat().st_mode&0o777,0o755)
            finally:os.umask(previous)
    def test_previous_failed_bundle_only(self):
        self.assertEqual(i.installed_source_hashes(i.PREVIOUS_BUNDLE,False),i.PREVIOUS_FILES)
        for enabled in (True,None):self.assertRaises(ValueError,i.installed_source_hashes,i.PREVIOUS_BUNDLE,enabled)
        self.assertRaises(ValueError,i.installed_source_hashes,'unknown',False)
if __name__=='__main__':unittest.main()
