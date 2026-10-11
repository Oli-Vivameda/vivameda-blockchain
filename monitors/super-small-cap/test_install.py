import ast, unittest
import install
class InstallerTests(unittest.TestCase):
    def test_additive(self):
        result=install.patch("SYSTEM='existing guards'\ndef dispatch(): return 1\n",'# '+install.MARKER)
        tree=ast.parse(result);self.assertIn('existing guards',tree.body[0].value.value);self.assertIn(install.MARKER,tree.body[0].value.value)
        self.assertEqual(tree.body[1].name,'dispatch')
    def test_repeat_and_nonliteral_refused(self):
        for s in ["SYSTEM='"+install.MARKER+"'",'SYSTEM=build()']:
            with self.assertRaises(ValueError):install.patch(s,'rules')
if __name__=='__main__':unittest.main()
