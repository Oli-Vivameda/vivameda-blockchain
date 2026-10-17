"""Root-only, no-start staging of a reviewed shadow bundle. No unit/config edits."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
from install import BASE,STATE,NAME
from verify import verify
from upgrade import journal_state
OLD='0a595dc64aa0d660bbfebd878a885fdee5c7daf4e5a1dedb384821bb2d181390'

def stage(expected,root=None,run=subprocess.run):
    if os.geteuid()!=0:raise ValueError('owner_root_action_required')
    if sys.version_info[:2]!=(3,12):raise ValueError('python_3_12_required')
    root=Path(root or Path(__file__).resolve().parent);manifest=verify(expected,root)
    verify(OLD,BASE/OLD)
    for unit in (NAME+'.service',NAME+'-queue-shadow.service',NAME+'-stream-shadow.service'):
        result=run(['systemctl','show',unit,'--property=ActiveState','--value'],capture_output=True,text=True,check=True)
        if result.stdout.strip()not in ('inactive','failed',''):raise ValueError('early_lane_process_must_be_stopped:'+unit)
    for path in (BASE,STATE):
        if path.is_symlink()or not path.is_dir():raise ValueError('existing_real_paths_required')
    stat=BASE.stat()
    if stat.st_uid!=0 or stat.st_mode&0o022:raise ValueError('root_controlled_runtime_base_required')
    lock=open(STATE/'process.lock','r')
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        before=journal_state(STATE/'lane.sqlite3');dest=BASE/expected
        if dest.exists():verify(expected,dest);return dict(already_staged=True,bundle=expected,started=False,enabled=False,units_changed=False,delivery_enabled=False)
        run([sys.executable,'-B','-m','unittest','discover','-s',str(root/'tests'),'-q'],cwd=root,check=True)
        dest.mkdir(mode=0o755)
        for name in manifest['sha256']:
            out=dest/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes((root/name).read_bytes());out.chmod(0o644)
        for folder in dest.rglob('*'):
            if folder.is_dir():folder.chmod(0o755)
        (dest/'BUNDLE.json').write_bytes((root/'BUNDLE.json').read_bytes());(dest/'BUNDLE.json').chmod(0o644);verify(expected,dest)
        if before!=journal_state(STATE/'lane.sqlite3'):raise ValueError('journal_changed_do_not_start')
        return dict(staged=True,bundle=expected,previous_installed_bundle=OLD,started=False,enabled=False,units_changed=False,delivery_config_changed=False,scanner_changed=False,journal_preserved=True,activation=before['activation'],delivery_enabled=False)
    finally:lock.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--expected-bundle',required=True);a=p.parse_args();print(json.dumps(stage(a.expected_bundle)))
if __name__=='__main__':main()
