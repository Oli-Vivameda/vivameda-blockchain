"""Owner-only install. Does not start, enable, or configure delivery."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import stat
import subprocess
import sys
import tempfile

CREDENTIAL = Path('/opt/vivameda-crypto-early-scout/credentials.json')
UNIT_PATH = Path('/etc/systemd/system/vivameda-early-lane-sender.service')
STATE = Path('/var/lib/vivameda-early-lane-sender')

def unit_text(release):
    return f'''[Unit]
Description=Early lane root-authenticated Telegram sender (no autonomous sends)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Group=vivameda-early-lane
WorkingDirectory={release}
ExecStart=/usr/bin/python3 -I -B {release}/owner.py --expected-bundle {release.name} serve
UMask=0077
RuntimeDirectory=vivameda-early-lane-sender
RuntimeDirectoryMode=0750
StateDirectory=vivameda-early-lane-sender
StateDirectoryMode=0700
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes
LockPersonality=yes
CapabilityBoundingSet=
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
ReadOnlyPaths={CREDENTIAL} /etc/vivameda-early-lane/delivery.json
ReadWritePaths={STATE} /run/vivameda-early-lane-sender
InaccessiblePaths=-/opt/vivameda-crypto-early-scout/data -/var/lib/vivameda-early-lane
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
'''

def main():
    p = argparse.ArgumentParser(); p.add_argument('--expected-bundle', required=True); a = p.parse_args()
    if os.geteuid() != 0: raise SystemExit('root_required')
    if sys.version_info < (3, 12): raise SystemExit('python_3_12_required')
    root = Path(__file__).resolve().parent
    raw = (root / 'BUNDLE.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != a.expected_bundle: raise SystemExit('bundle_mismatch')
    manifest = json.loads(raw)['sha256']
    for name, expected in manifest.items():
        data = (root / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected: raise SystemExit('file_mismatch')
    # Metadata only. Neither the installer nor tests read the live credential.
    st = CREDENTIAL.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o027:
        raise SystemExit('credential_requires_root_owned_nonwritable_private_file')
    pwd.getpwnam('vivameda-early-lane')
    release = Path('/opt/vivameda-early-lane-sender') / a.expected_bundle
    if UNIT_PATH.exists() or UNIT_PATH.is_symlink() or release.exists() or STATE.exists() or STATE.is_symlink():
        raise SystemExit('existing_sender_requires_separately_reviewed_upgrade')
    # Offline tests and systemd syntax verification before installation writes.
    subprocess.run([sys.executable, '-I', '-B', '-m', 'unittest', 'discover', '-s', str(root / 'tests')], cwd=root, check=True)
    with tempfile.TemporaryDirectory(prefix='early-lane-sender-unit-') as temp:
        candidate = Path(temp) / UNIT_PATH.name
        candidate.write_text(unit_text(release))
        # Verify syntax with the existing interpreter as ExecStart; the release
        # directory has intentionally not been created yet.
        check = unit_text(release).replace(f'WorkingDirectory={release}\n', '').replace(
            f'ExecStart=/usr/bin/python3 -I -B {release}/owner.py --expected-bundle {release.name} serve',
            'ExecStart=/usr/bin/python3 -c pass')
        candidate.write_text(check)
        subprocess.run(['systemd-analyze', 'verify', str(candidate)], check=True)
    release.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    parent = release.parent.lstat()
    if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != 0 or parent.st_mode & 0o022:
        raise SystemExit('unsafe_install_parent')
    release.mkdir(mode=0o755)
    try:
        for name in manifest:
            dest = release / name; dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((root / name).read_bytes()); dest.chmod(0o644)
        (release / 'BUNDLE.json').write_bytes(raw); (release / 'BUNDLE.json').chmod(0o644)
        for directory, _, _ in os.walk(release): os.chmod(directory, 0o755)
        STATE.mkdir(mode=0o700); os.chown(STATE, 0, 0)
        with UNIT_PATH.open('x') as unit: unit.write(unit_text(release))
        UNIT_PATH.chmod(0o644)
        subprocess.run(['systemctl', 'daemon-reload'], check=True)
    except Exception:
        # No service has been started; keep a failed install visible for review.
        raise SystemExit('install_incomplete_sender_not_started') from None
    print(json.dumps({'installed': True, 'started': False, 'enabled': False,
                      'delivery_config_changed': False, 'credential_contents_read': False,
                      'bundle': a.expected_bundle, 'state': str(STATE)}))

if __name__ == '__main__': main()
