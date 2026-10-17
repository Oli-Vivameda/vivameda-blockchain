#!/usr/bin/env python3
"""Owner-only installation of NEW desk and read-only export units. No old units."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
NAME='vivameda-meme-desk'
BASE=Path('/opt')/NAME
STATE=Path('/var/lib')/NAME
INBOX=Path('/var/lib/vivameda-meme-desk-live')
ETC=Path('/etc')/NAME

def check(root,b):
    for n,h in b['sha256'].items():
        if Path(n).is_absolute() or '..' in Path(n).parts or (root/n).is_symlink():raise ValueError('unsafe_path')
        if hashlib.sha256((root/n).read_bytes()).hexdigest()!=h:raise ValueError('source_mismatch')

def stage_release(root,dest,raw,b):
    dest.mkdir(mode=0o755);dest.chmod(0o755)
    for n in b['sha256']:
        target=dest/n;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((root/n).read_bytes());target.chmod(0o644)
    for directory in dest.rglob('*'):
        if directory.is_dir():directory.chmod(0o755)
    (dest/'BUNDLE.json').write_bytes(raw);(dest/'BUNDLE.json').chmod(0o644)
    check(dest,b)

def main():
    p=argparse.ArgumentParser();p.add_argument('--expected-bundle',required=True);a=p.parse_args()
    if os.geteuid()!=0:raise SystemExit('Owner root action required; no escalation attempted')
    root=Path(__file__).resolve().parent;raw=(root/'BUNDLE.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=a.expected_bundle:raise SystemExit('Bundle mismatch')
    b=json.loads(raw);check(root,b)
    units=Path('/etc/systemd/system')
    names=[NAME+'.service',NAME+'-export.service',NAME+'-export.timer']
    if any((units/n).exists() for n in names) or any(x.exists() for x in [BASE,STATE,INBOX,ETC]):raise SystemExit('Existing installation/path: separate reviewed migration required')
    try:pwd.getpwnam(NAME);raise SystemExit('Service identity exists; inspect before installation')
    except KeyError:pass
    if shutil.disk_usage('/var/lib').free<3*1024**3:raise SystemExit('Less than 3 GiB free; no installation')
    BASE.mkdir(mode=0o755);BASE.chmod(0o755);dest=BASE/a.expected_bundle
    stage_release(root,dest,raw,b)
    subprocess.run(['useradd','--system','--user-group','--home-dir',str(STATE),'--no-create-home','--shell','/usr/sbin/nologin',NAME],check=True)
    u=pwd.getpwnam(NAME);STATE.mkdir(mode=0o750);os.chown(STATE,u.pw_uid,u.pw_gid)
    INBOX.mkdir(mode=0o750);INBOX.chmod(0o750);os.chown(INBOX,0,u.pw_gid)
    (INBOX/'reserves.jsonl').write_text('');(INBOX/'reserves.jsonl').chmod(0o600)
    ETC.mkdir(mode=0o750);ETC.chmod(0o750);os.chown(ETC,0,u.pw_gid)
    confirmation={'destination_confirmed':False,'destination':None,'confirmed_at':None,'owner_id':None,'socket':None}
    (ETC/'delivery.json').write_text(json.dumps(confirmation,indent=2)+'\n');os.chown(ETC/'delivery.json',0,u.pw_gid);(ETC/'delivery.json').chmod(0o640)
    subprocess.run(['runuser','-u',NAME,'--','/usr/bin/python3','-B','-m','unittest','discover','-s',str(dest/'tests'),'-q'],cwd=dest,check=True)
    common='''NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
CapabilityBoundingSet=
MemoryMax=192M
CPUQuota=20%
TasksMax=16
UMask=0027
'''
    desk=f'''[Unit]
Description=Vivameda human-review meme desk; no trading execution
After=network.target
[Service]
User={NAME}
Group={NAME}
WorkingDirectory={dest}
ExecStart=/usr/bin/python3 -B {dest}/service.py run --state-dir {STATE} --input {INBOX}/tickets.json --delivery-config {ETC}/delivery.json
Restart=on-failure
RestartPreventExitStatus=75
RestartSec=10
TimeoutStopSec=30
RestrictAddressFamilies=AF_UNIX
ReadWritePaths={STATE}
{common}
[Install]
WantedBy=multi-user.target
'''
    export=f'''[Unit]
Description=Read-only owner-approved meme desk scanner export
[Service]
Type=oneshot
User=root
WorkingDirectory={dest}
ExecStart=/usr/bin/python3 -B {dest}/exporter.py --mode tickets --output {INBOX}/tickets.json --reserve-archive {INBOX}/reserves.jsonl --expected-bundle {a.expected_bundle} --reader-uid {u.pw_uid}
TimeoutStartSec=30
RestrictAddressFamilies=AF_UNIX
ReadWritePaths={INBOX}
ReadOnlyPaths=/opt/vivameda-crypto-early-scout/data
{common}
'''
    # Root exporter needs chown of its OWN output group; no DB permission changes.
    export=export.replace('CapabilityBoundingSet=','CapabilityBoundingSet=CAP_CHOWN CAP_DAC_READ_SEARCH')
    timer=f'''[Unit]
Description=Refresh meme desk sanitized input every 15 seconds
[Timer]
OnBootSec=15
OnUnitInactiveSec=15
AccuracySec=1
Unit={NAME}-export.service
[Install]
WantedBy=timers.target
'''
    for n,text in zip(names,[desk,export,timer]):(units/n).write_text(text)
    subprocess.run(['systemd-analyze','verify']+[str(units/n) for n in names],check=True)
    (BASE/'current').symlink_to(dest.name)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','--now',NAME+'-export.timer',NAME+'.service'],check=True)
    subprocess.run(['systemctl','is-active',NAME+'.service'],check=True)
    print(json.dumps({'installed':True,'bundle':a.expected_bundle,'service':NAME+'.service','state':str(STATE),'inbox':str(INBOX),'delivery_enabled':False,'scanner_database_permissions_changed':False,'existing_services_restarted':False}))
if __name__=='__main__':main()
