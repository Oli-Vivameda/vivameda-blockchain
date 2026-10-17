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
from service import Runner
from stream_capture import run as capture_run

def run(state,input_path,duration=600):
    if type(duration)is not int or not 1<=duration<=7200:raise ValueError('shadow_duration_1_to_7200_seconds')
    path=Path(state);path.mkdir(parents=True,exist_ok=True,mode=0o750)
    lock=open(path/'process.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    runner=None;child=None;running=True
    def stop(*_):
        nonlocal running
        running=False
    old={s:signal.signal(s,stop)for s in(signal.SIGTERM,signal.SIGINT)}
    started=time.time();deadline=time.monotonic()+duration;cycles=0;valid=0;complete=0;selected=0;issues={};errors={};last_print=0
    try:
        runner=Runner(path,stream=True)
        child=multiprocessing.get_context('spawn').Process(target=capture_run,args=(path/'stream',duration),daemon=True);child.start()
        while running and time.monotonic()<deadline:
            cycles+=1
            try:
                with open(input_path)as src:frame=json.load(src)
                result=runner.poll(frame,log_only=True);valid+=1;complete+=result['fully_evaluated_candidates'];selected+=result['selected']
                for key,n in result['collection_issues'].items():issues[key]=issues.get(key,0)+n
                if time.time()-last_print>=20:
                    print(canonical(dict(status='STREAM_SCREENING_SHADOW',cycle=cycles,**result,history=runner.collector.metrics,telegram_sent=0)),flush=True);last_print=time.time()
            except (OSError,ValueError,KeyError,TypeError,IndexError)as exc:
                reason=str(exc)[:120]if isinstance(exc,ValueError)else type(exc).__name__;errors[reason]=errors.get(reason,0)+1
            if not child.is_alive():
                errors['capture_process_stopped']=errors.get('capture_process_stopped',0)+1;break
            # Signals interrupt the short wait; no long blocking sleep.
            until=min(deadline,time.monotonic()+5)
            while running and time.monotonic()<until:time.sleep(min(.2,max(0,until-time.monotonic())))
    finally:
        if child:
            if child.is_alive():child.terminate()
            child.join(timeout=20)
            if child.is_alive():child.kill();child.join(timeout=5)
        result=dict(status='STREAM_SCREENING_SHADOW_FINISHED',started_at=started,finished_at=time.time(),cycles=cycles,valid_polls=valid,fully_evaluated_candidate_polls=complete,selected=selected,collection_issues=issues,errors=errors,telegram_sent=0,delivery_enabled=False,history=runner.collector.metrics if runner else {},screening_ready=False)
        atomic(path/'stream_screening_receipt.json',result)
        if runner:
            runner.collector.cache.close();runner.j.db.close()
            for h in runner.log.handlers[:]:h.close();runner.log.removeHandler(h)
        lock.close()
        for s,h in old.items():signal.signal(s,h)
    print(canonical(result),flush=True);return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--state-dir',required=True);p.add_argument('--input',required=True);p.add_argument('--duration',type=int,default=600);a=p.parse_args();run(a.state_dir,a.input,a.duration)
if __name__=='__main__':main()
