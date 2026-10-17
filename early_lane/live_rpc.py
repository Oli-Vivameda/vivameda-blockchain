"""One shared free RPC budget/cooldown; catch-up cannot consume live capacity."""
from sources import Rpc,BudgetExceeded
class LaneRpc(Rpc):
    LIMITS={'market':4,'live':7,'catchup':1}
    def __init__(self,cache,http=None):
        super().__init__(cache,http);self.lane='market';self.quotas=dict.fromkeys(self.LIMITS,0)
        self.calls=dict.fromkeys(self.LIMITS,0);self.denied=dict.fromkeys(self.LIMITS,0)
    def budget(self,n=12):
        if n!=12:raise ValueError('fixed_shared_rpc_budget_required')
        super().budget(n);self.quotas=dict(self.LIMITS);self.lane='market'
    def call(self,method,params=None):
        if self.lane not in self.LIMITS:raise ValueError('unknown_collection_lane')
        if self.quotas[self.lane]<=0:
            self.denied[self.lane]+=1;raise BudgetExceeded(self.lane+'_rpc_budget')
        before=self.remaining
        try:return super().call(method,params)
        finally:
            used=before-self.remaining
            if used>0:
                self.quotas[self.lane]-=used;self.calls[self.lane]+=used
