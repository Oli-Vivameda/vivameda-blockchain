"""Recover ordinary pre-call price samples from fixed private SQLite archives only."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import sqlite3
import time

HERE = Path(__file__).resolve().parent
RUN = HERE/'results/1791717527'
AUDIT_SHA = 'a6be3b3fcf8af373ef13a06da1eb60a78f7cba14fa952693f7d60ea4b9a98bd5'
LIVE = Path('/opt/vivameda-crypto-early-scout/data/early_scout.sqlite')
ARCHIVE = Path('/var/lib/vivameda-snapshot-archive/snapshots.sqlite')
ROOTS = (Path('/opt/vivameda-operations/crypto-backups'), Path('/opt/vivameda-operations/connect-backups'))

def source_connection(path):
    c=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=1)
    c.execute('PRAGMA query_only=ON')
    def authorize(action, table, column, db, trigger):
        if action==sqlite3.SQLITE_READ and (table!='snapshots' or column not in ('mint','ts','price','pair')):
            return sqlite3.SQLITE_DENY
        if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE,
                      sqlite3.SQLITE_ATTACH,sqlite3.SQLITE_DETACH):return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    c.set_authorizer(authorize);return c

def merge_samples(sources, cases, excluded):
    saved={c['id']:{} for c in cases if c['mint'] not in excluded};conflicts={k:set() for k in saved}
    receipts=[]
    for label,con in sources:
        start=time.monotonic();con.set_progress_handler(lambda:int(time.monotonic()-start>15),1000)
        count=0
        try:
            con.execute('BEGIN')
            for c in cases:
                if c['mint'] in excluded:continue
                rows=con.execute('SELECT ts,price,pair FROM snapshots WHERE mint=? AND ts BETWEEN ? AND ? ORDER BY ts LIMIT 2101',
                    (c['mint'],c['decision_ts']-2100,c['decision_ts'])).fetchall()
                if len(rows)>2100:raise ValueError('Source sample bound exceeded')
                for row in rows:
                    t,price,pair=row
                    previous=saved[c['id']].get(t)
                    if previous is not None and previous!=(t,price,pair):conflicts[c['id']].add(t)
                    saved[c['id']][t]=(t,price,pair);count+=1
            receipts.append({'source':label,'matched_sample_rows':count,'status':'read_complete'})
        except sqlite3.Error as e:
            receipts.append({'source':label,'status':'unavailable_or_not_snapshot_schema','error_type':type(e).__name__})
        finally:con.rollback();con.set_progress_handler(None,0)
    # Disagreeing snapshots are not silently resolved by source order.
    result={k:[v for t,v in sorted(rows.items()) if t not in conflicts[k]] for k,rows in saved.items()}
    return result,receipts,sum(len(v) for v in conflicts.values())

def discover():
    paths=[ARCHIVE] if ARCHIVE.is_file() and not ARCHIVE.is_symlink() else []
    compressed=0;visited=0
    for root in ROOTS:
        if not root.is_dir() or root.is_symlink():continue
        for directory,dirs,files in os.walk(root,followlinks=False):
            base=Path(directory);visited+=1
            if visited>1000:raise ValueError('Backup discovery bound exceeded')
            dirs[:]=[d for d in dirs if not (base/d).is_symlink()]
            if len(base.relative_to(root).parts)>=3:dirs[:]=[]
            for name in files:
                path=base/name
                if path.is_symlink():continue
                if name in ('early_scout.sqlite','early_scout.sqlite3','early_scout.db'):
                    with path.open('rb') as f:header=f.read(16)
                    if header==b'SQLite format 3\0':paths.append(path)
                elif name.endswith(('.gz','.tgz','.zip','.zst')):compressed+=1
    if len(paths)>60:raise ValueError('Snapshot source bound exceeded; refine explicitly')
    return paths,compressed

def main():
    p=argparse.ArgumentParser();p.add_argument('--owner-recover',action='store_true');p.add_argument('--expected-sha256',required=True);a=p.parse_args()
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest()!=a.expected_sha256:raise ValueError('Recovery hash mismatch')
    if not a.owner_recover or os.geteuid()!=0:raise ValueError('Fixed-path owner recovery required')
    if hashlib.sha256((HERE/'audit.py').read_bytes()).hexdigest()!=AUDIT_SHA:raise ValueError('Audit dependency changed')
    spec=importlib.util.spec_from_file_location('reviewed_audit',HERE/'audit.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    if RUN.is_symlink() or (RUN/'audit.json').is_symlink():raise ValueError('Audit path symlink refused')
    if (RUN/'audit.json').stat().st_size>50*1024**2:raise ValueError('Audit input bound exceeded')
    report=json.loads((RUN/'audit.json').read_text())
    if report.get('schema')!='private-retrospective-chart-audit-v1' or report.get('audit_source_sha256')!=AUDIT_SHA:raise ValueError('Unexpected audit report')
    live=sqlite3.connect(LIVE.as_uri()+'?mode=ro',uri=True,timeout=1)
    try:
        live.execute('PRAGMA query_only=ON');excluded={r[0] for r in live.execute('SELECT mint FROM pl_predictions')}
    finally:live.close()
    cases=[c for c in report['cases'] if c['mint'] not in excluded]
    paths,compressed=discover();sources=[]
    try:
        for path in paths:
            try:sources.append((str(path),source_connection(path)))
            except sqlite3.Error:pass
        samples,receipts,conflicts=merge_samples(sources,cases,excluded)
    finally:
        for _,c in sources:c.close()
    identity=pwd.getpwnam('vivameda-engineer');out=RUN/('recovery-'+str(int(time.time())))
    out.mkdir(mode=0o700);os.chown(out,identity.pw_uid,identity.pw_gid)
    recovered=[];counts={};index={}
    for c in cases:
        rows=samples.get(c['id'],[]);features,status=audit.pre_features(rows,c['decision_ts'])
        counts[status]=counts.get(status,0)+1
        recovered.append({'id':c['id'],'mint':c['mint'],'symbol':c['symbol'],'primary':c['primary'],
                          'decision_ts':c['decision_ts'],'pre_chart_status':status,'recovered_features':features,
                          'saved_pre_price_samples':rows})
        if rows:
            name=hashlib.sha256(c['id'].encode()).hexdigest()[:24]+'.svg'
            audit.private_write(out/name,audit.svg_chart(c,rows,[]),identity.pw_uid,identity.pw_gid);index[c['id']]=name
    result={'schema':'private-pre-chart-recovery-v1','output_directory':str(out),'sources':receipts,
            'compressed_backup_files_not_opened':compressed,'conflicting_timestamps_removed':conflicts,
            'pre_chart_status_counts':counts,'cases':recovered,'chart_index':index,
            'protected_records_read':False,'production_changed':False,'weights_updated':False,
            'limitations':['Only existing direct SQLite snapshot sources were queried; compressed backups were not opened.',
                           'Reconstructed snapshots are not original OHLC candles; no intraminute prices are invented.',
                           'Any archived sample could have been copied after its observation time; knowledge time is unverified.']}
    audit.private_write(out/'recovery.json',audit.canonical(result)+'\n',identity.pw_uid,identity.pw_gid)
    print(audit.canonical({k:v for k,v in result.items() if k not in ('cases','chart_index')}))

if __name__=='__main__':main()
