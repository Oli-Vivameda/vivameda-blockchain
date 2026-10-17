"""Desk-only pure primitives; no network, wallet, signer or transaction APIs."""
import hashlib
import json
import math
from decimal import Decimal as D

MANDATORY = ('token_controls', 'liquidity_control', 'trading_mechanics')
REGIMES = ('CONTINUATION', 'COMPRESSION', 'RECLAIM', 'OTHER')
PLANS = {'A': ('0.40', '0.25', 45), 'B': ('0.25', '0.20', 30), 'C': ('1.00', '0.35', 120)}
PREREG_COMMIT = '376c3fed540e89aeee8d8d26c2ce18636c409acf'
PROTOCOL_SHA256 = '62c4b3e4b13dbc97a3c973cf22b9fb40eb78a2e006c315e20abd8df92b5195a2'

def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':'), allow_nan=False, default=str)

def digest(x):
    return hashlib.sha256(canonical(x).encode()).hexdigest()

def finite(x):
    return type(x) in (int, float) and math.isfinite(x)

def positive(x):
    try:
        d = D(str(x))
        if not d.is_finite() or d <= 0:
            raise ValueError('nonpositive_or_nonfinite')
        return d
    except Exception as exc:
        raise ValueError('nonpositive_or_nonfinite') from exc

def screening(review, mint, pair, at):
    """Fresh evidence at the decision time; background UNKNOWNs stay visible."""
    if not isinstance(review, dict) or review.get('mint') != mint or review.get('chain') != 'solana' or not pair or review.get('pair') != pair:
        return False, {}, 'screening_identity'
    stamp = review.get('checked_at')
    if not finite(stamp) or not 0 <= at - stamp <= 300:
        return False, {}, 'screening_stale'
    checks = review.get('checks', {})
    if not isinstance(checks, dict):
        return False, {}, 'screening_shape'
    out = {}
    for key, item in checks.items():
        if not isinstance(item, dict):
            out[key] = 'UNKNOWN'; continue
        status, ts, refs = item.get('status'), item.get('observed_at'), item.get('evidence_refs')
        if status == 'REJECT':
            return False, {key: 'REJECT'}, 'screening_reject'
        valid = finite(ts) and 0 <= at - ts <= 300 and isinstance(refs, list) and bool(refs) and all(isinstance(r, str) and r.strip() for r in refs)
        out[key] = status if valid and status in ('PASS', 'REJECT') else 'UNKNOWN'
    ok = all(out.get(k) == 'PASS' for k in MANDATORY)
    return ok, out, 'eligible' if ok else 'mandatory_unknown'

def buy(x, y, dollars=D(10)):
    return positive(x) * positive(dollars) / (positive(y) + positive(dollars))

def sell(x, y, qty):
    return positive(y) * positive(qty) / (positive(x) + positive(qty))
