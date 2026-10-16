"""Read-only Solana polling and deliberately narrow swap normalization."""
import json
import time
import urllib.request
import urllib.parse
from decimal import Decimal as D
from core import USDC, SOL, TOKEN, JUPITER

class Rpc:
    def __init__(self, url):
        if not url.startswith('https://'):
            raise ValueError('HTTPS required')
        self.url = url
    def call(self, method, params=None):
        if method not in {'getHealth', 'getSignaturesForAddress', 'getTransaction', 'getAccountInfo', 'getTokenLargestAccounts', 'getTokenSupply'}:
            raise ValueError('Read-only method allowlist')
        req = urllib.request.Request(self.url, json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or []}).encode(), {'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.load(r)
        if data.get('error'):
            raise RuntimeError('RPC error')  # Never log credential-bearing endpoint/error bodies.
        return data['result']

def normalize(tx, wallet, signature, detected):
    """Support one economic asset exchanged against USDC or SOL via Jupiter.

    Routed intermediate balances are netted. Reject ambiguous multi-asset activity,
    unsupported programs and external transfers rather than manufacturing buys.
    Native SOL includes owner token-account lamports, cancelling rent/WSOL setup.
    """
    if not tx or tx.get('blockTime') is None:
        return None, 'missing_transaction_or_time'
    meta = tx.get('meta') or {}
    if meta.get('err') is not None:
        return None, 'failed_transaction'
    msg = tx['transaction']['message']
    keys = msg['accountKeys']
    if not keys or not isinstance(keys[0], dict) or keys[0]['pubkey'] != wallet or not keys[0].get('signer'):
        return None, 'unsupported_nonpayer_or_nonsigner'
    instructions = msg.get('instructions', [])
    swaps = [i for i, x in enumerate(instructions) if x.get('programId') == JUPITER]
    if len(swaps) != 1:
        return None, 'not_single_supported_swap'
    # Require successful program-specific instruction evidence, not a mere address mention.
    logs = meta.get('logMessages') or []
    if not any(x in ('Program log: Instruction: Route', 'Program log: Instruction: SharedAccountsRoute',
                     'Program log: Instruction: ExactOutRoute', 'Program log: Instruction: SharedAccountsExactOutRoute') for x in logs):
        return None, 'unsupported_swap_instruction'
    pre, post, decimals, owned = {}, {}, {}, set()
    for name, target in [('preTokenBalances', pre), ('postTokenBalances', post)]:
        if name not in meta:
            return None, 'missing_token_balances'
        for b in meta[name]:
            if b.get('owner') != wallet:
                continue
            if b.get('programId') != TOKEN:
                return None, 'unsupported_token_program'
            mint, amount = b['mint'], b['uiTokenAmount']
            if mint in decimals and decimals[mint] != amount['decimals']:
                return None, 'inconsistent_decimals'
            decimals[mint] = amount['decimals']
            target[mint] = target.get(mint, 0) + int(amount['amount'])
            owned.add(b['accountIndex'])
    pubkeys = [x['pubkey'] for x in keys]
    owned_keys = {pubkeys[i] for i in owned}
    allowed_setup = {'createAccount', 'createAccountWithSeed', 'initializeAccount', 'initializeAccount2', 'initializeAccount3', 'syncNative', 'closeAccount', 'create', 'createIdempotent'}
    # Outer instructions may only set up accounts/compute budget; transfers/airdrops
    # outside the one swap subtree could otherwise contaminate balance deltas.
    outside = [x for i, x in enumerate(instructions) if i not in swaps]
    outside += [x for group in meta.get('innerInstructions', []) if group['index'] not in swaps for x in group['instructions']]
    for x in outside:
        if x.get('programId') == 'ComputeBudget111111111111111111111111111111':
            continue
        p = x.get('parsed')
        if not isinstance(p, dict):
            return None, 'ambiguous_outer_instruction'
        typ, info = p.get('type'), p.get('info', {})
        if typ == 'transfer' and x.get('program') == 'system' and info.get('source') == wallet and info.get('destination') in owned_keys:
            continue  # Native SOL wrapping: cancelled by owner-account lamports below.
        if typ not in allowed_setup:
            return None, 'external_transfer_or_unsupported_setup'
        if typ == 'closeAccount' and (info.get('account') not in owned_keys or info.get('destination') != wallet):
            return None, 'ambiguous_account_close'
    delta = {m: post.get(m, 0) - pre.get(m, 0) for m in pre.keys() | post.keys()}
    assets = [m for m, qty in delta.items() if qty and m not in (USDC, SOL)]
    if len(assets) != 1:
        return None, 'ambiguous_multi_asset_swap'
    mint = assets[0]
    qty = delta[mint]
    cash = D(delta.get(USDC, 0)) / 1000000
    # Include rent balances of ALL owned token accounts, plus fee paid by wallet.
    native = (D(meta['postBalances'][0]) - D(meta['preBalances'][0]) + D(meta['fee']) +
              sum((D(meta['postBalances'][i]) - D(meta['preBalances'][i]) for i in owned), D(0))) / 1000000000
    if cash and abs(native) > D('0.000001'):
        return None, 'multiple_considerations'
    consideration, currency = (cash, 'USDC') if cash else (native, 'SOL')
    if not consideration or (consideration > 0) == (qty > 0):
        return None, 'no_recoverable_swap_consideration'
    return {'id': signature + ':' + str(swaps[0]) + ':' + wallet + ':' + mint,
            'signature': signature, 'slot': tx['slot'], 'wallet': wallet, 'mint': mint,
            'side': 'buy' if qty > 0 else 'sell', 'qty_raw': abs(qty),
            'pre_qty_raw': pre.get(mint, 0), 'decimals': decimals[mint],
            'consideration': str(abs(consideration)), 'price_currency': currency,
            'source_price': str(abs(consideration) / (D(abs(qty)) / (10 ** decimals[mint]))),
            'tx_time': tx['blockTime'], 'detected': detected, 'confirmation': 'confirmed',
            'parser': 'single-jupiter-economic-delta-v1'}, 'supported_swap'

class Feed:
    def __init__(self, ledger, rpc):
        self.l, self.rpc = ledger, rpc
    def poll(self, now=None):
        now = time.time() if now is None else now
        l = self.l
        for w in l.w['wallets']:
            wallet = w['address']
            cursor = l.get('cursor:' + wallet)
            if cursor is None:
                rows = self.rpc.call('getSignaturesForAddress', [wallet, {'limit': 1, 'commitment': 'confirmed'}])
                with l.db:
                    l.set('cursor:' + wallet, {'signature': rows[0]['signature'] if rows else None, 'seeded': now})
                    l.log('cursor_seed_no_replay', {'wallet': wallet, 'head': rows[0]['signature'] if rows else None}, now)
                continue
            # Durable pagination: stage each page before cursor advances. Up to 1000
            # signatures per poll, resumable across disconnects; no silent truncation.
            pending = l.get('pagination:' + wallet) or {'before': None, 'head': None, 'detected': now}
            options = {'limit': 100, 'commitment': 'confirmed'}
            if pending['before']:
                options['before'] = pending['before']
            rows = self.rpc.call('getSignaturesForAddress', [wallet, options])
            page_full = len(rows) == 100
            boundary = next((i for i, r in enumerate(rows) if r['signature'] == cursor['signature']), None)
            reached = boundary is not None or cursor['signature'] is None
            if boundary is not None:
                rows = rows[:boundary]
            with l.db:
                if rows and not pending['head']:
                    pending['head'] = rows[0]['signature']
                for r in rows:
                    l.db.execute('INSERT OR IGNORE INTO seen VALUES(?,?,?,?,?,?,?)',
                                 (wallet, r['signature'], r['slot'], r.get('blockTime'), now,
                                  'failed' if r.get('err') is not None else 'pending', json.dumps(r)))
                if page_full and not reached:
                    pending['before'] = rows[-1]['signature']
                    l.set('pagination:' + wallet, pending)
                    l.log('catchup_in_progress', {'wallet': wallet, 'oldest_time': rows[-1].get('blockTime')}, now)
                elif reached:
                    if pending['head']:
                        l.set('cursor:' + wallet, {'signature': pending['head'], 'seeded': cursor['seeded']})
                    l.db.execute('DELETE FROM state WHERE key=?', ('pagination:' + wallet,))
                    l.set('gap:' + wallet, None)
                else:
                    l.set('gap:' + wallet, {'time': now, 'reason': 'cursor_not_found_in_provider_history'})
                    l.log('feed_gap_blocked', {'wallet': wallet}, now)
            # Do not process newer pages ahead of older events while catching up.
            if not reached:
                continue
            for r in l.db.execute("SELECT * FROM seen WHERE wallet=? AND status='pending' ORDER BY slot,signature LIMIT 20", (wallet,)).fetchall():
                tx = self.rpc.call('getTransaction', [r['signature'], {'encoding': 'jsonParsed', 'commitment': 'confirmed', 'maxSupportedTransactionVersion': 0}])
                if tx is None:
                    with l.db:
                        l.log('transaction_gap_retry', {'signature': r['signature'], 'wallet': wallet}, now)
                    break  # Preserve order: do not trade later events across a missing tx.
                e, reason = normalize(tx, wallet, r['signature'], r['detected'])
                if e:
                    # Atomic event insertion + raw-transaction acknowledgement.
                    with l.db:
                        l.db.execute('INSERT OR IGNORE INTO events VALUES(?,?,?,?,?,?,NULL,?)', (e['id'], wallet, e['mint'], e['side'], e['tx_time'], e['detected'], json.dumps(e)))
                        l.db.execute('UPDATE seen SET status=? WHERE wallet=? AND signature=?', (reason, wallet, r['signature']))
                else:
                    with l.db:
                        l.db.execute('UPDATE seen SET status=? WHERE wallet=? AND signature=?', (reason, wallet, r['signature']))
                        l.log('non_signal', {'wallet': wallet, 'signature': r['signature'], 'reason': reason}, now)

class Quotes:
    """Optional authorized free Metis-compatible GET API. Disabled by default.

    No hidden key lookup, signup, swap POST or paid API fallback. Endpoint access
    must be explicitly configured by the owner before use. API V1 is deprecated.
    """
    def __init__(self, config):
        self.c = config
    def request(self, a, b, amount):
        if not self.c['quote_access_authorized_free'] or not self.c['quote_url']:
            return None
        url = self.c['quote_url']
        if not url.startswith('https://') or '?' in url or '@' in url:
            raise ValueError('Public HTTPS quote endpoint without credentials required')
        query = urllib.parse.urlencode({'inputMint': a, 'outputMint': b, 'amount': amount,
                                       'slippageBps': self.c['slippage_bps'], 'restrictIntermediateTokens': 'true'})
        with urllib.request.urlopen(url + '?' + query, timeout=5) as r:
            q = json.load(r)
        if (q.get('inputMint') != a or q.get('outputMint') != b or int(q.get('inAmount', 0)) != amount
                or q.get('swapMode') != 'ExactIn' or not q.get('routePlan')):
            return None
        return q
    def __call__(self, mint, side, amount, now):
        try:
            a, b = (USDC, mint) if side == 'buy' else (mint, USDC)
            q = self.request(a, b, amount)
            if not q:
                return None
            out, minimum = int(q['outAmount']), int(q['otherAmountThreshold'])
            # Validate provider threshold against our frozen slippage floor.
            if not 0 < minimum <= out or minimum < out * (10000 - self.c['slippage_bps']) // 10000:
                return None
            sol = self.request(SOL, USDC, 1000000000)
            return {'mint': mint, 'side': side, 'input_raw': amount, 'min_output_raw': minimum,
                    'obtained': time.time(), 'provider': 'owner-authorized-free-metis-compatible-api',
                    'fidelity': 'size_specific_quote', 'embedded_fees_in_output': True,
                    'external_cost_usd': self.c['network_priority_rent_usd'],
                    'price_impact': q['priceImpactPct'], 'raw_quote': q,
                    'sol_usd': str(D(sol['outAmount']) / 1000000) if sol else None}
        except Exception:
            return None

class Risk:
    def __init__(self, rpc):
        self.rpc = rpc
    def __call__(self, mint, now):
        result = {'obtained': time.time(), 'provider': 'solana-rpc+public-rugcheck',
                  'holder_concentration': 'unknown', 'bundling': 'unknown', 'linked_wallets': 'unknown', 'creator_history': 'unknown'}
        try:
            a = self.rpc.call('getAccountInfo', [mint, {'encoding': 'jsonParsed', 'commitment': 'confirmed'}])['value']
            if not a:
                return result
            info = a['data']['parsed']['info']
            result.update(classic_token_program=a['owner'] == TOKEN,
                          mint_authority_revoked=info.get('mintAuthority', 'unknown') is None,
                          freeze_authority_revoked=info.get('freezeAuthority', 'unknown') is None,
                          no_transfer_restrictions=a['owner'] == TOKEN)
            with urllib.request.urlopen('https://api.rugcheck.xyz/v1/tokens/' + mint + '/report', timeout=5) as r:
                report = json.load(r)
            if report.get('mint') != mint:
                return result
            result['provider_report'] = report
            # Absence of flags is not a guarantee: this only means no current
            # provider alert, and provider coverage is recorded explicitly.
            if isinstance(report.get('risks'), list) and isinstance(report.get('rugged'), bool):
                result['no_scam_alerts'] = not report['rugged'] and not any(x.get('level') == 'danger' for x in report['risks'])
            result.update(holder_concentration=report.get('topHolders', 'unknown'),
                          bundling=report.get('insiderNetworks', 'unknown'),
                          linked_wallets=report.get('knownAccounts', 'unknown'),
                          creator_history=report.get('creatorTokens', 'unknown'))
            result['obtained'] = time.time()
        except Exception:
            result['coverage'] = 'partial_or_unavailable'
        return result
