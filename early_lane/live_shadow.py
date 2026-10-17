"""Bounded integrated stream + frozen lane screening, unconditionally log-only."""
import argparse
import fcntl
import json
import multiprocessing
from pathlib import Path
import signal
import time
from core import canonical
from exporter import atomic
from live_service import LiveRunner
from core import RULES_SHA
import uuid
from stream_capture import run as capture_run

def run(state,input_path=None,duration=600,public_source_probe=False):
    if bool(input_path)==bool(public_source_probe):raise ValueError('choose_owner_feed_or_public_source_probe')
    if type(duration)is not int or not 1<=duration<=7200:raise ValueError('shadow_duration_1_to_7200_seconds')
    path=Path(state);path.mkdir(parents=True,exist_ok=True,mode=0o750)
    lock=open(path/'process.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    runner=None;child=None;running=True
    def stop(*_):
        nonlocal running
        running=False
    old={s:signal.signal(s,stop)for s in(signal.SIGTERM,signal.SIGINT)}
    session_id=uuid.uuid4().hex
    started=time.time();deadline=time.monotonic()+duration;cycles=0;valid=0;complete=0;selected=0;issues={};errors={};last_print=0
    try:
        runner=LiveRunner(path,session_id)
        child=multiprocessing.get_context('spawn').Process(target=capture_run,args=(path/'stream',duration,session_id),daemon=True);child.start()
        while running and time.monotonic()<deadline:
            cycles+=1
            try:
                if public_source_probe:
                    frame=dict(schema='early-lane-feed-v1',rules_sha256=RULES_SHA,exported_at=time.time(),source_live=False,launches=[],observations=[],coverage={'scope':'isolated public RPC creation source probe; no owner export','universal_launch_coverage':False})
                else:
                    with open(input_path)as src:frame=json.load(src)
                result=runner.poll(frame,log_only=True);valid+=1;complete+=result['fully_evaluated_candidates'];selected+=result['selected']
                for key,n in result['collection_issues'].items():issues[key]=issues.get(key,0)+n
                if time.time()-last_print>=20:
                    print(canonical(dict(status='LIVE_ISOLATION_SHADOW',cycle=cycles,**result,history=runner.collector.metrics,telegram_sent=0)),flush=True);last_print=time.time()
            except (OSError,ValueError,KeyError,TypeError,IndexError)as exc:
                reason=str(exc)[:120]if isinstance(exc,ValueError)else type(exc).__name__;errors[reason]=errors.get(reason,0)+1
            if not child.is_alive()and time.monotonic()<deadline:
                errors['capture_process_stopped']=errors.get('capture_process_stopped',0)+1;break
            # Signals interrupt the short wait; no long blocking sleep.
            until=min(deadline,time.monotonic()+5)
            while running and time.monotonic()<until:time.sleep(min(.2,max(0,until-time.monotonic())))
    finally:
        if child:
            if child.is_alive():child.terminate()
            child.join(timeout=20)
            if child.is_alive():child.kill();child.join(timeout=5)
        result=dict(status='LIVE_ISOLATION_SHADOW_FINISHED',started_at=started,finished_at=time.time(),cycles=cycles,valid_polls=valid,fully_evaluated_candidate_polls=complete,selected=selected,collection_issues=issues,errors=errors,telegram_sent=0,delivery_enabled=False,history=runner.collector.metrics if runner else {},screening_ready=False,session_id=session_id,public_source_probe=public_source_probe,workers=runner.collector.worker_metrics if runner else {},rpc_calls=runner.collector.rpc.calls if runner else {},rpc_denied=runner.collector.rpc.denied if runner else {},queues=runner.collector.queue_summary(time.time())if runner else {},discovery=runner.discovery_counts if runner else {})
        atomic(path/'live_screening_receipt.json',result)
        if runner:
            runner.collector.cache.close();runner.j.db.close()
            for h in runner.log.handlers[:]:h.close();runner.log.removeHandler(h)
        lock.close()
        for s,h in old.items():signal.signal(s,h)
    print(canonical(result),flush=True);return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--state-dir',required=True);p.add_argument('--input');p.add_argument('--public-source-probe',action='store_true');p.add_argument('--duration',type=int,default=600);a=p.parse_args();run(a.state_dir,a.input,a.duration,a.public_source_probe)
if __name__=='__main__':main()
