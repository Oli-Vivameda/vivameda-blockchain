#!/usr/bin/env python3
"""Dedicated paper-only daemon and local report/control CLI."""
import argparse
import fcntl
import json
import pathlib
import signal
import time
from core import Ledger, dumps
from feed import Feed, Rpc, Quotes, Risk

def main():
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['run', 'once', 'report', 'pause'])
    p.add_argument('--config', default=str(pathlib.Path(__file__).with_name('config.json')))
    p.add_argument('--watchlist', default=str(pathlib.Path(__file__).with_name('watchlist.json')))
    p.add_argument('--state-dir', required=True)
    args = p.parse_args()
    state = pathlib.Path(args.state_dir)
    state.mkdir(parents=True, exist_ok=True)
    if args.command in ('run', 'once'):
        lock = open(state / 'daemon.lock', 'a')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    l = Ledger(state / 'paper.sqlite3', json.loads(pathlib.Path(args.config).read_text()), json.loads(pathlib.Path(args.watchlist).read_text()))
    if args.command == 'report':
        print(dumps(l.report()))
        return
    if args.command == 'pause':
        with l.db:
            l.db.execute('UPDATE accounts SET paused=1')
            l.log('operator_pause_entries', {})
        print('Entries paused durably; exits remain managed. No automatic resume command.')
        return
    running = True
    def stop(*_):
        nonlocal running
        running = False
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    rpc = Rpc(l.c['rpc_url'])
    feed, quotes, risk = Feed(l, rpc), Quotes(l.c), Risk(rpc)
    with l.db:
        l.log('service_start', {'paper_only': True, 'binding': l.get('binding')})
    failures = 0
    while running:
        started = time.time()
        health = {'heartbeat': started, 'mode': l.report(started)['status'], 'wallets': len(l.w['wallets']), 'quote_access': bool(l.c['quote_access_authorized_free'] and l.c['quote_url'])}
        try:
            # Check the public feed even while waiting, at most once per minute.
            prior = l.get('health') or {}
            if started - prior.get('last_feed_success', 0) >= 60:
                rpc.call('getHealth')
                health['last_feed_success'] = time.time()
                health['probe_latency_s'] = time.time() - started
            else:
                health['last_feed_success'] = prior.get('last_feed_success')
            feed.poll()
            l.maintain(quotes)
            l.process(quotes, risk)
            failures = 0
            health['last_successful_poll'] = time.time() if l.w['wallets'] else None
        except Exception as exc:
            failures += 1
            health.update(feed_error=type(exc).__name__, consecutive_failures=failures)
            with l.db:
                l.log('feed_gap_or_runtime_error', {'error_type': type(exc).__name__, 'since': started})
        health['cycle_s'] = time.time() - started
        with l.db:
            l.set('health', health)
        print(dumps(health), flush=True)
        if args.command == 'once':
            break
        # Bounded backoff: no provider hammering during 429s or outages.
        delay = min(60, l.c['poll_s'] * 2 ** min(failures, 4))
        until = time.monotonic() + delay
        while running and time.monotonic() < until:
            time.sleep(min(1, max(0, until - time.monotonic())))
    with l.db:
        l.log('service_stop', {})
    l.db.close()
if __name__ == '__main__':
    main()
