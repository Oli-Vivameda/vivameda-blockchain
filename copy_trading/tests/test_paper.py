import copy
import json
import pathlib
import sys
import tempfile
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from core import Ledger, D, USDC, SOL, TOKEN, JUPITER
from feed import Feed, normalize, Rpc
ROOT = pathlib.Path(__file__).resolve().parents[1]
WALLET = '1' * 32
WALLET2 = '2' * 32

class Paper(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.c = json.loads((ROOT / 'config.json').read_text())
        self.w = json.loads((ROOT / 'watchlist.json').read_text())
        self.w['wallets'] = [dict(address=w, chain='solana', verified=True, primary_attribution='SYNTHETIC TEST ONLY', purchase_evidence='fixture', copy_suitability='fixture') for w in [WALLET, WALLET2]]
        self.path = pathlib.Path(self.tmp.name) / 'test.sqlite3'
        self.l = Ledger(self.path, self.c, self.w)
    def tearDown(self):
        self.l.db.close()
        self.tmp.cleanup()
    def event(self, ident='buy1', side='buy', mint='fixture-mint', **kw):
        e = dict(id=ident, wallet=WALLET, mint=mint, side=side, tx_time=100, detected=101, confirmation='confirmed', qty_raw=1000000, pre_qty_raw=10000000, decimals=6, source_price='1', price_currency='USDC')
        e.update(kw)
        return e
    def quote(self, mint, side, amount, now):
        return dict(mint=mint, side=side, input_raw=amount, min_output_raw=amount, obtained=now, fidelity='size_specific_quote', provider='SYNTHETIC TEST ONLY', embedded_fees_in_output=True, external_cost_usd='0.10', price_impact='0.001', sol_usd='100')
    def risk(self, mint, now):
        return dict(obtained=now, **{x: True for x in self.c['blocking_risk_fields']})
    def reason(self, ident='buy1', s='A'):
        return self.l.db.execute('SELECT reason FROM decisions WHERE event=? AND strategy=?', (ident, s)).fetchone()[0]
    def buy(self, **kw):
        e = self.event(**kw)
        self.l.observe(e)
        self.l.process(self.quote, self.risk, 104)
        return e
    def test_duplicate_atomic_and_restart_cash(self):
        e = self.buy()
        self.l.observe(e)
        self.l.process(self.quote, self.risk, 105)
        self.assertEqual(len(self.l.positions('A')), 1)
        self.assertEqual(self.l.report(105)['strategies']['A']['cash'], '225.00')
        self.l.db.close()
        self.l = Ledger(self.path, self.c, self.w)
        self.l.process(self.quote, self.risk, 106)
        self.assertEqual(self.l.db.execute('SELECT count(*) FROM fills').fetchone()[0], 1)
        self.assertEqual(self.l.report(106)['strategies']['A']['cash'], '225.00')
    def test_partial_source_sell(self):
        self.buy()
        qty = int(self.l.positions('A')[0]['qty'])
        self.l.observe(self.event('sell1', 'sell', qty_raw=3000000, tx_time=105, detected=106))
        self.l.process(self.quote, self.risk, 109)
        self.assertEqual(int(self.l.positions('A')[0]['qty']), qty * 7 // 10)
    def test_partial_exits_not_counted_as_closed_trades(self):
        self.buy()
        self.l.observe(self.event('partial', 'sell', qty_raw=3000000, tx_time=105, detected=106))
        self.l.process(self.quote, self.risk, 109)
        self.assertEqual(self.l.report(109)['strategies']['A']['completed_trades'], 0)
        self.l.observe(self.event('full', 'sell', qty_raw=7000000, pre_qty_raw=7000000, tx_time=110, detected=111))
        self.l.process(self.quote, self.risk, 114)
        self.assertEqual(self.l.report(114)['strategies']['A']['completed_trades'], 1)
    def test_no_unbought_sell(self):
        self.buy(ident='sell1', side='sell')
        self.assertEqual(self.reason('sell1'), 'no_bought_inventory')
    def test_aggregate_token_no_repeated_buy(self):
        self.buy()
        self.l.maintain(self.quote, 104)
        self.buy(ident='buy2', wallet=WALLET2)
        self.assertEqual(self.reason('buy2'), 'existing_token_no_repeat')
    def test_stale_and_future(self):
        for ident, ts in [('stale', 10), ('future', 200)]:
            self.buy(ident=ident, tx_time=ts)
            self.assertEqual(self.reason(ident), 'stale_or_future_signal')
    def test_missing_source_price(self):
        self.buy(source_price=None)
        self.assertEqual(self.reason(), 'missing_reliable_source_price')
    def test_chase(self):
        self.buy(source_price='0.9')
        self.assertEqual(self.reason(), 'price_chase')
    def test_missing_quote(self):
        self.l.observe(self.event())
        self.l.process(lambda *a: None, self.risk, 104)
        self.assertEqual(self.reason(), 'missing_or_invalid_quote')
    def test_buy_route_without_sell_route_skips(self):
        self.l.observe(self.event())
        self.l.process(lambda mint, side, amount, now: self.quote(mint, side, amount, now) if side == 'buy' else None, self.risk, 104)
        self.assertEqual(self.reason(), 'no_fresh_sellability_quote')
        self.assertEqual(self.l.positions('A'), [])
    def test_stale_quote(self):
        def quote(*args):
            q = self.quote(*args); q['obtained'] = 90; return q
        self.l.observe(self.event())
        self.l.process(quote, self.risk, 104)
        self.assertEqual(self.reason(), 'missing_or_invalid_quote')
    def test_early_quote_rejected(self):
        def quote(*args):
            q = self.quote(*args); q['obtained'] = 102; return q
        self.l.observe(self.event())
        self.l.process(quote, self.risk, 104)
        self.assertEqual(self.reason(), 'missing_or_invalid_quote')
    def test_unknown_risk_blocks(self):
        self.l.observe(self.event())
        self.l.process(self.quote, lambda *a: {}, 104)
        self.assertEqual(self.reason(), 'risk_block_or_unknown')
    def test_failed_exit_inventory_and_retry(self):
        self.buy()
        self.l.observe(self.event('sell', 'sell', qty_raw=3000000))
        self.l.process(lambda *a: None, self.risk, 104)
        self.assertEqual(self.reason('sell'), 'failed_exit_quote')
        self.assertEqual(int(self.l.positions('A')[0]['qty']), 24900000)
        self.l.maintain(self.quote, 105)
        self.assertEqual(int(self.l.positions('A')[0]['qty']), 17430000)
        self.l.maintain(self.quote, 106)
        self.assertEqual(int(self.l.positions('A')[0]['qty']), 17430000)
    def test_three_tokens_and_total_cost_cap(self):
        for i in range(4):
            self.l.maintain(self.quote, 104)
            self.buy(ident=str(i), mint='mint' + str(i))
        self.assertEqual(len(self.l.positions('A')), 3)
        self.assertEqual(sum(D(p['cost']) for p in self.l.positions('A')), 75)
        self.assertEqual(self.reason('3'), 'max_tokens')
    def test_all_in_fees_cap(self):
        def quote(*args):
            q = self.quote(*args); q['external_cost_usd'] = '1'; return q
        self.l.observe(self.event())
        self.l.process(quote, self.risk, 104)
        self.assertEqual(self.reason(), 'all_in_cost_cap')
    def test_drawdown_latch_and_exits_continue(self):
        self.buy()
        self.l.maintain(lambda *a: None, 110)  # Unknown liquidation valued zero = 10% drawdown.
        self.l.maintain(self.quote, 111)
        self.buy(ident='later', mint='new')
        self.assertEqual(self.reason('later'), 'entries_paused')
        self.l.observe(self.event('sell', 'sell', qty_raw=10000000, tx_time=112, detected=113))
        self.l.process(self.quote, self.risk, 116)
        self.assertEqual(len(self.l.positions('A')), 0)
    def test_out_of_order_buy_superseded(self):
        self.l.observe(self.event('sell', 'sell', tx_time=102))
        self.buy()
        self.assertEqual(self.reason(), 'superseded_out_of_order_entry')
    def test_out_of_order_sell_not_applied_to_new_inventory(self):
        self.buy(tx_time=103)
        self.l.observe(self.event('old-sell', 'sell', tx_time=100))
        self.l.process(self.quote, self.risk, 105)
        self.assertEqual(self.reason('old-sell'), 'out_of_order_sale')
    def test_binding_change_cannot_reset(self):
        self.c['starting_cash'] = '500'
        with self.assertRaises(ValueError):
            Ledger(self.path, self.c, self.w)
    def test_b_disabled(self):
        self.buy()
        self.assertEqual(self.reason(s='B'), 'strategy_disabled')
        self.assertEqual(self.l.positions('B'), [])
    def test_b_requires_frozen_parameters(self):
        self.c['strategy_b']['enabled'] = True
        with self.assertRaises(AssertionError):
            Ledger(pathlib.Path(self.tmp.name)/'other', self.c, self.w)
    def test_b_independent_and_take_profit(self):
        self.l.db.close()
        self.c['strategy_b'] = dict(enabled=True, frozen_at='test', take_profit='0.1', stop_loss='0.1', max_hold_s=100)
        self.l = Ledger(pathlib.Path(self.tmp.name)/'b', self.c, self.w)
        self.buy()
        self.assertEqual(len(self.l.positions('B')), 1)
        def quote(*args):
            q = self.quote(*args); q['min_output_raw'] = int(q['min_output_raw'] * 1.3); return q
        self.l.maintain(quote, 110)
        self.assertEqual(self.l.positions('B'), [])
        self.assertEqual(len(self.l.positions('A')), 1)
    def test_execution_delay(self):
        self.l.observe(self.event())
        self.l.process(self.quote, self.risk, 102)
        self.assertEqual(self.l.db.execute('SELECT count(*) FROM decisions').fetchone()[0], 0)
    def test_quote_wrong_size_future_impact(self):
        for field, value in [('input_raw', 1), ('obtained', 200), ('price_impact', '0.9')]:
            ident = field
            self.l.observe(self.event(ident))
            def quote(*args):
                q = self.quote(*args); q[field] = value; return q
            self.l.process(quote, self.risk, 104)
            self.assertEqual(self.reason(ident), 'missing_or_invalid_quote')
    def test_missing_source_inventory_sell_skipped(self):
        self.buy()
        self.l.observe(self.event('sell', 'sell', pre_qty_raw=0))
        self.l.process(self.quote, self.risk, 104)
        self.assertEqual(self.reason('sell'), 'unknown_source_sale_fraction')
    def test_feed_missing_cursor_blocks_trades(self):
        with self.l.db:
            for w in [WALLET, WALLET2]:
                self.l.set('cursor:' + w, {'signature':'missing', 'seeded':90})
        class Fake:
            def call(self, method, params):
                if method == 'getSignaturesForAddress':
                    return [{'signature':'new', 'slot':10,'blockTime':99,'err':None}]
                raise AssertionError('Must not fetch/trade across unresolved gap')
        Feed(self.l, Fake()).poll(100)
        self.assertIsNotNone(self.l.get('gap:' + WALLET))
        self.assertEqual(self.l.db.execute('SELECT count(*) FROM events').fetchone()[0], 0)
    def test_missing_transaction_retry_retains_detection(self):
        with self.l.db:
            for w in [WALLET, WALLET2]:
                self.l.set('cursor:' + w, {'signature':'old', 'seeded':90})
        class Fake:
            def call(self, method, params):
                if method == 'getSignaturesForAddress':
                    return [{'signature':'new', 'slot':10,'blockTime':99,'err':None}, {'signature':'old','slot':9,'blockTime':98,'err':None}]
                return None
        Feed(self.l, Fake()).poll(100)
        Feed(self.l, Fake()).poll(110)
        rows = self.l.db.execute("SELECT detected,status FROM seen WHERE signature='new'").fetchall()
        self.assertTrue(all(r['detected'] == 100 and r['status'] == 'pending' for r in rows))
    def test_rpc_write_rejected(self):
        with self.assertRaises(ValueError):
            Rpc('https://example.invalid').call('sendTransaction')
    def test_feed_seed_and_restart_does_not_replay(self):
        class Fake:
            calls = 0
            def call(self, method, params):
                self.calls += 1
                if self.calls <= 2:
                    return [{'signature': 'seed', 'slot': 1}]
                return []
        rpc = Fake()
        Feed(self.l, rpc).poll(100)
        self.assertEqual(self.l.db.execute('SELECT count(*) FROM seen').fetchone()[0], 0)
        self.assertEqual(self.l.get('cursor:' + WALLET)['signature'], 'seed')
        self.l.db.close()
        self.l = Ledger(self.path, self.c, self.w)
        Feed(self.l, rpc).poll(101)
        self.assertEqual(self.l.db.execute('SELECT count(*) FROM events').fetchone()[0], 0)

class Parser(unittest.TestCase):
    def tx(self, native=False):
        mint = 'fixture-mint'
        def b(index, mint, amount, decimals=6):
            return dict(accountIndex=index, owner=WALLET, mint=mint, programId=TOKEN, uiTokenAmount={'amount': str(amount), 'decimals': decimals})
        pre = [b(1, mint, 0), b(2, USDC, 25000000)]
        post = [b(1, mint, 1000000), b(2, USDC, 24000000)]
        meta = dict(err=None, fee=5000, preBalances=[2000000000, 2000000, 2000000], postBalances=[1999995000, 2000000, 2000000], preTokenBalances=pre, postTokenBalances=post, logMessages=['Program log: Instruction: Route'], innerInstructions=[])
        return dict(blockTime=100, slot=1000, meta=meta, transaction={'message': {'accountKeys': [{'pubkey': WALLET, 'signer': True}, {'pubkey': 'ata1'}, {'pubkey': 'ata2'}], 'instructions': [{'programId': JUPITER}]}})
    def norm(self, tx):
        return normalize(tx, WALLET, 'sig', 102)
    def test_routed_buy_and_integer_quantity(self):
        e, reason = self.norm(self.tx())
        self.assertEqual(e['side'], 'buy')
        self.assertEqual(e['qty_raw'], 1000000)
        self.assertEqual(e['source_price'], '1')
    def test_airdrop_not_buy(self):
        tx = self.tx(); tx['transaction']['message']['instructions'] = []
        self.assertIsNone(self.norm(tx)[0])
    def test_airdrop_plus_swap_outer_transfer_rejected(self):
        tx = self.tx(); tx['transaction']['message']['instructions'].append({'program':'spl-token','parsed':{'type':'transfer','info':{}}})
        self.assertEqual(self.norm(tx)[1], 'external_transfer_or_unsupported_setup')
    def test_failed_ignored(self):
        tx = self.tx(); tx['meta']['err'] = {'InstructionError': [1, 'x']}
        self.assertEqual(self.norm(tx)[1], 'failed_transaction')
    def test_sol_rent_recovery(self):
        tx = self.tx()
        tx['meta']['postTokenBalances'][1]['uiTokenAmount']['amount'] = '25000000'
        tx['meta']['preBalances'][1] = 0
        tx['meta']['postBalances'][0] = 1897995000  # -0.1 SOL swap -0.002 rent -fee
        e, reason = self.norm(tx)
        self.assertEqual(e['price_currency'], 'SOL')
        self.assertEqual(D(e['source_price']), D('0.1'))
    def test_wrapped_sol_no_double_count(self):
        tx = self.tx()
        for name, amount in [('preTokenBalances', '1000000000'), ('postTokenBalances', '900000000')]:
            tx['meta'][name][1].update(mint=SOL, uiTokenAmount={'amount': amount, 'decimals':9})
        tx['meta']['preBalances'][2] = 1002000000
        tx['meta']['postBalances'][2] = 902000000
        e, reason = self.norm(tx)
        self.assertEqual(D(e['consideration']), D('0.1'))
    def test_partial_sell_source_fraction_data(self):
        tx = self.tx()
        tx['meta']['preTokenBalances'], tx['meta']['postTokenBalances'] = tx['meta']['postTokenBalances'], tx['meta']['preTokenBalances']
        e, _ = self.norm(tx)
        self.assertEqual(e['side'], 'sell')
        self.assertEqual(e['pre_qty_raw'], 1000000)
    def test_token2022_rejected(self):
        tx = self.tx(); tx['meta']['postTokenBalances'][0]['programId'] = 'Token2022'
        self.assertEqual(self.norm(tx)[1], 'unsupported_token_program')
    def test_multi_asset_rejected(self):
        tx = self.tx(); extra = copy.deepcopy(tx['meta']['postTokenBalances'][0]); extra['mint'] = 'extra'; tx['meta']['postTokenBalances'].append(extra)
        self.assertEqual(self.norm(tx)[1], 'ambiguous_multi_asset_swap')

if __name__ == '__main__':
    unittest.main()
