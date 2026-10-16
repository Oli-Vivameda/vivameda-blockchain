#!/usr/bin/env python3
"""Owner-run, scoped installation. Never called by the engineering connector."""
import argparse
import grp
import hashlib
import json
import os
import pathlib
import pwd
import shutil
import subprocess
import tempfile

NAME = 'vivameda-copy-paper'
UNIT = NAME + '.service'
BASE = pathlib.Path('/opt') / NAME
STATE = pathlib.Path('/var/lib') / NAME

def check(root, release):
    for name, expected in release['sha256'].items():
        p = pathlib.PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or (root / name).is_symlink():
            raise ValueError('Unsafe source path')
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Release content mismatch: ' + name)

def main():
    a = argparse.ArgumentParser()
    a.add_argument('--expected-release-sha256', required=True)
    args = a.parse_args()
    if os.geteuid() != 0:
        raise SystemExit('Owner root action required; no privilege escalation is attempted')
    src = pathlib.Path(__file__).resolve().parent
    raw = (src / 'RELEASE.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.expected_release_sha256:
        raise SystemExit('Reviewed release mismatch')
    release = json.loads(raw)
    check(src, release)
    # Never silently replace an existing installation or its frozen configuration.
    unitpath = pathlib.Path('/etc/systemd/system') / UNIT
    if unitpath.exists() or (BASE / 'current').exists():
        raise SystemExit('Existing installation: upgrade requires a separately reviewed migration; no runtime changes made')
    if any(x.is_symlink() for x in [BASE, STATE]):
        raise SystemExit('Unsafe installation path')
    BASE.mkdir(mode=0o755, exist_ok=True)
    dest = BASE / args.expected_release_sha256
    if dest.exists():
        raise SystemExit('Release directory already exists; inspect interrupted installation first')
    dest.mkdir(mode=0o755)
    for name in release['sha256']:
        p = dest / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((src / name).read_bytes())
        p.chmod(0o644)
    (dest / 'RELEASE.json').write_bytes(raw)
    check(dest, release)  # Validate the copied bytes, not just the mutable staging path.
    try:
        pwd.getpwnam(NAME)
        raise SystemExit('Service user already exists; inspect ownership before installation')
    except KeyError:
        subprocess.run(['useradd', '--system', '--home-dir', str(STATE), '--no-create-home', '--shell', '/usr/sbin/nologin', NAME], check=True)
    user = pwd.getpwnam(NAME)
    STATE.mkdir(mode=0o750, exist_ok=False)
    os.chown(STATE, user.pw_uid, user.pw_gid)
    # Offline tests execute as the new service user, never as root.
    subprocess.run(['runuser', '-u', NAME, '--', '/usr/bin/python3', '-B', '-m', 'unittest', 'discover', '-s', str(dest / 'tests'), '-q'], check=True, cwd=dest)
    config = json.loads((dest / 'config.json').read_text())
    watchlist = json.loads((dest / 'watchlist.json').read_text())
    if not config['paper_only'] or watchlist['wallets']:
        raise SystemExit('Initial reviewed installation must remain paper-only and waiting for verified wallets')
    unit = f'''[Unit]
Description=Vivameda isolated Solana copy paper experiment
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
User={NAME}
Group={NAME}
WorkingDirectory={dest}
ExecStart=/usr/bin/python3 -B {dest}/service.py run --state-dir {STATE}
Restart=on-failure
RestartSec=10
TimeoutStopSec=30
UMask=0027
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
LockPersonality=true
CapabilityBoundingSet=
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
ReadWritePaths={STATE}
MemoryMax=192M
CPUQuota=20%
TasksMax=16

[Install]
WantedBy=multi-user.target
'''
    unitpath.write_text(unit)
    subprocess.run(['systemd-analyze', 'verify', str(unitpath)], check=True)
    (BASE / 'current').symlink_to(dest.name)
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'enable', '--now', UNIT], check=True)
    subprocess.run(['systemctl', 'is-active', UNIT], check=True)
    print(json.dumps({'installed': str(dest), 'service': UNIT, 'release_sha256': args.expected_release_sha256, 'state': str(STATE), 'paper_only': True}))

if __name__ == '__main__':
    main()
