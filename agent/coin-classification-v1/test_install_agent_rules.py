import ast
import unittest
import install_agent_rules as i

class InstallTests(unittest.TestCase):
    def test_only_system_changes(self):
        source="import os\nSYSTEM = '''Existing guards.'''\ndef run():\n    return SYSTEM\n"
        updated=i.patch(source,'# '+i.MARKER+'\nInstructions')
        before=ast.parse(source);after=ast.parse(updated)
        self.assertEqual(ast.dump(before.body[0]),ast.dump(after.body[0]))
        self.assertEqual(ast.dump(before.body[2]),ast.dump(after.body[2]))
        self.assertIn('Existing guards.',after.body[1].value.value)
        self.assertIn(i.MARKER,after.body[1].value.value)

    def test_duplicate_and_unexpected_system_fail_closed(self):
        with self.assertRaises(ValueError):i.patch('SYSTEM = '+repr(i.MARKER),'rules')
        with self.assertRaises(ValueError):i.patch('SYSTEM = get_rules()','rules')

if __name__=='__main__':unittest.main()
