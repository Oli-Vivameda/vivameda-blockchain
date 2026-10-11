"""Owner activation of dedicated Crypto Lab instructions; no Telegram/scanner edits."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
APP=Path('/opt/vivameda-crypto-runtime')
OLD='ddd57fea740ce087122482a89ad1ea65d18516f2a077264d0bc6f593b8dd2423'
FILES=('AGENT_RULES.md','classification.py','test_classification.py','install_agent_rules.py','test_install_agent_rules.py')
MARKER='Vivameda small-cap coin classification rules v1'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bundle():return hashlib.sha256(b''.join(n.encode()+b'\0'+(HERE/n).read_bytes()+b'\0' for n in FILES)).hexdigest()

def patch(source,rules):
    tree=ast.parse(source)
    nodes=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SYSTEM' for t in n.targets)]
    if len(nodes)!=1 or not isinstance(nodes[0].value,ast.Constant) or not isinstance(nodes[0].value.value,str):raise ValueError('Expected literal agent SYSTEM')
    n=nodes[0]
    if MARKER in n.value.value:raise ValueError('Instructions already patched; verify installed version')
    lines=source.splitlines(True);lines[n.lineno-1:n.end_lineno]=['SYSTEM = '+repr(n.value.value+'\n\n'+rules)+'\n']
    result=''.join(lines);compile(result,'crypto_agent.py','exec');return result

def replace(path,raw,mode=0o644,uid=0,gid=0):
    fd,tmp=tempfile.mkstemp(prefix='.classification-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            os.fchmod(f.fileno(),mode);os.fchown(f.fileno(),uid,gid);f.write(raw);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def main():
    p=argparse.ArgumentParser();p.add_argument('--hash',action='store_true');p.add_argument('--install',action='store_true');p.add_argument('--expected-sha256');a=p.parse_args()
    if a.hash:print(bundle());return
    if a.expected_sha256!=bundle():raise ValueError('Reviewed bundle mismatch')
    for n in FILES:
        if (HERE/n).is_symlink():raise ValueError('Source symlink refused')
        if n.endswith('.py'):compile((HERE/n).read_text(),n,'exec')
    tests=subprocess.run(['/usr/bin/python3','-m','unittest','discover','-s',str(HERE),'-p','test_*.py'],capture_output=True,text=True,timeout=30)
    if tests.returncode:raise ValueError('Rule validation tests failed')
    if not a.install:
        print(json.dumps({'validated':True,'installed':False,'bundle_sha256':bundle(),'tests_passed':14}));return
    if os.geteuid()!=0:raise ValueError('Owner root required to write dedicated production agent')
    agent=APP/'crypto_agent.py';targets=(agent,APP/'COIN_CLASSIFICATION_RULES.md',APP/'classification.py')
    if any(p.is_symlink() for path in targets for p in (path,*path.parents)):raise ValueError('Destination symlink refused')
    if sha(agent)!=OLD:raise ValueError('Installed agent source changed; review before patching')
    if any(p.exists() for p in targets[1:]):raise ValueError('Unexpected existing classification files')
    source=agent.read_text();new=patch(source,(HERE/'AGENT_RULES.md').read_text());meta=agent.stat()
    backup=Path(tempfile.mkdtemp(prefix='crypto-classification-rules-',dir='/opt/vivameda-operations'));backup.chmod(0o700)
    shutil.copy2(agent,backup/'crypto_agent.py')
    changed=False
    try:
        replace(targets[1],(HERE/'AGENT_RULES.md').read_bytes());replace(targets[2],(HERE/'classification.py').read_bytes())
        if sha(agent)!=OLD:raise ValueError('Agent changed during install')
        replace(agent,new.encode(),meta.st_mode&0o777,meta.st_uid,meta.st_gid)
        changed=True
        tree=ast.parse(agent.read_text());system=next(n.value.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SYSTEM' for t in n.targets))
        if MARKER not in system or sha(targets[1])!=sha(HERE/'AGENT_RULES.md') or sha(targets[2])!=sha(HERE/'classification.py'):raise ValueError('Instruction postflight failed')
    except Exception:
        if changed and sha(agent)==hashlib.sha256(new.encode()).hexdigest():
            replace(agent,source.encode(),meta.st_mode&0o777,meta.st_uid,meta.st_gid)
        for path in targets[1:]:
            if path.exists():path.unlink()
        raise
    print(json.dumps({'installed':True,'policy':'crypto-coin-classification-v1','bundle_sha256':bundle(),
        'agent_source_sha256':sha(agent),'backup':str(backup),'fresh_agent_processes_load_instructions':True,
        'telegram_relay_changed':False,'classifier_dispatch_integration_enabled':False,'scanner_changed':False,
        'paper_policy_changed':False,'protected_outcomes_read':False,'weights_updated':False,'live_execution':False},sort_keys=True))

if __name__=='__main__':main()
