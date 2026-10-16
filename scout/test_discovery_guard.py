import ast, hashlib, json, logging, math, re, sqlite3, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch as mock
import requests

ROOT = Path(__file__).resolve().parent

def function_source(source, name):
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.get_source_segment(source, node)

def functions(source):
    return {n.name: ast.dump(n, include_attributes=False)
            for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)}

def discovery_source(source):
    nodes = []
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("discovery_"):
            nodes.append(ast.get_source_segment(source, node))
        elif isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id.startswith("DISCOVERY_")
                for target in node.targets):
            nodes.append(ast.get_source_segment(source, node))
    return "\n\n".join(nodes)

patch = SimpleNamespace(ROOT=ROOT, SOURCE=ROOT / "early_scout.py",
                        function_source=function_source, functions=functions)

class Clock:
    def __init__(self,now=10000):self.now=now
    def time(self):return self.now
class Response:
    def __init__(self,body):self.body=body
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,n):return self.body[:n]
def baseline():
    return patch.SOURCE.read_text()

class GuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=baseline()
        cls.candidate=cls.original
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);(self.base/"data").mkdir()
        self.clock=Clock();self.sent=[];self.requests=[]
        self.ns=dict(Path=Path,BASE=self.base,json=json,math=math,re=re,logging=logging,
                     sqlite3=sqlite3,requests=requests,time=self.clock,DB_PATH=":memory:",
                     PUMP_URL="https://frontend-api-v3.pump.fun/coins")
        for name in ("db","upsert_pump"):
            exec(patch.function_source(self.original,name),self.ns)
        exec(discovery_source(self.candidate),self.ns)
        exec(patch.function_source(self.candidate,"pump_rows"),self.ns)
        self.c=self.ns["db"]();self.addCleanup(self.c.close)
        self.state=self.ns["discovery_new"](self.clock.now)
        self.state["scan_watermark_ms"]=9700000
        self.ns["telegram"]=self.sent.append
    def row(self,age=10,letter="A",**changes):
        d=dict(mint=letter*32,created_timestamp=int((self.clock.now-age)*1000),
               last_trade_timestamp=int(self.clock.now*1000),market_cap_usd=100000,ath_market_cap=120000)
        d.update(changes);return d
    def fetcher(self,creation=None,trade=None,extra=None):
        def fetch(sort,offset=0):
            self.requests.append((sort,offset))
            value=extra if offset else creation if sort=="created_timestamp" else trade
            if isinstance(value,Exception):raise value
            return value if value is not None else [self.row(letter="B")]
        self.ns["pump_rows"]=fetch
    def cycle(self):
        self.ns["discovery_cycle"](self.c,self.state)
    def count(self):
        return self.c.execute("SELECT count(*) FROM launches").fetchone()[0]
    def http(self,status):
        r=requests.Response();r.status_code=status
        return requests.HTTPError("hidden-provider-url",response=r)
    def test_save_creation_when_trade_fails(self):
        self.fetcher(creation=[self.row()],trade=self.http(500));self.cycle()
        self.assertEqual(self.count(),1)
        self.assertEqual(self.state["feeds"]["last_trade_timestamp"]["error"],"HTTP_OTHER")
    def test_save_trade_when_creation_fails(self):
        self.fetcher(creation=ValueError("schema"),trade=[self.row()]);self.cycle()
        self.assertEqual(self.count(),1)
        self.assertGreater(self.state["feeds"]["last_trade_timestamp"]["last_success"],0)
    def test_rate_limit_stops_further_host_requests(self):
        self.fetcher(creation=self.http(429));self.cycle()
        self.assertEqual(self.requests,[("created_timestamp",0)])
        self.clock.now+=100;self.cycle()
        self.assertEqual(len(self.requests),1)
        self.assertEqual(self.state["host_retry_at"],10300)
    def test_403_cooldown(self):
        self.fetcher(creation=self.http(403));self.cycle()
        self.assertEqual(self.state["host_retry_at"],10300)
    def test_second_feed_rate_limit_keeps_first_commit(self):
        self.fetcher(creation=[self.row()],trade=self.http(429));self.cycle()
        self.assertEqual(self.count(),1)
        self.assertEqual(len(self.requests),2)
    def test_no_error_suppresses_market_work_in_main(self):
        source=patch.function_source(self.candidate,"main")
        self.assertIn('logging.error("DISCOVERY_GUARD_ERROR',source)
        self.assertLess(source.index("discovery_cycle"),source.index("enrich_and_score"))
        self.assertNotIn("continue",source)
    def test_bootstrap_anchors_forward_capture_without_claiming_past_coverage(self):
        self.state["scan_watermark_ms"]=0
        self.fetcher(creation=[self.row()],trade=[self.row()])
        self.cycle()
        self.assertEqual(len(self.requests),2)
        self.assertEqual(self.state["bootstrap_at"],10000)
        self.assertFalse(self.state["historical_coverage_asserted"])
        self.assertIsNone(self.state["pending"])
    def test_catchup_follows_actual_page_size_and_overlap(self):
        head=[self.row(age=10+i,letter="A" if i==0 else "B") for i in range(70)]
        head=[dict(r,mint=("A"*30+("B" if i<35 else "C")+("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"[i%35]))) for i,r in enumerate(head)]
        self.fetcher(creation=head,trade=[self.row(letter="D")],
                     extra=[self.row(age=80,letter="E"),self.row(age=100,letter="F")])
        self.cycle()
        self.assertIn(("created_timestamp",60),self.requests)
        self.assertEqual(len(self.requests),3)
        self.assertEqual(self.state["pending"]["offset"],61)
    def test_catchup_one_page_per_pass_and_30_second_budget(self):
        self.fetcher(creation=[self.row()],trade=[self.row()],extra=[self.row(age=100,letter="C")])
        self.cycle();n=len([r for r in self.requests if r[1]])
        self.clock.now+=20;self.cycle()
        self.assertEqual(len([r for r in self.requests if r[1]]),n)
    def test_catchup_gap_not_silently_cleared_on_offset_bound(self):
        self.state["pending"]=dict(target_ms=1000,anchor_ms=9990000,oldest_ms=9980000,offset=10001,started_at=10000)
        self.ns["discovery_catchup"](self.c,self.state,10000)
        self.assertEqual(self.state["coverage_gap"],"offset_bound")
        self.assertEqual(self.requests,[])
    def test_catchup_stops_at_one_hour_runtime_bound(self):
        self.state["pending"]=dict(target_ms=1000,anchor_ms=9990000,oldest_ms=9980000,offset=60,started_at=10000)
        self.ns["discovery_catchup"](self.c,self.state,13601)
        self.assertEqual(self.state["coverage_gap"],"catchup_time_bound")
    def test_repeated_page_detected(self):
        self.state["pending"]=dict(target_ms=9000000,anchor_ms=9990000,oldest_ms=9980000,offset=60,started_at=10000)
        self.fetcher(extra=[self.row(age=5)])
        self.ns["discovery_catchup"](self.c,self.state,10000)
        self.assertEqual(self.state["coverage_gap"],"pagination_no_progress")
        self.assertEqual(self.count(),0)
    def test_catchup_completion_advances_to_original_anchor_only(self):
        self.state["pending"]=dict(target_ms=9500000,anchor_ms=9900000,oldest_ms=9800000,offset=60,started_at=10000)
        self.fetcher(extra=[self.row(age=501)])
        self.ns["discovery_catchup"](self.c,self.state,10000)
        self.assertIsNone(self.state["pending"])
        self.assertEqual(self.state["scan_watermark_ms"],9900000)
        self.assertEqual(self.state["recovery_count"],1)
    def test_long_outage_gap_remains_visible_while_recent_catchup_runs(self):
        self.clock.now=50000
        self.state["scan_watermark_ms"]=1000000
        self.ns["discovery_creation_head"](self.state,[49990000,49980000],50000)
        self.assertEqual(self.state["coverage_gap"],"outside_6h_window")
        self.assertIsNotNone(self.state["pending"])
        self.assertEqual(self.state["pending"]["target_ms"],28400000)
    def test_old_unresolved_gap_does_not_prevent_new_catchup(self):
        self.state["coverage_gap"]="offset_bound"
        self.state["pending"]=dict(target_ms=9500000,anchor_ms=9900000,oldest_ms=9800000,offset=60,started_at=10000)
        self.fetcher(extra=[self.row(age=501)])
        self.ns["discovery_catchup"](self.c,self.state,10000)
        self.assertIsNone(self.state["pending"])
        self.assertEqual(self.state["coverage_gap"],"offset_bound")
        self.assertEqual(self.count(),1)
    def test_catchup_failure_keeps_head_rows_and_does_not_falsify_watermark(self):
        self.fetcher(creation=[self.row()],trade=[self.row()],extra=self.http(429))
        self.cycle()
        self.assertEqual(self.count(),1)
        self.assertEqual(self.state["scan_watermark_ms"],9700000)
        self.assertIsNotNone(self.state["pending"])
    def test_first_seen_is_receipt_not_creation_or_backfill_time(self):
        row=self.row(age=2000)
        self.ns["discovery_ingest"](self.c,[row],"created_timestamp",self.state,10000)
        first=self.c.execute("SELECT first_seen,created_ts FROM launches").fetchone()
        self.assertEqual(first,(10000000,row["created_timestamp"]))
        self.clock.now+=60
        self.ns["discovery_ingest"](self.c,[row],"created_timestamp",self.state,10060)
        self.assertEqual(self.c.execute("SELECT first_seen FROM launches").fetchone()[0],10000000)
    def test_delay_buckets_unique_new_tokens_only(self):
        rows=[self.row(age=10),self.row(age=2000,letter="B"),self.row(age=22000,letter="C")]
        # Advance clock so every synthetic creation time remains positive.
        self.clock.now=40000
        rows=[self.row(age=10),self.row(age=2000,letter="B"),self.row(age=22000,letter="C")]
        self.ns["discovery_ingest"](self.c,rows,"last_trade_timestamp",self.state,40000)
        self.ns["discovery_ingest"](self.c,rows,"last_trade_timestamp",self.state,40000)
        f=self.state["feeds"]["last_trade_timestamp"]
        self.assertEqual((f["inserted_total"],f["within_30m_total"],f["within_6h_total"],f["late_over_6h_total"]),(3,1,1,1))
    def test_malformed_trade_row_does_not_discard_valid_trade_rows(self):
        bad=self.row(letter="C",market_cap_usd=-1)
        self.fetcher(creation=[self.row()],trade=[self.row(letter="B"),bad])
        self.cycle()
        self.assertEqual(self.count(),2)
        f=self.state["feeds"]["last_trade_timestamp"]
        self.assertEqual(f["last_rejected_rows"],1)
        self.assertEqual(f["partial_since"],10000)
        self.assertGreater(f["last_success"],0)
        self.assertTrue(any("quarantined" in p for p in self.ns["discovery_problems"](self.state,10181)))
    def test_quality_warning_clears_only_after_valid_head(self):
        self.state["feeds"]["last_trade_timestamp"]["partial_since"]=9800
        self.fetcher(creation=[self.row()],trade=[self.row(letter="B")])
        self.cycle()
        self.assertEqual(self.state["feeds"]["last_trade_timestamp"]["partial_since"],0)
    def test_malformed_creation_rows_leave_visible_gap_but_save_valid_rows(self):
        self.fetcher(creation=[self.row(),self.row(letter="C",market_cap_usd=-1)],trade=[self.row(letter="B")],extra=ValueError("unavailable"))
        self.cycle()
        self.assertGreaterEqual(self.count(),2)
        self.assertEqual(self.state["coverage_gap"],"invalid_creation_rows")
    def test_all_invalid_rows_do_not_refresh_freshness(self):
        self.fetcher(creation=[self.row(market_cap_usd=-1)],trade=[self.row(letter="B")])
        self.cycle()
        self.assertEqual(self.state["feeds"]["created_timestamp"]["last_nonempty"],0)
        self.assertEqual(self.count(),1)
    def test_malformed_page_is_atomic(self):
        rows=[self.row(),self.row(letter="B",market_cap_usd="invalid")]
        with self.assertRaises(ValueError):self.ns["discovery_ingest"](self.c,rows,"created_timestamp",self.state,10000)
        self.assertEqual(self.count(),0)
    def test_invalid_times_and_market_values_fail_closed(self):
        for changes in ({"created_timestamp":10000001},{"created_timestamp":True},
                        {"market_cap_usd":float("nan")},{"last_trade_timestamp":10000001}):
            with self.assertRaises(ValueError):
                self.ns["discovery_validate_page"]([self.row(**changes)],"created_timestamp",10000)
    def test_creation_sort_order_checked(self):
        with self.assertRaises(ValueError):
            self.ns["discovery_validate_page"]([self.row(age=50),self.row(age=10,letter="B")],"created_timestamp",10000)
    def test_unknown_market_and_trade_fields_preserved(self):
        r=self.row(market_cap_usd=None,last_trade_timestamp=None)
        self.ns["discovery_ingest"](self.c,[r],"created_timestamp",self.state,10000)
        self.assertIsNone(self.c.execute("SELECT current_mc FROM launches").fetchone()[0])
    def test_stale_creation_head_is_not_healthy(self):
        self.fetcher(creation=[self.row(age=181)],trade=[self.row(letter="B")])
        self.cycle()
        self.assertEqual(self.state["feeds"]["created_timestamp"]["last_nonempty"],0)
        self.assertEqual(self.count(),1)
    def test_warning_after_three_minutes_and_hourly_repeat(self):
        self.clock.now+=181;self.ns["discovery_notify"](self.state,self.clock.now)
        self.assertEqual(len(self.sent),1)
        self.assertIn("DISCOVERY WARNING",self.sent[0])
        self.ns["discovery_notify"](self.state,self.clock.now+601)
        self.assertEqual(len(self.sent),1)
        self.ns["discovery_notify"](self.state,self.clock.now+3601)
        self.assertEqual(len(self.sent),2)
    def test_short_failure_does_not_send_warning(self):
        self.ns["discovery_notify"](self.state,10100)
        self.assertEqual(self.sent,[])
    def test_recovery_only_when_catchup_complete_and_throttled(self):
        self.ns["discovery_notify"](self.state,10181)
        self.assertEqual(len(self.sent),1)
        for f in self.state["feeds"].values():f["last_nonempty"]=10800
        self.state["pending"]=dict(target_ms=1,anchor_ms=2,oldest_ms=2,offset=1,started_at=10800)
        self.ns["discovery_notify"](self.state,10800)
        self.assertEqual(len(self.sent),1)
        self.state["pending"]=None
        self.ns["discovery_notify"](self.state,10800)
        self.assertEqual(len(self.sent),2)
        self.assertIn("RECOVERY",self.sent[-1])
    def test_notification_failure_cannot_flood_each_pass_or_restart(self):
        def fail(text):raise requests.RequestException("secret should never appear")
        self.ns["telegram"]=fail
        self.ns["discovery_notify"](self.state,10181)
        with mock.dict(self.ns,telegram=self.sent.append):
            self.ns["discovery_notify"](self.state,10201)
        self.assertEqual(self.sent,[])
        self.assertEqual(self.ns["discovery_load"](10201)["last_notice_attempt"],10181)
    def test_no_notification_when_throttle_cannot_be_persisted(self):
        with mock("os.replace",side_effect=OSError("disk")):
            self.ns["discovery_notify"](self.state,10181)
        self.assertEqual(self.sent,[])
    def test_state_roundtrip_and_no_token_identities_in_health(self):
        self.ns["discovery_save"](self.state)
        restored=self.ns["discovery_load"](10000)
        self.assertEqual(restored["feeds"],self.state["feeds"])
        raw=(self.base/"data/discovery_health.json").read_text()
        self.assertNotIn("mint",raw)
    def test_corrupt_state_never_manufactures_healthy_history(self):
        (self.base/"data/discovery_health.json").write_text("{broken")
        restored=self.ns["discovery_load"](10000)
        self.assertEqual(restored["coverage_gap"],"state_unreadable")
        self.assertEqual(restored["feeds"]["created_timestamp"]["last_success"],0)
    def test_state_persists_retry_and_catchup_across_restart(self):
        self.state["host_retry_at"]=10200
        self.state["pending"]=dict(target_ms=1000,anchor_ms=9990000,oldest_ms=9980000,offset=120,started_at=9990)
        self.ns["discovery_save"](self.state)
        restored=self.ns["discovery_load"](10000)
        self.assertEqual(restored["pending"],self.state["pending"])
        self.assertEqual(restored["host_retry_at"],10200)
    def test_no_protected_table_access(self):
        queries=[];self.c.set_trace_callback(queries.append)
        self.fetcher(creation=[self.row()],trade=[self.row()],extra=ValueError("unavailable"));self.cycle()
        self.assertFalse(any("pl_" in q or "fc_" in q or "v2_" in q for q in queries))
    def test_screening_study_telegram_functions_identical(self):
        contract=json.loads((ROOT/"discovery_function_contract.json").read_text())
        actual=functions(self.candidate)
        for name, expected in contract["unchanged_functions"].items():
            self.assertIn(name,actual)
            self.assertEqual(hashlib.sha256(actual[name].encode()).hexdigest(),expected,name)
    def test_source_matches_verified_discovery_release(self):
        contract=json.loads((ROOT/"discovery_function_contract.json").read_text())
        self.assertEqual(hashlib.sha256(self.candidate.encode()).hexdigest(),contract["published_scout_sha256"])
    def test_http_offset_validation(self):
        for sort,offset in [("created_timestamp",-1),("created_timestamp",10001),("last_trade_timestamp",70),("created_timestamp",True)]:
            with self.assertRaises(ValueError):self.ns["pump_rows"](sort,offset)
    def test_http_pagination_keeps_original_transport_and_fields(self):
        row=self.row(age=100)
        with mock("urllib.request.urlopen",return_value=Response(json.dumps([row]).encode())) as get:
            self.assertEqual(self.ns["pump_rows"]("created_timestamp",70),[row])
            self.assertIn("offset=70",get.call_args.args[0].full_url)
            self.assertIn("includeNsfw=false",get.call_args.args[0].full_url)
    def test_empty_head_does_not_refresh_nonempty_health(self):
        self.fetcher(creation=[],trade=[self.row()])
        self.cycle()
        self.assertEqual(self.state["feeds"]["created_timestamp"]["last_nonempty"],0)
        self.assertEqual(self.state["feeds"]["created_timestamp"]["last_success"],10000)
if __name__=="__main__":unittest.main()
