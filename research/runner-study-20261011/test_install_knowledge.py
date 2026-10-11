import ast
import json
from pathlib import Path
import tempfile
import unittest
import urllib.request
from install_knowledge import BEGIN, END, HERE, apply_transaction, patch_agent, patch_worker, system_value, unpatch_agent


class KnowledgeIntegrationTests(unittest.TestCase):
    def rules(self):
        return (HERE/'COMPACT_RULES.md').read_text()

    def test_preserves_agent_code_and_existing_instructions(self):
        source = 'SYSTEM = "old safeguards"\nMODEL = "existing-model"\nx = 7\n'
        new = patch_agent(source, self.rules())
        self.assertEqual(system_value(new)[1], 'old safeguards\n\n'+self.rules())
        self.assertIn('MODEL = "existing-model"\nx = 7', new)

    def test_duplicate_patch_refused(self):
        with self.assertRaises(ValueError):
            patch_agent(patch_agent('SYSTEM = "old"\n', self.rules()), self.rules())

    def test_idempotency_base_source_verifiable(self):
        source = "SYSTEM = 'old'\nMODEL = 'existing'\n"
        self.assertEqual(unpatch_agent(patch_agent(source, self.rules()), self.rules()), source)

    def test_ambiguous_block_refused(self):
        with self.assertRaises(ValueError):
            patch_agent('SYSTEM = "old"\n', self.rules()+BEGIN)

    def test_worker_drift_refused(self):
        with self.assertRaises(ValueError):
            patch_worker('def model_review(): return 0')

    def model_function(self):
        source = patch_worker((HERE/'review_worker.py').read_text())
        tree = ast.parse(source)
        wanted = {'LABELS', 'SETUPS', 'REFERENCE_KEYS'}
        nodes = [n for n in tree.body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id in wanted for t in n.targets)]
        nodes += [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name=='model_review']
        namespace = {'urllib': __import__('urllib'), 'json': json,
                     'canonical': lambda x: json.dumps(x, sort_keys=True),
                     'FIELDS': ('chart_setup','participation_and_liquidity','thesis','historical_failure','invalidation')}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), '<tested-worker-function>', 'exec'), namespace)
        return namespace['model_review']

    def packet(self):
        return dict(mint='m', pair='p', chain='solana', alert_ts=1, observations=[],
                    market_cap=15000, liquidity=1000, evidence={'chart':{'text':'actual prices'}},
                    comparable_pair_available=False, screening={'checked_at':2,'checks':{}})

    def test_actual_model_payload_receives_knowledge(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit):
                return json.dumps({'done':True,'done_reason':'stop','message':{'content':json.dumps({'decision':'EARLY_WATCH','setup':'unresolved','refs':['chart']})}}).encode()
        class Opener:
            def open(self, request, timeout):
                self.payload=json.loads(request.data)
                return Response()
        opener=Opener()
        settings={'MODEL':'existing-model','SYSTEM':'# Vivameda super-small-cap trigger v1\nexisting guards\n## Record and learn\nold material\n'+self.rules()}
        result=self.model_function()(self.packet(),settings,opener=opener)
        prompt=opener.payload['messages'][0]['content']
        self.assertIn(self.rules().strip(),prompt)
        self.assertIn('existing guards',prompt)
        self.assertNotIn('old material',prompt)
        self.assertEqual(opener.payload['model'],'existing-model')
        self.assertEqual(result['decision'],'EARLY_WATCH')

    def test_missing_knowledge_fails_closed_before_request(self):
        with self.assertRaises(ValueError):
            self.model_function()(self.packet(),{'MODEL':'existing','SYSTEM':'no block'},opener=object())

    def test_failed_second_write_restores_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=Path(tmp)/'a',Path(tmp)/'b'
            a.write_bytes(b'old-a'); b.write_bytes(b'old-b')
            failed=False
            def writer(path,raw,meta):
                nonlocal failed
                if path==b and not failed:
                    failed=True
                    raise OSError('injected atomic write refusal')
                path.write_bytes(raw)
            with self.assertRaises(OSError):
                apply_transaction([(a,b'new-a'),(b,b'new-b')],writer)
            self.assertEqual(a.read_bytes(),b'old-a')
            self.assertEqual(b.read_bytes(),b'old-b')


if __name__ == '__main__':
    unittest.main()
