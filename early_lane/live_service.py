"""Session-scoped live discovery, independently budgeted catch-up and pricing."""
from pathlib import Path
from service import Runner
from live_history import LiveCollector
from outcomes import HORIZONS

class LiveRunner(Runner):
    def __init__(self,state,session_id,http=None):
        p=Path(state);p.mkdir(mode=0o750,parents=True,exist_ok=True)
        collector=LiveCollector(p/'live_rpc_cache.sqlite3',p/'stream',session_id,http)
        try:super().__init__(state,stream=True,collector=collector)
        except BaseException:collector.cache.close();raise
        self.discovery_counts={}
    def prepare_launches(self,frame,now):
        exported=super().prepare_launches(frame,now)
        discovered=self.collector.discoveries(now)
        rows={x['mint']:dict(x,discovery_source='owner_export')for x in exported}
        for x in discovered:
            if x['mint']not in rows:rows[x['mint']]=dict(x,discovery_source='public_rpc_creation')
        self.collector.live_mints={x['mint']for x in discovered}
        self.discovery_counts=dict(exported=len(exported),current_session=len(discovered),
            stream_only=sum(x['mint']not in {r['mint']for r in exported}for x in discovered),
            union=len(rows),universal_launch_coverage=False)
        return list(rows.values())
    def birth_priority(self):return True
    def market_batch(self,watched,existing,now,priority):
        # Due outcome checkpoints precede discovery, then reserve six of thirty
        # slots for catch-up price coverage. Remaining slots can serve live work.
        urgent=[]
        for mint,c in existing.items():
            done={r['body']['horizon_min']for r in self.j.rows('checkpoint',mint)}
            if any(h not in done and abs(c['at']+h*60-now)<=120 for h in HORIZONS):
                if mint in watched:urgent.append(watched[mint])
        chosen=sorted(urgent,key=priority)[:30];seen={x['mint']for x in chosen}
        available=[x for x in sorted(watched.values(),key=priority)if x['mint']not in seen]
        live=[x for x in available if x['mint']in self.collector.live_mints]
        catchup=[x for x in available if x['mint']not in self.collector.live_mints]
        room=30-len(chosen);reserve=min(6,len(catchup),room)
        chosen+=live[:room-reserve];seen={x['mint']for x in chosen}
        chosen+=catchup[:min(reserve,30-len(chosen))];seen.update(x['mint']for x in chosen)
        chosen+=[x for x in available if x['mint']not in seen][:30-len(chosen)]
        return chosen
    def poll(self,frame,now=None,fixtures=False,log_only=True):
        if log_only is not True:raise ValueError('live_isolation_shadow_only')
        result=super().poll(frame,now,fixtures,True)
        result.update(discovery=self.discovery_counts,workers=self.collector.worker_metrics,
            rpc_calls=self.collector.rpc.calls.copy(),rpc_denied=self.collector.rpc.denied.copy(),
            rpc_cycle_remaining=self.collector.rpc.quotas.copy(),delivery_enabled=False)
        return result
