"""Authenticate captured Pump AMM RPC account relationships, never a boolean flag.

Decoder offsets reuse the Crypto Lab's reviewed protocol_screening.py pool layout.
No network calls or current-reserve historical backfill. Evidence is owner-supplied
raw RPC capture; references/timestamps are provenance, not cryptographic attestation.
"""
import base64
from decimal import Decimal as D
from common import positive, finite, digest
PUMP = 'pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA'
SPL = 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
SOL = 'So11111111111111111111111111111111111111112'
USDC = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def b58(raw):
    zero, n, s = len(raw) - len(raw.lstrip(b'\0')), int.from_bytes(raw, 'big'), ''
    while n:
        n, r = divmod(n, 58); s = ALPHABET[r] + s
    return '1' * zero + s

def info(a, kind):
    if not isinstance(a, dict) or a.get('owner') != SPL or a.get('executable'):
        raise ValueError('unsupported_token_program')
    parsed = a['data']['parsed']
    if parsed['type'] != kind:
        raise ValueError('account_kind')
    return parsed['info']

def authenticate(record, mint, pair, at, price, max_age=180):
    try:
        if record.get('mint') != mint or record.get('pair') != pair or record.get('chain') != 'solana':
            raise ValueError('reserve_identity')
        observed = record.get('observed_at')
        if not finite(observed) or not 0 <= at - observed <= max_age:
            raise ValueError('reserve_time')
        refs = record.get('evidence_refs')
        if not isinstance(refs, list) or not refs or not all(isinstance(x, str) and x.strip() for x in refs):
            raise ValueError('reserve_provenance')
        pr, ar = record['pool_response'], record['accounts_response']
        account = pr['value']
        if account['owner'] != PUMP or account.get('executable'):
            raise ValueError('pool_program')
        if account['data'][1] != 'base64':
            raise ValueError('pool_encoding')
        raw = base64.b64decode(account['data'][0], validate=True)
        if len(raw) != 271 or raw[:8] != bytes([241,154,109,4,17,177,109,188]):
            raise ValueError('unsupported_pool_layout')
        if raw[243] != 0 or int.from_bytes(raw[245:261], 'little', signed=True) != 0:
            raise ValueError('nonconstant_product_or_mayhem')
        addresses = [b58(raw[11+32*i:43+32*i]) for i in range(6)]
        _, base_mint, quote_mint, lp_mint, base_vault, quote_vault = addresses
        if base_mint != mint or quote_mint not in (SOL, USDC):
            raise ValueError('unsupported_pool_mints')
        # Address order is captured explicitly; a valid unrelated account list is insufficient.
        if record['account_addresses'] != [mint, lp_mint, base_vault, quote_vault]:
            raise ValueError('vault_address_binding')
        if record['pool_address'] != pair:
            raise ValueError('pool_address_binding')
        if not isinstance(pr['context']['slot'], int) or ar['context']['slot'] < pr['context']['slot']:
            raise ValueError('slot_order')
        ma, la, ba, qa = ar['value']
        mi, li = info(ma, 'mint'), info(la, 'mint')
        if not mi.get('isInitialized') or li.get('mintAuthority') != pair or li.get('freezeAuthority') is not None:
            raise ValueError('mint_or_lp_authentication')
        bi, qi = info(ba, 'account'), info(qa, 'account')
        for i, m in [(bi, mint), (qi, quote_mint)]:
            if i['mint'] != m or i['owner'] != pair or i['state'] != 'initialized' or i.get('delegate') or i.get('closeAuthority'):
                raise ValueError('vault_relationship')
        if bi['tokenAmount']['decimals'] != mi['decimals'] or qi['tokenAmount']['decimals'] != (9 if quote_mint == SOL else 6):
            raise ValueError('decimals_mismatch')
        x = positive(bi['tokenAmount']['amount']) / 10 ** mi['decimals']
        q = positive(qi['tokenAmount']['amount']) / 10 ** qi['tokenAmount']['decimals']
        usd = record['quote_usd']
        if (not finite(usd.get('observed_at')) or not 0 <= at-usd['observed_at'] <= max_age
                or not isinstance(usd.get('evidence_refs'), list) or not usd['evidence_refs']):
            raise ValueError('usd_conversion_provenance')
        y = q * positive(usd['price'])
        if abs(y / x / positive(price) - 1) > D('0.03'):
            raise ValueError('reserve_price_mismatch')
        return {'x': str(x), 'y': str(y), 'observed_at': observed, 'proof_hash': digest(record), 'evidence_refs': refs, 'pool': pair}
    except (KeyError, TypeError, IndexError, ValueError, AttributeError) as exc:
        raise ValueError('unauthenticated_reserves:' + str(exc)) from exc

def select(records, mint, pair, at, price, max_age=180):
    # Choose latest contemporaneous capture; never fall back to stale/future or
    # older favourable reserves if the latest proof is malformed.
    matches = [r for r in records if r.get('mint') == mint and r.get('pair') == pair and finite(r.get('observed_at')) and r['observed_at'] <= at]
    if not matches:
        raise ValueError('authenticated_reserves_missing')
    latest = max(r['observed_at'] for r in matches)
    matches = [r for r in matches if r['observed_at'] == latest]
    if len({digest(r) for r in matches}) != 1:
        raise ValueError('conflicting_reserve_capture')
    return authenticate(matches[0], mint, pair, at, price, max_age)
