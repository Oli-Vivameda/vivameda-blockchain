#!/usr/bin/env python3
"""Verify and snapshot the reviewed sender before importing executable code."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

def snapshot_command(snapshot, command):
    # Isolated Python deliberately omits the script directory. Add only the
    # private, hash-verified snapshot before loading reviewed local helpers.
    bootstrap = ("import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); "
                 "sys.argv=sys.argv[1:]; runpy.run_path(sys.argv[0],run_name='__main__')")
    return [sys.executable, '-I', '-B', '-c', bootstrap, str(snapshot)] + command

def main():
    p = argparse.ArgumentParser(); p.add_argument('--expected-bundle', required=True)
    p.add_argument('command', choices=['install', 'serve', 'test-channel'])
    p.add_argument('args', nargs=argparse.REMAINDER); a = p.parse_args()
    root = Path(__file__).resolve().parent
    raw = (root / 'BUNDLE.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != a.expected_bundle:
        raise SystemExit('sender_bundle_mismatch_no_credential_opened')
    files = {}
    for name, expected in json.loads(raw)['sha256'].items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or (root / path).is_symlink():
            raise SystemExit('unsafe_sender_source_path')
        data = (root / path).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected: raise SystemExit('sender_source_mismatch')
        files[name] = data
    with tempfile.TemporaryDirectory(prefix='early-lane-sender-reviewed-') as temp:
        snap = Path(temp); snap.chmod(0o700)
        for name, data in files.items():
            dest = snap / name; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(data)
        (snap / 'BUNDLE.json').write_bytes(raw)
        args = a.args[1:] if a.args[:1] == ['--'] else a.args
        if a.command == 'install': command = [str(snap / 'install.py'), '--expected-bundle', a.expected_bundle] + args
        else: command = [str(snap / 'sender.py'), a.command] + args
        # Snapshot contains only reviewed files; safe path first for imports.
        raise SystemExit(subprocess.run(snapshot_command(snap, command), cwd=snap).returncode)
if __name__ == '__main__': main()
