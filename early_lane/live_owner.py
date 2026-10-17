"""Hash-checked isolated entrypoint for no-start staging or bounded stream shadow."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

def main():
    p=argparse.ArgumentParser();p.add_argument('--expected-bundle',required=True);p.add_argument('command',choices=['stage','shadow']);p.add_argument('args',nargs=argparse.REMAINDER);a=p.parse_args()
    root=Path(__file__).resolve().parent;raw=(root/'BUNDLE.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=a.expected_bundle:raise SystemExit('reviewed_bundle_mismatch')
    files={}
    for name,want in json.loads(raw)['sha256'].items():
        path=Path(name)
        if path.is_absolute()or '..'in path.parts or(root/path).is_symlink():raise SystemExit('unsafe_source_path')
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=want:raise SystemExit('reviewed_file_mismatch:'+name)
        files[name]=data
    with tempfile.TemporaryDirectory(prefix='early-lane-live-reviewed-')as temp:
        snap=Path(temp);os.chmod(snap,0o700)
        for name,data in files.items():
            out=snap/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
        (snap/'BUNDLE.json').write_bytes(raw)
        args=a.args[1:]if a.args[:1]==['--']else a.args
        cmd=[str(snap/'stream_stage.py'),'--expected-bundle',a.expected_bundle]if a.command=='stage'else[str(snap/'live_shadow.py')]
        raise SystemExit(subprocess.run([sys.executable,'-B']+cmd+args,cwd=snap).returncode)
if __name__=='__main__':main()
