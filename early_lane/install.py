#!/usr/bin/env python3
"""Owner-only NEW lane installation. Never starts/enables any unit."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys
from verify import verify
NAME='vivameda-early-lane'
BASE=Path('/opt')/NAME
STATE=Path('/var/lib')/NAME
INBOX=Path('/var/lib/vivameda-early-lane-inbox')
ETC=Path('/etc')/NAME

def units(dest,bundle,uid,source):
    common='''NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
CapabilityBoundingSet=
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
MemoryMax=256M
CPUQuota=25%
TasksMax=16
UMask=0027
'''
    lane=f'''[Unit]
Description=Vivameda experimental early lane; read-only, no trading
After=network-online.target
[Service]
User={NAME}
Group={NAME}
WorkingDirectory={dest}
ExecStart=/usr/bin/python3 -B {dest}/service.py run --state-dir {STATE} --input {INBOX}/feed.json --delivery-config {ETC}/delivery.json
Restart=on-failure
RestartPreventExitStatus=75
RestartSec=15
TimeoutStopSec=30
ReadWritePaths={STATE}
InaccessiblePaths=/opt/vivameda-crypto-early-scout/data
{common}
[Install]
WantedBy=multi-user.target
'''
    export=f'''[Unit]
Description=Owner-approved read-only early lane export
[Service]
Type=oneshot
User=root
WorkingDirectory={dest}
ExecStart=/usr/bin/python3 -B {dest}/exporter.py --source {source} --output {INBOX}/feed.json --tracked {STATE}/tracked.json --expected-bundle {bundle} --reader-uid {uid}
TimeoutStartSec=55
ReadWritePaths={INBOX}
ReadOnlyPaths={Path(source).parent}
{common.replace('CapabilityBoundingSet=','CapabilityBoundingSet=CAP_CHOWN CAP_DAC_READ_SEARCH')}
'''
    timer='''[Unit]
Description=Refresh approved early lane feed every 20 seconds
[Timer]
OnBootSec=10
OnUnitActiveSec=20
AccuracySec=1
[Install]
WantedBy=timers.target
'''
    return {NAME+'.service':lane,NAME+'-export.service':export,NAME+'-export.timer':timer}

def main():
    p=argparse.ArgumentParser();p.add_argument('--expected-bundle',required=True);p.add_argument('--source',default='/opt/vivameda-crypto-early-scout/data/early_scout.sqlite');a=p.parse_args()
    if os.geteuid()!=0:raise SystemExit('Owner root action required; no escalation attempted')
    if sys.version_info[:2]!=(3,12):raise SystemExit('Python 3.12 required')
    root=Path(__file__).resolve().parent;manifest=verify(a.expected_bundle,root)
    source=Path(a.source)
    if not source.is_absolute() or not source.is_file() or any(c.isspace() for c in str(source)):raise SystemExit('Existing absolute scanner DB path required')
    target=Path('/etc/systemd/system')
    if any(x.exists() for x in (BASE,STATE,INBOX,ETC)) or any((target/n).exists() for n in units('/unused',a.expected_bundle,0,source)):raise SystemExit('Existing installation: reviewed migration required, never overwrite state')
    try:pwd.getpwnam(NAME);raise SystemExit('Existing service identity: inspect before installation')
    except KeyError:pass
    if shutil.disk_usage('/var/lib').free<3*1024**3:raise SystemExit('3 GiB free reserve required')
    # Test from a writable scratch cwd before changing the system.
    subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(root/'tests'),'-q'],cwd=root,check=True)
    BASE.mkdir(mode=0o755);BASE.chmod(0o755);dest=BASE/a.expected_bundle;dest.mkdir(mode=0o755);dest.chmod(0o755)
    for name in manifest['sha256']:
        out=dest/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes((root/name).read_bytes());out.chmod(0o644)
    for directory in dest.rglob('*'):
        if directory.is_dir():directory.chmod(0o755)
    (dest/'BUNDLE.json').write_bytes((root/'BUNDLE.json').read_bytes());(dest/'BUNDLE.json').chmod(0o644);verify(a.expected_bundle,dest)
    subprocess.run(['useradd','--system','--user-group','--home-dir',str(STATE),'--no-create-home','--shell','/usr/sbin/nologin',NAME],check=True)
    user=pwd.getpwnam(NAME)
    STATE.mkdir(mode=0o750);STATE.chmod(0o750);os.chown(STATE,user.pw_uid,user.pw_gid)
    for folder in (INBOX,ETC):folder.mkdir(mode=0o750);folder.chmod(0o750);os.chown(folder,0,user.pw_gid)
    confirmation=dict(new_channel_confirmed=False,channel=None,confirmed_at=None,socket=None)
    conf=ETC/'delivery.json';conf.write_text(json.dumps(confirmation,indent=2)+'\n');conf.chmod(0o640);os.chown(conf,0,user.pw_gid)
    for name,text in units(dest,a.expected_bundle,user.pw_uid,source).items():(target/name).write_text(text);(target/name).chmod(0o644)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    print(json.dumps(dict(installed=True,started=False,enabled=False,bundle=a.expected_bundle,source=str(source),state=str(STATE),inbox=str(INBOX),channel='TBD',scanner_changed=False)))
if __name__=='__main__':main()
