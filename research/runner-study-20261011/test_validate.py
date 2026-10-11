import copy
import json
from pathlib import Path
import unittest
from validate import decision_view, price_path, validate_status

T0 = '2026-10-01T00:00:00Z'
T1 = '2026-10-01T00:01:00Z'
T2 = '2026-10-01T00:02:00Z'
T3 = '2026-10-01T00:03:00Z'


class IntegrityTests(unittest.TestCase):
    def evidence(self, **changes):
        row = dict(mint='m', pair='p', observed_at=T0, known_at=T0,
                   knowledge_time_verified=True, time_precision='timestamp')
        row.update(changes)
        return row

    def samples(self):
        return [dict(mint='m', pair='p', time=t, price=p)
                for t, p in [(T0, 1), (T1, 10), (T2, .5), (T3, 100)]]

    def status(self):
        return json.loads(Path(__file__).with_name('STATUS.json').read_text())

    def test_late_knowledge_excluded(self):
        self.assertEqual(decision_view([self.evidence(known_at=T2)], T1, 'm', 'p')['included'], [])

    def test_late_observation_excluded(self):
        self.assertEqual(decision_view([self.evidence(observed_at=T2)], T1, 'm', 'p')['included'], [])

    def test_unverified_archive_time_excluded(self):
        result = decision_view([self.evidence(knowledge_time_verified=False)], T1, 'm', 'p')
        self.assertEqual(result['excluded'][0]['reason'], 'knowledge_time_unverified')

    def test_identity_bound(self):
        self.assertEqual(decision_view([self.evidence(pair='other')], T1, 'm', 'p')['included'], [])

    def test_date_only_excluded(self):
        self.assertEqual(decision_view([self.evidence(time_precision='date_only')], T1, 'm', 'p')['included'], [])

    def test_asof_evidence_allowed(self):
        self.assertEqual(len(decision_view([self.evidence()], T1, 'm', 'p')['included']), 1)

    def test_peak_not_held_and_future_excluded(self):
        path = price_path(self.samples(), T0, T2, 'm', 'p')
        self.assertEqual(path['peak_multiple'], 10)
        self.assertEqual(path['endpoint_multiple'], .5)
        self.assertFalse(path['executable_return_verified'])

    def test_no_invented_entry(self):
        with self.assertRaises(ValueError):
            price_path(self.samples(), '2026-10-01T00:00:30Z', T2, 'm', 'p')

    def test_conflicting_sample_rejected(self):
        with self.assertRaises(ValueError):
            price_path(self.samples() + [dict(mint='m', pair='p', time=T0, price=2)], T0, T2, 'm', 'p')

    def test_incomplete_status_valid(self):
        self.assertFalse(validate_status(self.status())['complete'])

    def test_false_completion_rejected(self):
        status = self.status()
        status['complete'] = True
        with self.assertRaises(ValueError):
            validate_status(status)

    def test_rank_provenance_required(self):
        status = self.status()
        status['ranked_records'] = [dict(chain='solana', mint='m', ranked_runner_verified=True)]
        with self.assertRaises(ValueError):
            validate_status(status)

    def test_duplicate_rank_rejected(self):
        status = self.status()
        row = dict(chain='solana', mint='m', ranked_runner_verified=False)
        status['ranked_records'] = [row, copy.deepcopy(row)]
        with self.assertRaises(ValueError):
            validate_status(status)


if __name__ == '__main__':
    unittest.main()
