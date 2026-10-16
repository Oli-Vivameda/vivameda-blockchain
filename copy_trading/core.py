"""Paper accounting only. No transaction construction, signing or sending."""
import hashlib
import json
import sqlite3
import time
from decimal import Decimal as D, ROUND_DOWN

USDC = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
SOL = 'So11111111111111111111111111111111111111112'
TOKEN = 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
JUPITER = 'JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4'

def dumps(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':'), default=str)

def digest(x):
    return hashlib.sha256(dumps(x).encode()).hexdigest()

def validate(c, w):
    assert c['paper_only'] is True, 'Only paper mode exists'
    for k in ['starting_cash', 'max_buy', 'token_cap', 'total_cap', 'drawdown_pause']:
        assert D(c[k]) > 0
    assert 0 < D(c['drawdown_pause']) < 1
    assert 0 <= c['slippage_bps'] < 10000
    assert c['execution_delay_s'] >= 0 and c['max_signal_age_s'] > 0
    assert c['quote_max_age_s'] > 0 and c['risk_max_age_s'] > 0
    assert D(c['network_priority_rent_usd']) > 0
    b = c['strategy_b']
    if b['enabled']:
        assert b.get('frozen_at') and all(b.get(k) and D(str(b[k])) > 0 for k in ['take_profit', 'stop_loss', 'max_hold_s'])
    assert w['frozen_at'] and w['version'] and c['frozen_at']
    for wallet in w['wallets']:
        assert wallet['chain'] == 'solana' and wallet['verified'] is True
        assert wallet['primary_attribution'] and wallet['purchase_evidence'] and wallet['copy_suitability']
        assert len(wallet['address']) >= 32
    assert len({x['address'] for x in w['wallets']}) == len(w['wallets'])

