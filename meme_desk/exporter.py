#!/usr/bin/env python3
"""Owner-only read-only, column-allowlisted scanner export; never opens outcomes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import urllib.parse
from common import canonical, PROTOCOL_SHA256, PREREG_COMMIT

SOURCE = '/opt/vivameda-crypto-early-scout/data/early_scout.sqlite'
COLUMNS = {
    'pl_predictions': {'mint'},
    'v2_cases': {'id','mint','decision_ts','source','score','regime'},
    'launches': {'mint','symbol','created_ts','pinned_pair'},
    'snapshots': {'mint','ts','pair','price','mc','liq'},
    'prealert_reviews': {'mint','checked_at','review'},
}

def authorizer(action, table, column, database, trigger):
    if action == sqlite3.SQLITE_READ:
        return sqlite3.SQLITE_OK if table in COLUMNS and (column in COLUMNS[table] or column == '') else sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_TRANSACTION and table == 'ROLLBACK':
        return sqlite3.SQLITE_OK
    if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE):
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY

def readonly(path):
    c = sqlite3.connect('file:' + urllib.parse.quote(str(Path(path).resolve()), safe='/') + '?mode=ro', uri=True, timeout=.2)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA query_only=ON')
    c.execute('BEGIN')
    started = time.monotonic()
    c.set_progress_handler(lambda: int(time.monotonic() - started > 20), 1000)
    c.set_authorizer(authorizer)
    return c

def safe_review(raw):
    r = json.loads(raw)
    if not isinstance(r, dict):
        return None
    # Explicit fields only, no arbitrary source features or model columns.
    out = {k: r.get(k) for k in ['mint','chain','pair','checked_at']}
    out['checks'] = {k: {a:v.get(a) for a in ['status','observed_at','evidence_refs','reason']} for k,v in r.get('checks',{}).items() if isinstance(v,dict)}
    return out

def collect(c, mode, now, reserves=None, since=None, max_cases=10000):
    exclusion = 'NOT EXISTS(SELECT 1 FROM pl_predictions p WHERE p.mint=d.mint)'
    earliest = "NOT EXISTS(SELECT 1 FROM v2_cases e WHERE e.mint=d.mint AND e.source='ALERT' AND (e.decision_ts<d.decision_ts OR (e.decision_ts=d.decision_ts AND e.id<d.id)))"
    q = "SELECT d.id,d.mint,d.decision_ts,d.score,d.regime FROM v2_cases d WHERE d.source='ALERT' AND " + exclusion
    params = []
    if mode == 'replay':
        q += ' AND ' + earliest
    else:
        q += ' AND d.decision_ts>=?'; params.append(max(since or now-120, now-120))
    q += ' AND d.decision_ts<=? ORDER BY d.decision_ts,d.id LIMIT ?'; params += [now,max_cases+1]
    rows = c.execute(q, params).fetchall()
    if len(rows) > max_cases:
        raise ValueError('export_case_limit_exceeded_no_partial_results')
    out = []
    for d in rows:
        at = d['decision_ts']
        l = c.execute('SELECT symbol,created_ts,pinned_pair FROM launches WHERE mint=?', (d['mint'],)).fetchone()
        row = {k:d[k] for k in d.keys()}
        row.update(symbol=l['symbol'] if l else '?', created_ts=l['created_ts'] if l else None, pair=l['pinned_pair'] if l else None)
        review_at = at if mode == 'replay' else now
        review = c.execute('SELECT review FROM prealert_reviews WHERE mint=? AND checked_at BETWEEN ? AND ? ORDER BY checked_at DESC,review LIMIT 1', (d['mint'],review_at-300,review_at)).fetchone()
        row['review'] = safe_review(review[0]) if review else None
        if mode == 'replay' and row['review']:
            row['pair'] = row['review'].get('pair')
        start, end = (at, min(now,at+60+180+7200+180)) if mode == 'replay' else (now-120,now)
        snapshots = c.execute('SELECT ts,pair,price,mc,liq FROM snapshots WHERE mint=? AND ts BETWEEN ? AND ? ORDER BY ts', (d['mint'], start, end)).fetchall()
        row['snapshots'] = [dict(s) for s in snapshots]
        row['reserves'] = [r for r in reserves or [] if r.get('mint') == d['mint'] and start-180 <= r.get('observed_at', -1e20) <= end]
        out.append(row)
    return {'schema':'meme-desk-export-v1','mode':mode,'exported_at':now,'protocol_sha256':PROTOCOL_SHA256,'preregistration_commit':PREREG_COMMIT,
            'frozen_membership_excluded':True,'source_query_only':True,'rows':out,
            'aggregates':{'development_alerts_exported':len(out),'reserve_captures_exported':sum(len(x['reserves']) for x in out)}}

def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError('symlink_output_refused')
    fd, temp = tempfile.mkstemp(prefix='.desk-export-', dir=path.parent)
    try:
        os.fchmod(fd, 0o640)
        with os.fdopen(fd, 'w') as f:
            f.write(canonical(data)+'\n'); f.flush(); os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp): os.unlink(temp)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source', default=SOURCE)
    p.add_argument('--mode', choices=['replay','tickets'], required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--reserve-archive')
    p.add_argument('--expected-bundle', required=True)
    p.add_argument('--reader-uid',type=int)
    a=p.parse_args()
    from verify import verify
    verify(a.expected_bundle)  # Before DB open; includes protocol and all implementation files.
    reserves=[]
    if a.reserve_archive:
        with open(a.reserve_archive) as f:
            reserves=[json.loads(line) for line in f if line.strip()]
    c=readonly(a.source)
    try:
        result=collect(c,a.mode,int(time.time()),reserves)
    finally:
        c.rollback();c.close()
    atomic_write(a.output,result)
    if a.reader_uid is not None:
        import pwd,stat
        if os.geteuid()!=0:raise ValueError('reader_assignment_requires_owner')
        reader=pwd.getpwuid(a.reader_uid);parent=Path(a.output).parent
        st=parent.stat()
        if st.st_uid!=0 or st.st_mode & 0o022:raise ValueError('export_directory_must_be_owner_controlled')
        os.chown(parent,-1,reader.pw_gid);os.chmod(parent,0o750)
        os.chown(a.output,0,reader.pw_gid);os.chmod(a.output,0o640)
    print(canonical({'output':a.output,'sha256':hashlib.sha256(Path(a.output).read_bytes()).hexdigest(),**result['aggregates'],'mode':a.mode,'query_only':True,'protected_outcomes_read':False}))
if __name__=='__main__': main()
