import tempfile,unittest
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
if __name__=='__main__':unittest.main()