class Ledger:
    def __init__(self, path, config, watchlist):
        validate(config, watchlist)
        self.c, self.w = config, watchlist
        self.live_clock = False
        self.db = sqlite3.connect(path, timeout=15)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS versions(kind TEXT, hash TEXT, data TEXT, PRIMARY KEY(kind,hash));
        CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY, data TEXT);
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, wallet TEXT, mint TEXT, side TEXT, tx_time REAL, detected REAL, processed REAL, data TEXT);
        CREATE TABLE IF NOT EXISTS decisions(event TEXT, strategy TEXT, reason TEXT, time REAL, data TEXT, PRIMARY KEY(event,strategy));
        CREATE TABLE IF NOT EXISTS accounts(strategy TEXT PRIMARY KEY, cash TEXT, peak TEXT, paused INTEGER);
        CREATE TABLE IF NOT EXISTS positions(strategy TEXT,wallet TEXT,mint TEXT,qty TEXT,cost TEXT,opened REAL,decimals INTEGER,mark TEXT,mark_time REAL,PRIMARY KEY(strategy,wallet,mint));
        CREATE TABLE IF NOT EXISTS fills(id INTEGER PRIMARY KEY,event TEXT,strategy TEXT,wallet TEXT,mint TEXT,side TEXT,qty TEXT,usd TEXT,costs TEXT,pnl TEXT,time REAL,quote TEXT);
        CREATE TABLE IF NOT EXISTS observations(id INTEGER PRIMARY KEY,time REAL,kind TEXT,data TEXT);
        CREATE TABLE IF NOT EXISTS seen(wallet TEXT,signature TEXT,slot INTEGER,tx_time REAL,detected REAL,status TEXT,data TEXT,PRIMARY KEY(wallet,signature));
        ''')
        with self.db:
            old = self.get('binding')
            binding = {'config': digest(config), 'watchlist': digest(watchlist)}
            if old and old != binding:
                raise ValueError('Frozen binding changed: use a NEW experiment database; bankroll migration is not automatic')
            self.set('binding', binding)
            for kind, data in [('config', config), ('watchlist', watchlist)]:
                self.db.execute('INSERT OR IGNORE INTO versions VALUES(?,?,?)', (kind, digest(data), dumps(data)))
            for s in ['A', 'B']:
                self.db.execute('INSERT OR IGNORE INTO accounts VALUES(?,?,?,0)', (s, config['starting_cash'], config['starting_cash']))

    def get(self, key):
        r = self.db.execute('SELECT data FROM state WHERE key=?', (key,)).fetchone()
        return json.loads(r[0]) if r else None

    def set(self, key, data):
        self.db.execute('INSERT OR REPLACE INTO state VALUES(?,?)', (key, dumps(data)))

    def log(self, kind, data, now=None):
        self.db.execute('INSERT INTO observations(time,kind,data) VALUES(?,?,?)', (time.time() if now is None else now, kind, dumps(data)))

    def observe(self, e):
        """Only normalized, supported swaps belong here; raw rejected tx remain in seen."""
        assert e['side'] in ('buy', 'sell') and e['confirmation'] == 'confirmed'
        assert e['wallet'] in {x['address'] for x in self.w['wallets']}
        assert int(e['qty_raw']) > 0 and e['decimals'] >= 0
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO events VALUES(?,?,?,?,?,?,NULL,?)',
                            (e['id'], e['wallet'], e['mint'], e['side'], e['tx_time'], e['detected'], dumps(e)))

    def positions(self, s):
        return [dict(x) for x in self.db.execute('SELECT * FROM positions WHERE strategy=?', (s,))]

    def equity(self, s, now):
        cash = D(self.db.execute('SELECT cash FROM accounts WHERE strategy=?', (s,)).fetchone()[0])
        # Missing/stale executable liquidation estimates are valued at zero, never carried at cost.
        return cash + sum((max(D(0), D(p['mark'])) for p in self.positions(s)
                           if p['mark'] is not None and now - p['mark_time'] <= self.c['quote_max_age_s']), D(0))

    def pause_check(self, s, now):
        a = self.db.execute('SELECT * FROM accounts WHERE strategy=?', (s,)).fetchone()
        equity = self.equity(s, now)
        peak = max(D(a['peak']), equity)
        paused = a['paused'] or equity <= peak * (1 - D(self.c['drawdown_pause']))
        self.db.execute('UPDATE accounts SET peak=?,paused=? WHERE strategy=?', (str(peak), int(paused), s))
        self.set('max_drawdown:' + s, str(max(D(self.get('max_drawdown:' + s) or 0), 1 - equity / peak)))
        for w in self.w['wallets']:
            key = s + ':' + w['address']
            value = self.wallet_value(s, w['address'], now)
            wallet_peak = max(D(self.get('wallet_peak:' + key) or self.c['starting_cash']), value)
            self.set('wallet_peak:' + key, str(wallet_peak))
            self.set('wallet_max_drawdown:' + key, str(max(D(self.get('wallet_max_drawdown:' + key) or 0), 1 - value / wallet_peak)))
        if paused and not a['paused']:
            self.log('drawdown_pause', {'strategy': s, 'equity': equity, 'peak': peak}, now)
        return paused

    def valid_quote(self, q, mint, side, amount, not_before, now):
        if not q or q.get('fidelity') != 'size_specific_quote':
            return False
        try:
            return (q['mint'] == mint and q['side'] == side and int(q['input_raw']) == int(amount)
                    and not_before <= q['obtained'] <= now and now - q['obtained'] <= self.c['quote_max_age_s']
                    and int(q['min_output_raw']) > 0 and D(q['external_cost_usd']) >= 0
                    and q['provider'] and q['embedded_fees_in_output'] is True
                    and 0 <= D(q['price_impact']) <= D(self.c['max_price_impact']))
        except (KeyError, ValueError, TypeError):
            return False

    def decide(self, e, s, provider, risk, now):
        c = self.c
        reason, data = 'unknown', {}
        p = next((x for x in self.positions(s) if x['wallet'] == e['wallet'] and x['mint'] == e['mint']), None)
        def done(r, extra=None):
            self.db.execute('INSERT INTO decisions VALUES(?,?,?,?,?)', (e['id'], s, r, now, dumps(extra or data)))
            return r
        if s == 'B' and not c['strategy_b']['enabled']:
            return done('strategy_disabled')
        if e['side'] == 'sell':
            if s == 'B':
                return done('own_exit_strategy')
            if not p:
                return done('no_bought_inventory')
            pre = int(e.get('pre_qty_raw') or 0)
            if pre <= 0 or int(e['qty_raw']) > pre:
                return done('unknown_source_sale_fraction')
            amount = int(D(p['qty']) * D(e['qty_raw']) / D(pre))
            data['requested_raw'] = amount
            newer_fill = self.db.execute('SELECT 1 FROM fills f JOIN events e2 ON f.event=e2.id WHERE f.strategy=? AND f.wallet=? AND f.mint=? AND e2.tx_time>?', (s, e['wallet'], e['mint'], e['tx_time'])).fetchone()
            if newer_fill:
                return done('out_of_order_sale')
            return self.exit(e, s, p, amount, provider, now, done)
        # Buy decisions are terminal; failed sells remain visible and retry separately.
        if now < e['tx_time'] or now - e['tx_time'] > c['max_signal_age_s']:
            return done('stale_or_future_signal')
        latest = self.db.execute('SELECT max(tx_time) FROM events WHERE wallet=? AND mint=? AND tx_time>?',
                                 (e['wallet'], e['mint'], e['tx_time'])).fetchone()[0]
        if latest is not None:
            return done('superseded_out_of_order_entry')
        if self.pause_check(s, now):
            return done('entries_paused')
        pos = self.positions(s)
        if any(x['mint'] == e['mint'] for x in pos):
            return done('existing_token_no_repeat')
        if len({x['mint'] for x in pos}) >= c['max_tokens']:
            return done('max_tokens')
        cash = D(self.db.execute('SELECT cash FROM accounts WHERE strategy=?', (s,)).fetchone()[0])
        budget = min(D(c['max_buy']), D(c['token_cap']), D(c['total_cap']) - sum((D(x['cost']) for x in pos), D(0)), cash)
        fee = D(c['network_priority_rent_usd'])
        amount = int(((budget - fee) * 1000000).to_integral_value(rounding=ROUND_DOWN))
        if amount <= 0:
            return done('exposure_or_cash_cap')
        source_price = e.get('source_price')
        if not source_price or D(source_price) <= 0 or e.get('price_currency') not in ('USDC', 'SOL'):
            return done('missing_reliable_source_price')
        evidence = risk(e['mint'], now)
        now = time.time() if self.live_clock else now
        data['risk'] = evidence
        self.log('risk', data, now)
        if (not evidence or not 0 <= now - evidence.get('obtained', -1e12) <= c['risk_max_age_s']
                or any(evidence.get(k) is not True for k in c['blocking_risk_fields'])):
            return done('risk_block_or_unknown')
        q = provider(e['mint'], 'buy', amount, now)
        now = time.time() if self.live_clock else now
        if now - e['tx_time'] > c['max_signal_age_s']:
            return done('stale_after_provider_delay')
        data['quote'] = q
        self.log('quote_attempt', data, now)
        if not self.valid_quote(q, e['mint'], 'buy', amount, e['detected'] + c['execution_delay_s'], now):
            return done('missing_or_invalid_quote')
        out = int(q['min_output_raw'])
        usd = D(amount) / 1000000 + D(q['external_cost_usd'])
        if usd > budget:
            return done('all_in_cost_cap')
        price = (D(amount) / 1000000) / (D(out) / (10 ** e['decimals']))
        if e['price_currency'] == 'SOL':
            if not q.get('sol_usd') or D(q['sol_usd']) <= 0:
                return done('missing_sol_conversion')
            price /= D(q['sol_usd'])
        if price > D(source_price) * (1 + D(c['max_chase'])):
            return done('price_chase')
        reverse = provider(e['mint'], 'sell', out, now)
        now = time.time() if self.live_clock else now
        data['initial_sellability_quote'] = reverse
        if now - e['tx_time'] > c['max_signal_age_s']:
            return done('stale_after_provider_delay')
        if now - evidence['obtained'] > c['risk_max_age_s']:
            return done('stale_risk_after_provider_delay')
        if not self.valid_quote(reverse, e['mint'], 'sell', out, e['detected'] + c['execution_delay_s'], now):
            return done('no_fresh_sellability_quote')
        if now - q['obtained'] > c['quote_max_age_s']:
            return done('buy_quote_expired_during_sellability_check')
        mark = max(D(0), D(reverse['min_output_raw']) / 1000000 - D(reverse['external_cost_usd']))
        self.db.execute('UPDATE accounts SET cash=? WHERE strategy=?', (str(cash - usd), s))
        self.db.execute('INSERT INTO positions VALUES(?,?,?,?,?,?,?,?,?)',
                        (s, e['wallet'], e['mint'], str(out), str(usd), now, e['decimals'], str(mark), reverse['obtained']))
        self.fill(e, s, 'buy', out, usd, q, D(0), now)
        return done('paper_buy_quote_estimate')

    def fill(self, e, s, side, qty, usd, quote, pnl, now):
        self.db.execute('INSERT INTO fills(event,strategy,wallet,mint,side,qty,usd,costs,pnl,time,quote) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                        (e['id'], s, e['wallet'], e['mint'], side, str(qty), str(usd), quote['external_cost_usd'], str(pnl), now, dumps(quote)))

    def exit(self, e, s, p, amount, provider, now, done):
        if amount <= 0:
            return done('rounding_dust')
        q = provider(e['mint'], 'sell', amount, now)
        now = time.time() if self.live_clock else now
        self.log('exit_quote_attempt', {'event': e['id'], 'strategy': s, 'quote': q}, now)
        if not self.valid_quote(q, e['mint'], 'sell', amount, e['detected'] + self.c['execution_delay_s'], now):
            return done('failed_exit_quote')
        proceeds = D(q['min_output_raw']) / 1000000 - D(q['external_cost_usd'])
        if proceeds < 0:
            return done('failed_exit_cost_exceeds_output')
        cost = D(p['cost']) * D(amount) / D(p['qty'])
        cash = D(self.db.execute('SELECT cash FROM accounts WHERE strategy=?', (s,)).fetchone()[0])
        self.db.execute('UPDATE accounts SET cash=? WHERE strategy=?', (str(cash + proceeds), s))
        if amount >= int(p['qty']):
            self.db.execute('DELETE FROM positions WHERE strategy=? AND wallet=? AND mint=?', (s, p['wallet'], p['mint']))
        else:
            # Invalidate old mark after partial size changes.
            self.db.execute('UPDATE positions SET qty=?,cost=?,mark=NULL,mark_time=NULL WHERE strategy=? AND wallet=? AND mint=?',
                            (str(int(p['qty']) - amount), str(D(p['cost']) - cost), s, p['wallet'], p['mint']))
        self.fill(e, s, 'sell', amount, proceeds, q, proceeds - cost, now)
        return done('paper_sell_quote_estimate')

    def process(self, provider, risk, now=None):
        self.live_clock = now is None
        now = time.time() if now is None else now
        rows = self.db.execute('SELECT data FROM events WHERE processed IS NULL AND detected<=? ORDER BY tx_time,id', (now - self.c['execution_delay_s'],)).fetchall()
        for row in rows:
            e = json.loads(row[0])
            for s in ['A', 'B']:
                with self.db:
                    if not self.db.execute('SELECT 1 FROM decisions WHERE event=? AND strategy=?', (e['id'], s)).fetchone():
                        self.decide(e, s, provider, risk, now)
            with self.db:
                self.db.execute('UPDATE events SET processed=? WHERE id=? AND processed IS NULL', (time.time() if self.live_clock else now, e['id']))

    def maintain(self, provider, now=None):
        self.live_clock = now is None
        now = time.time() if now is None else now
        for s in ['A', 'B']:
            if s == 'B' and not self.c['strategy_b']['enabled']:
                continue
            for p in self.positions(s):
                q = provider(p['mint'], 'sell', int(p['qty']), now)
                now = time.time() if self.live_clock else now
                with self.db:
                    valid = self.valid_quote(q, p['mint'], 'sell', int(p['qty']), p['opened'], now)
                    if valid:
                        mark = max(D(0), D(q['min_output_raw']) / 1000000 - D(q['external_cost_usd']))
                        self.db.execute('UPDATE positions SET mark=?,mark_time=? WHERE strategy=? AND wallet=? AND mint=?',
                                        (str(mark), q['obtained'], s, p['wallet'], p['mint']))
                    else:
                        self.log('stale_or_unsellable_position', {'strategy': s, 'wallet': p['wallet'], 'mint': p['mint']}, now)
                    if s == 'B':
                        b = self.c['strategy_b']
                        move = mark / D(p['cost']) - 1 if valid else None
                        trigger = ('max_hold' if now - p['opened'] >= b['max_hold_s'] else
                                   'take_profit' if move is not None and move >= D(b['take_profit']) else
                                   'stop_loss' if move is not None and move <= -D(b['stop_loss']) else None)
                        if trigger:
                            e = {'id': f'B:{p["wallet"]}:{p["mint"]}:{p["opened"]}:{now}', 'wallet': p['wallet'], 'mint': p['mint'], 'detected': now - self.c['execution_delay_s']}
                            self.exit(e, s, p, int(p['qty']), lambda *args: q, now,
                                      lambda r: self.log(r, {'strategy': s, 'trigger': trigger, 'event': e['id']}, now))
            with self.db:
                self.pause_check(s, now)
        self.retry_failed_exits(provider, now)

    def retry_failed_exits(self, provider, now):
        # A failed exit is retried against the ORIGINAL requested quantity less subsequent fills.
        # Never recalculate a source fraction on remaining inventory and compound the sale.
        rows = self.db.execute("SELECT e.data,d.data FROM events e JOIN decisions d ON e.id=d.event WHERE d.strategy='A' AND d.reason IN ('failed_exit_quote','failed_exit_cost_exceeds_output')").fetchall()
        for row in rows:
            e = json.loads(row[0])
            p = next((p for p in self.positions('A') if p['wallet'] == e['wallet'] and p['mint'] == e['mint']), None)
            # Later source sales supersede failed intents, preventing over-exit on recovery.
            if not p or self.db.execute("SELECT 1 FROM events WHERE wallet=? AND mint=? AND side='sell' AND tx_time>?", (e['wallet'], e['mint'], e['tx_time'])).fetchone():
                with self.db:
                    self.db.execute("UPDATE decisions SET reason='failed_exit_superseded_review_required' WHERE event=? AND strategy='A'", (e['id'],))
                    self.log('failed_exit_superseded_review_required', {'event': e['id']}, now)
                continue
            previous = json.loads(row[1])
            amount = previous.get('requested_raw')
            if amount is None:
                # Stored by process before first attempt in current release.
                continue
            with self.db:
                def done(reason):
                    if reason == 'paper_sell_quote_estimate':
                        self.db.execute('UPDATE decisions SET reason=?,time=? WHERE event=? AND strategy=?', (reason, now, e['id'], 'A'))
                    return reason
                self.exit(e, 'A', p, min(int(amount), int(p['qty'])), provider, now, done)

    def closed_cycle_pnls(self, strategy, wallet=None):
        cycles, finished = {}, []
        for f in self.db.execute('SELECT * FROM fills WHERE strategy=? ORDER BY id', (strategy,)):
            if wallet is not None and f['wallet'] != wallet:
                continue
            key = (f['wallet'], f['mint'])
            qty, pnl = cycles.get(key, (0, D(0)))
            if f['side'] == 'buy':
                qty += int(f['qty'])
            else:
                qty -= int(f['qty'])
                pnl += D(f['pnl'])
            if qty == 0:
                finished.append(pnl)
                cycles.pop(key, None)
            else:
                cycles[key] = (qty, pnl)
        return finished

    def wallet_value(self, strategy, wallet, now):
        realized = sum((D(x[0]) for x in self.db.execute("SELECT pnl FROM fills WHERE strategy=? AND wallet=? AND side='sell'", (strategy, wallet))), D(0))
        positions = [p for p in self.positions(strategy) if p['wallet'] == wallet]
        cost = sum((D(p['cost']) for p in positions), D(0))
        marks = sum((D(p['mark']) for p in positions if p['mark'] is not None and now - p['mark_time'] <= self.c['quote_max_age_s']), D(0))
        return D(self.c['starting_cash']) + realized + marks - cost

    def report(self, now=None):
        now = time.time() if now is None else now
        out = {'status': 'WAITING_FOR_VERIFIED_WALLETS' if not self.w['wallets'] else 'PAPER_MONITORING',
               'fidelity': 'size-specific conservative quote estimates only; no confirmed fills', 'binding': self.get('binding'),
               'health': self.get('health'), 'strategies': {}}
        for s in ['A', 'B']:
            a = dict(self.db.execute('SELECT * FROM accounts WHERE strategy=?', (s,)).fetchone())
            equity = self.equity(s, now)
            sells = [dict(x) for x in self.db.execute("SELECT * FROM fills WHERE strategy=? AND side='sell'", (s,))]
            pnl = [D(x['pnl']) for x in sells]
            closed = self.closed_cycle_pnls(s)
            wins, losses = [x for x in closed if x > 0], [x for x in closed if x < 0]
            positions = self.positions(s)
            a.update(enabled=s == 'A' or self.c['strategy_b']['enabled'], equity=str(equity), net_return=str(equity / D(self.c['starting_cash']) - 1),
                     drawdown=str(1 - equity / D(a['peak'])), max_drawdown=self.get('max_drawdown:' + s) or '0', exposure=str(sum((D(p['cost']) for p in positions), D(0))), positions=positions,
                     realized_pnl=str(sum(pnl, D(0))), completed_exit_legs=len(sells), completed_trades=len(closed), win_rate=str(D(len(wins)) / len(closed)) if closed else None,
                     average_win=str(sum(wins) / len(wins)) if wins else None, average_loss=str(sum(losses) / len(losses)) if losses else None,
                     external_costs=str(sum((D(x[0]) for x in self.db.execute('SELECT costs FROM fills WHERE strategy=?', (s,))), D(0))),
                     skips=[dict(x) for x in self.db.execute('SELECT reason,count(*) AS count FROM decisions WHERE strategy=? GROUP BY reason', (s,))],
                     per_wallet=[dict(x) for x in self.db.execute('SELECT wallet,count(*) AS exit_legs FROM fills WHERE strategy=? AND side=\'sell\' GROUP BY wallet', (s,))],
                     sample_warning='SMALL SAMPLE; win statistics use fully closed source/token position cycles')
            out['strategies'][s] = a
        out['source_observations'] = [dict(x) for x in self.db.execute('SELECT wallet,side,count(*) AS events FROM events GROUP BY wallet,side')]
        out['source_performance_coverage'] = 'Observed supported swaps only; initial holdings and unsupported trades unknown. No source ROI inferred.'
        out['wallet_results'] = []
        for wallet in self.w['wallets']:
            for strategy in ['A', 'B']:
                fills = [dict(x) for x in self.db.execute('SELECT * FROM fills WHERE wallet=? AND strategy=?', (wallet['address'], strategy))]
                sells = [x for x in fills if x['side'] == 'sell']
                pnl = [D(x['pnl']) for x in sells]
                closed = self.closed_cycle_pnls(strategy, wallet['address'])
                wins, losses = [x for x in closed if x > 0], [x for x in closed if x < 0]
                positions = [p for p in self.positions(strategy) if p['wallet'] == wallet['address']]
                cost = sum((D(x['usd']) for x in fills if x['side'] == 'buy'), D(0))
                realized = sum(pnl, D(0))
                open_cost = sum((D(p['cost']) for p in positions), D(0))
                marks = sum((D(p['mark']) for p in positions if p['mark'] is not None and now - p['mark_time'] <= self.c['quote_max_age_s']), D(0))
                out['wallet_results'].append(dict(wallet=wallet['address'], strategy=strategy, realized_pnl=str(realized), net_pnl=str(realized + marks - open_cost), return_on_deployed_cost=str((realized + marks - open_cost) / cost) if cost else None, exposure=str(open_cost), completed_exit_legs=len(pnl), completed_trades=len(closed), win_rate=str(D(len(wins))/len(closed)) if closed else None, net_return_contribution=str((realized + marks - open_cost)/D(self.c['starting_cash'])), max_drawdown_contribution=self.get('wallet_max_drawdown:' + strategy + ':' + wallet['address']) or '0', average_win=str(sum(wins)/len(wins)) if wins else None, average_loss=str(sum(losses)/len(losses)) if losses else None, costs=str(sum((D(x['costs']) for x in fills), D(0))), skips=[dict(x) for x in self.db.execute('SELECT d.reason,count(*) AS count FROM decisions d JOIN events e ON d.event=e.id WHERE e.wallet=? AND d.strategy=? GROUP BY d.reason', (wallet['address'],strategy))]))
        out['latency_seconds'] = [dict(x) for x in self.db.execute('SELECT wallet, count(*) AS events,avg(detected-tx_time) AS mean,max(detected-tx_time) AS maximum FROM events GROUP BY wallet')]
        return out
