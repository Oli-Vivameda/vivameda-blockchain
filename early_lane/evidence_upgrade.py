#!/usr/bin/env python3
"""Owner-only source repair for the stopped RPC early-lane installation.

Preserves own user/config/state and all journal rows. Starts/stops no services.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import sqlite3
import subprocess
import sys
import tempfile
from install import BASE,STATE,INBOX,ETC,NAME,units
from verify import verify
from exporter import readonly,collect
from sources import Collector
from pricing import Marks
import time
OLD='41b453fb10042452c0f35a215973d6eb0c21fb07703ce59425558dc41946ea1d'

def preflight(frame,rpc):
    batch=sorted(frame['launches'],key=lambda x:(-x['created_at'],x['mint']))[:30]
    if not batch:raise ValueError('no_recent_launches_for_live_pricing_preflight')
    rpc.budget(6);marks=Marks(rpc).read(batch)
    count=sum(v.get('mc') is not None for v in marks.values())
    result={'sampled_launches':len(batch),'authenticated_market_marks':count,'unpriced':len(batch)-count,'meaning':'pricing transport only, not full screening or alert readiness'}
    if not count:raise ValueError('no_authenticated_live_prices_upgrade_not_applied')
    return result

def ensure_stopped(run=subprocess.run):
    for name in (NAME+'.service',NAME+'-rollout.service',NAME+'-rollout-rpc.service',NAME+'-rollout-rpc2.service',NAME+'-evidence-shadow.service',NAME+'-export.service',NAME+'-export.timer'):
        r=run(['systemctl','show',name,'--property=ActiveState','--value'],capture_output=True,text=True,check=True)
        if r.stdout.strip() not in ('inactive','failed',''):raise ValueError('stop_only_early_lane_first:'+name)

def journal_state(path):
    if not path.exists():raise ValueError('existing_state_required')
    c=sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True);c.execute('PRAGMA query_only=ON')
    try:
        from core import digest
        previous='';n=0;cohorts=0;activation=None
        for seq,ts,kind,key,body,prev,h in c.execute('SELECT seq,ts,kind,key,body,previous,hash FROM events ORDER BY seq'):
            data=json.loads(body);n+=1
            if seq!=n or prev!=previous or h!=digest(dict(seq=seq,ts=ts,kind=kind,key=key,body=data,previous=prev)):raise ValueError('existing_journal_corrupt')
            previous=h;cohorts+=kind=='cohort'
            if kind=='activation':activation=ts
        return {'events':n,'head':previous,'cohorts':cohorts,'activation':activation}
    finally:c.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--expected-bundle',required=True);p.add_argument('--from-bundle',required=True);a=p.parse_args()
    if os.geteuid()!=0:raise SystemExit('Owner root action required; no escalation attempted')
    if sys.version_info[:2]!=(3,12):raise SystemExit('Python 3.12 required')
    if a.from_bundle!=OLD:raise SystemExit('Only the reviewed RPC bundle can be upgraded here')
    root=Path(__file__).resolve().parent;m=verify(a.expected_bundle,root);verify(OLD,BASE/OLD)
    ensure_stopped()
    lock=open(STATE/'process.lock','r');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    before=journal_state(STATE/'lane.sqlite3');u=pwd.getpwnam(NAME)
    for folder in (BASE,ETC,INBOX):
        s=folder.lstat()
        if folder.is_symlink() or s.st_uid!=0 or s.st_mode&0o022:raise SystemExit('Root-controlled existing paths required')
    target=Path('/etc/systemd/system');old_units=units(BASE/OLD,OLD,u.pw_uid,'/opt/vivameda-crypto-early-scout/data/early_scout.sqlite')
    for name,want in old_units.items():
        if (target/name).is_symlink() or (target/name).read_text()!=want:raise SystemExit('Existing unit changed; separate review required: '+name)
    # No installation mutation until live pricing succeeds on owner-exported mints.
    c=readonly('/opt/vivameda-crypto-early-scout/data/early_scout.sqlite')
    try:frame=collect(c,time.time())
    finally:c.rollback();c.close()
    with tempfile.TemporaryDirectory(prefix='early-lane-price-preflight-') as t:
        collector=Collector(Path(t)/'rpc.sqlite3')
        try:live=preflight(frame,collector.rpc)
        finally:collector.cache.close()
    print(json.dumps({'live_pricing_preflight':live}),flush=True)
    dest=BASE/a.expected_bundle
    if dest.exists():raise SystemExit('New release path already exists; inspect rather than overwrite')
    subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(root/'tests'),'-q'],cwd=root,check=True)
    dest.mkdir(mode=0o755);dest.chmod(0o755)
    for name in m['sha256']:
        out=dest/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes((root/name).read_bytes());out.chmod(0o644)
    for f in dest.rglob('*'):
        if f.is_dir():f.chmod(0o755)
    (dest/'BUNDLE.json').write_bytes((root/'BUNDLE.json').read_bytes());(dest/'BUNDLE.json').chmod(0o644);verify(a.expected_bundle,dest)
    definitions=units(dest,a.expected_bundle,u.pw_uid,'/opt/vivameda-crypto-early-scout/data/early_scout.sqlite')
    with tempfile.TemporaryDirectory(prefix='early-lane-unit-verify-') as temp:
        paths=[]
        for name,text in definitions.items():
            out=Path(temp)/name;out.write_text(text);paths.append(str(out))
        subprocess.run(['systemd-analyze','verify']+paths,check=True)
    backup=BASE/('before-evidence-repair-'+a.expected_bundle);backup.mkdir(mode=0o700)
    for name,text in definitions.items():(backup/name).write_bytes((target/name).read_bytes())
    try:
        for name,text in definitions.items():
            temporary=target/(name+'.early-lane-new');temporary.write_text(text);temporary.chmod(0o644);os.replace(temporary,target/name)
        subprocess.run(['systemctl','daemon-reload'],check=True)
    except BaseException:
        for name in definitions:(target/name).write_bytes((backup/name).read_bytes())
        subprocess.run(['systemctl','daemon-reload'],check=False);raise
    after=journal_state(STATE/'lane.sqlite3')
    if before!=after:raise SystemExit('Journal changed unexpectedly; do not start')
    print(json.dumps({'upgraded':True,'old_bundle':OLD,'bundle':a.expected_bundle,'journal_preserved':True,'activation':after['activation'],'started':False,'scanner_changed':False,'public_launch_refresh':False,'pricing':'read-only public RPC + on-chain Pyth','live_pricing_preflight':live,'screening_ready':False,'delivery_enabled':False}))
if __name__=='__main__':main()
