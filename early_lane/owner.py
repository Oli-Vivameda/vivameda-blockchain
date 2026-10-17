#!/usr/bin/env python3
"""Hash-checked owner entrypoint. Snapshot reviewed bytes before importing code."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--expected-bundle',required=True)
    p.add_argument('command',choices=['export','install','upgrade','log-only','report','once'])
    p.add_argument('args',nargs=argparse.REMAINDER);a=p.parse_args()
    root=Path(__file__).resolve().parent
    raw=(root/'BUNDLE.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=a.expected_bundle:raise SystemExit('Reviewed bundle mismatch; no protected data opened')
    files={}
    for name,want in json.loads(raw)['sha256'].items():
        path=Path(name)
        if path.is_absolute() or '..' in path.parts or (root/path).is_symlink():raise SystemExit('Unsafe source path')
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=want:raise SystemExit('Reviewed file mismatch: '+name)
        files[name]=data
    # Captured bytes go to a private directory before executing any project import.
    # The root command's caller should check owner.py itself before running it.
    with tempfile.TemporaryDirectory(prefix='vivameda-early-lane-reviewed-') as temp:
        snap=Path(temp);os.chmod(snap,0o700)
        for name,data in files.items():
            dest=snap/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        (snap/'BUNDLE.json').write_bytes(raw)
        args=a.args[1:] if a.args[:1]==['--'] else a.args
        if a.command=='export':cmd=[str(snap/'exporter.py'),'--expected-bundle',a.expected_bundle]+args
        elif a.command=='install':cmd=[str(snap/'install.py'),'--expected-bundle',a.expected_bundle]+args
        elif a.command=='upgrade':cmd=[str(snap/'upgrade.py'),'--expected-bundle',a.expected_bundle]+args
        else:cmd=[str(snap/'service.py'),a.command]+args
        raise SystemExit(subprocess.run([sys.executable,'-B']+cmd,cwd=snap).returncode)
if __name__=='__main__':main()
