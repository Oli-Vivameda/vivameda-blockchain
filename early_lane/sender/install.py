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
from sender import credential_metadata_valid, secure_json

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
CapabilityBoundingSet=CAP_DAC_READ_SEARCH
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
ReadOnlyPaths={CREDENTIAL} /etc/vivameda-early-lane/delivery.json
ReadWritePaths={STATE} /run/vivameda-early-lane-sender
InaccessiblePaths=-/opt/vivameda-crypto-early-scout/data -/var/lib/vivameda-early-lane
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
'''

def verify_release(root, expected):
    raw = (root / 'BUNDLE.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected: raise SystemExit('installed_bundle_mismatch')
    for name, digest in json.loads(raw)['sha256'].items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or (root / path).is_symlink(): raise SystemExit('unsafe_installed_source')
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != digest: raise SystemExit('installed_source_mismatch')

def stopped_units():
    for name in ('vivameda-early-lane-sender.service', 'vivameda-early-lane.service'):
        run = subprocess.run(['systemctl', 'show', name, '--property=ActiveState', '--property=UnitFileState', '--no-pager'], capture_output=True, text=True, check=True)
        fields = dict(line.split('=', 1) for line in run.stdout.splitlines() if '=' in line)
        if fields.get('ActiveState') not in ('inactive', 'failed') or fields.get('UnitFileState') != 'disabled':
            raise SystemExit('continuous_services_must_be_stopped_and_disabled')

def main():
    p = argparse.ArgumentParser(); p.add_argument('--expected-bundle', required=True); p.add_argument('--from-bundle'); a = p.parse_args()
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
    if not credential_metadata_valid(st):
        raise SystemExit('credential_requires_root_or_scanner_owned_owner_only_file')
    pwd.getpwnam('vivameda-early-lane')
    release = Path('/opt/vivameda-early-lane-sender') / a.expected_bundle
    upgrading = a.from_bundle is not None
    if upgrading:
        stopped_units()
        config = secure_json(Path('/etc/vivameda-early-lane/delivery.json'))
        if config.get('new_channel_confirmed') is not False or config.get('confirmed_at') is not None:
            raise SystemExit('delivery_must_remain_disabled')
        st = STATE.lstat()
        if not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o077: raise SystemExit('unsafe_sender_state')
        unit_stat = UNIT_PATH.lstat()
        if not stat.S_ISREG(unit_stat.st_mode) or unit_stat.st_uid != 0 or unit_stat.st_mode & 0o022: raise SystemExit('unsafe_sender_unit')
        if release.exists():
            verify_release(release, a.expected_bundle)
            if UNIT_PATH.read_text() != unit_text(release): raise SystemExit('installed_unit_mismatch')
            print(json.dumps({'already_upgraded': True, 'started': False, 'enabled': False}))
            return
        previous = release.parent / a.from_bundle
        if not all(c in '0123456789abcdef' for c in a.from_bundle) or len(a.from_bundle) != 64: raise SystemExit('invalid_previous_bundle')
        verify_release(previous, a.from_bundle)
        if UNIT_PATH.read_text() != unit_text(previous): raise SystemExit('installed_unit_mismatch')
    elif UNIT_PATH.exists() or UNIT_PATH.is_symlink() or release.exists() or STATE.exists() or STATE.is_symlink():
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
        if not upgrading:
            STATE.mkdir(mode=0o700); os.chown(STATE, 0, 0)
        if upgrading:
            backup = STATE / ('sender-unit-before-' + a.from_bundle + '.service')
            if not backup.exists():
                with backup.open('x') as saved: saved.write(UNIT_PATH.read_text())
                backup.chmod(0o600)
        with UNIT_PATH.open('w' if upgrading else 'x') as unit: unit.write(unit_text(release))
        UNIT_PATH.chmod(0o644)
        subprocess.run(['systemctl', 'daemon-reload'], check=True)
    except Exception:
        # No service has been started; keep a failed install visible for review.
        raise SystemExit('install_incomplete_sender_not_started') from None
    print(json.dumps({'installed': True, 'started': False, 'enabled': False,
                      'delivery_config_changed': False, 'credential_contents_read': False,
                      'bundle': a.expected_bundle, 'state': str(STATE), 'state_preserved': True}))

if __name__ == '__main__': main()
