"""Root-authenticated, fail-closed Telegram transport. No autonomous sends."""
import argparse
import contextlib
import email.utils
import fcntl
import http.client
import json
import math
import os
from pathlib import Path
import pwd
import re
import socket
import sqlite3
import ssl
import stat
import struct
import time

PROTOCOL = 'vivameda-early-lane-send-v1'
CONFIG = Path('/etc/vivameda-early-lane/delivery.json')
CREDENTIAL = Path('/opt/vivameda-crypto-early-scout/credentials.json')
STATE = Path('/var/lib/vivameda-early-lane-sender')
SOCKET = Path('/run/vivameda-early-lane-sender/sender.sock')
SECRET = re.compile(r'\b[0-9]{5,}:[A-Za-z0-9_-]{20,}\b')
TEST_TEXT = 'EARLY LANE CHANNEL TEST. Owner requested; not a token alert. Delivery remains disabled.'

class Refused(Exception):
    """Only fixed public reason codes may be returned to clients."""

def credential_metadata_valid(st):
    """Trust the existing scanner account without changing its private file."""
    scanner_uid = pwd.getpwnam('vivameda-scout').pw_uid
    return (stat.S_ISREG(st.st_mode) and st.st_uid in (0, scanner_uid)
            and not st.st_mode & 0o077)

def secure_json(path, *, private=False):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        st = os.fstat(stream.fileno())
        valid = credential_metadata_valid(st) if private else (stat.S_ISREG(st.st_mode) and st.st_uid == 0 and not st.st_mode & 0o022)
        if not valid:
            raise Refused('unsafe_protected_file')
        raw = stream.read(16385)
    if len(raw) > 16384:
        raise Refused('root_file_too_large')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise Refused('invalid_root_file')
    return value

def channel_id(value, new=False):
    s = str(value)
    pattern = r'-100[0-9]+' if new else r'-?[1-9][0-9]*'
    if not re.fullmatch(pattern, s) or abs(int(s)) > 2**53 - 1:
        raise Refused('invalid_chat_id')
    return s

def authorize(channel, *, owner_test=False):
    config = secure_json(CONFIG)
    wanted = channel_id(config.get('channel'), new=True)
    if channel_id(channel, new=True) != wanted:
        raise Refused('wrong_chat')
    if not owner_test:
        confirmed = config.get('confirmed_at')
        if (config.get('new_channel_confirmed') is not True or
                not isinstance(confirmed, (int, float)) or isinstance(confirmed, bool) or
                not math.isfinite(confirmed) or confirmed <= 0 or config.get('socket') != str(SOCKET)):
            raise Refused('delivery_not_confirmed')
    elif os.geteuid() != 0:
        raise Refused('owner_required')
    credential = secure_json(CREDENTIAL, private=True)  # Runtime only; never copied to state.
    if wanted == channel_id(credential.get('chat_id')):
        raise Refused('scanner_chat_forbidden')
    token = credential.get('bot_token')
    if not isinstance(token, str) or not re.fullmatch(r'[0-9]{5,}:[A-Za-z0-9_-]{20,}', token):
        raise Refused('credential_invalid')
    return token

def validate(request):
    if not isinstance(request, dict) or set(request) != {'protocol', 'channel', 'text', 'parse_mode', 'idempotency_key'}:
        raise Refused('invalid_request')
    if request['protocol'] != PROTOCOL or request['parse_mode'] != 'HTML':
        raise Refused('invalid_protocol')
    channel_id(request['channel'], new=True)
    text = request['text']; key = request['idempotency_key']
    if (not isinstance(text, str) or not 1 <= len(text) <= 4096 or '\x00' in text or
            any(0xd800 <= ord(c) <= 0xdfff for c in text) or SECRET.search(text)):
        raise Refused('invalid_text')
    if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,200}', key) or SECRET.search(key):
        raise Refused('invalid_event_key')

def retry_delay(headers, data, now):
    values = [1.0]
    try:
        n = float(data.get('parameters', {}).get('retry_after', 0))
        if math.isfinite(n): values.append(n)
    except (AttributeError, TypeError, ValueError, OverflowError):
        pass
    value = headers.get('retry-after', '')
    try:
        n = float(value)
        if math.isfinite(n): values.append(n)
    except (TypeError, ValueError, OverflowError):
        try:
            values.append(email.utils.parsedate_to_datetime(value).timestamp() - now)
        except (TypeError, ValueError, OverflowError):
            pass
    return math.ceil(max(values))

class Telegram:
    def __init__(self, factory=None):
        self.factory = factory or (lambda: http.client.HTTPSConnection('api.telegram.org', timeout=6, context=ssl.create_default_context()))

    def send(self, token, channel, text):
        """Return classification, whitelisted receipt, delay. Never return API errors."""
        conn = None
        try:
            conn = self.factory()
            body = json.dumps({'chat_id': channel, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': True}).encode()
            conn.request('POST', '/bot' + token + '/sendMessage', body, {'Content-Type': 'application/json'})
            response = conn.getresponse()
            raw = response.read(65537)
            headers = {k.lower(): v for k, v in response.getheaders()}
            try:
                data = json.loads(raw) if len(raw) <= 65536 else {}
            except (ValueError, UnicodeError):
                data = {}
            if not isinstance(data, dict): data = {}
            if response.status == 429 or data.get('error_code') == 429:
                return 'retry', None, retry_delay(headers, data, time.time())
            if response.status == 200 and data.get('ok') is True:
                result = data.get('result', {})
                if not isinstance(result, dict): return 'ambiguous', None, 0
                chat = result.get('chat', {})
                if not isinstance(chat, dict): return 'ambiguous', None, 0
                mid = result.get('message_id'); date = result.get('date')
                if (type(mid) is int and mid > 0 and type(date) is int and date > 0 and
                        str(chat.get('id')) == channel):
                    return 'sent', {'chat_id': channel, 'message_id': mid, 'date': date}, 0
                return 'ambiguous', None, 0
            # A definite rejection can safely retry after an operator fixes permissions.
            if data.get('ok') is False and data.get('error_code') in (400, 401, 403):
                return 'retry', None, 60
            return 'ambiguous', None, 0
        except Exception:
            # URL/HTTP exception strings can contain the token. Never expose them.
            return 'ambiguous', None, 0
        finally:
            if conn is not None:
                with contextlib.suppress(Exception): conn.close()

class Journal:
    def __init__(self, path):
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS events (
                event_key TEXT PRIMARY KEY, channel TEXT NOT NULL, text TEXT NOT NULL,
                kind TEXT NOT NULL, created REAL NOT NULL, status TEXT NOT NULL,
                receipt TEXT, retry_at REAL NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value REAL NOT NULL);
        ''')
        # A crash may have happened after Telegram accepted but before receipt commit.
        self.db.execute("UPDATE events SET status='ambiguous' WHERE status='inflight'")

    def close(self): self.db.close()

class Engine:
    def __init__(self, journal, api=None, authorization=authorize, clock=time.time):
        self.journal = journal; self.api = api or Telegram(); self.authorization = authorization; self.clock = clock

    def handle(self, request, *, owner_test=False):
        try:
            validate(request)
            channel = channel_id(request['channel'], new=True)
            if owner_test and (request['text'] != TEST_TEXT or request['idempotency_key'] != 'owner-channel-test-v1:' + channel):
                raise Refused('fixed_owner_test_required')
            if not owner_test and request['idempotency_key'].startswith('owner-channel-test-'):
                raise Refused('reserved_event_key')
            token = self.authorization(channel, owner_test=owner_test)
        except Exception:
            return {'status': 403, 'error': 'request_or_destination_refused'}
        db = self.journal.db; now = self.clock(); key = request['idempotency_key']
        kind = 'owner_test' if owner_test else 'lane'
        db.execute('INSERT OR IGNORE INTO events(event_key,channel,text,kind,created,status) VALUES(?,?,?,?,?,?)',
                   (key, channel, request['text'], kind, now, 'queued'))
        row = db.execute('SELECT * FROM events WHERE event_key=?', (key,)).fetchone()
        if row['channel'] != channel or row['kind'] != kind:
            return {'status': 409, 'error': 'event_destination_conflict'}
        if row['status'] == 'sent': return {'status': 200, 'receipt': json.loads(row['receipt'])}
        if row['status'] != 'queued': return {'status': 409, 'error': 'delivery_uncertain_owner_review_required'}
        cooldown = db.execute("SELECT value FROM metadata WHERE key='retry_at'").fetchone()
        deadline = max(row['retry_at'], cooldown[0] if cooldown else 0)
        if deadline > now: return {'status': 429, 'retry_after': math.ceil(deadline - now)}
        # Commit the uncertain boundary BEFORE making any network request.
        db.execute("UPDATE events SET status='inflight' WHERE event_key=?", (key,))
        text = row['text']; age = max(0, int(now - row['created']))
        if age > 60:
            match = re.match(r'LATE ([0-9]+)s', text)
            if match:
                text = 'LATE ' + str(int(match[1]) + age) + 's' + text[match.end():]
            else:
                text = 'LATE ' + str(age) + 's — queued delivery; refresh current data\n' + text
        try:
            status, receipt, delay = self.api.send(token, channel, text)
        except Exception:
            status, receipt, delay = 'ambiguous', None, 0
        if status == 'sent':
            # Validate even an injected adapter: no untrusted fields enter receipts.
            if (not isinstance(receipt, dict) or set(receipt) != {'chat_id', 'message_id', 'date'} or
                    receipt['chat_id'] != channel or type(receipt['message_id']) is not int or receipt['message_id'] <= 0 or
                    type(receipt['date']) is not int or receipt['date'] <= 0):
                status = 'ambiguous'
            else:
                db.execute("BEGIN IMMEDIATE")
                db.execute("UPDATE events SET status='sent',receipt=? WHERE event_key=?", (json.dumps(receipt), key))
                db.execute("INSERT OR REPLACE INTO metadata VALUES('retry_at',?)", (self.clock() + 1,))
                db.execute("COMMIT")
                return {'status': 200, 'receipt': receipt}
        if status == 'retry' and isinstance(delay, (int, float)) and math.isfinite(delay) and delay > 0:
            until = self.clock() + math.ceil(delay)
            db.execute("BEGIN IMMEDIATE")
            db.execute("UPDATE events SET status='queued',retry_at=? WHERE event_key=?", (until, key))
            db.execute("INSERT OR REPLACE INTO metadata VALUES('retry_at',?)", (until,))
            db.execute("COMMIT")
            return {'status': 429, 'retry_after': math.ceil(delay)}
        db.execute("UPDATE events SET status='ambiguous' WHERE event_key=?", (key,))
        return {'status': 409, 'error': 'delivery_uncertain_owner_review_required'}

def read_request(conn):
    raw = b''
    while b'\n' not in raw:
        chunk = conn.recv(4096)
        if not chunk: raise Refused('truncated_request')
        raw += chunk
        if len(raw) > 65536: raise Refused('oversize_request')
    return json.loads(raw.split(b'\n', 1)[0])

def peer_allowed(conn, lane_uid):
    _, uid, _ = struct.unpack('3i', conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
    return uid in (0, lane_uid)

def serve_connection(conn, engine, lane_uid):
    conn.settimeout(2)
    try:
        if not peer_allowed(conn, lane_uid): raise Refused('unauthorized_peer')
        result = engine.handle(read_request(conn))
    except Exception:
        result = {'status': 403, 'error': 'request_refused'}
    with contextlib.suppress(Exception):
        conn.sendall((json.dumps(result, separators=(',', ':')) + '\n').encode())

@contextlib.contextmanager
def state_lock():
    if os.geteuid() != 0: raise Refused('root_required')
    st = STATE.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o077:
        raise Refused('unsafe_state_directory')
    fd = os.open(STATE / 'sender.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)

def main():
    p = argparse.ArgumentParser(); p.add_argument('command', choices=['serve', 'test-channel'])
    p.add_argument('--expected-channel'); args = p.parse_args()
    os.umask(0o077)
    try:
        with state_lock():
            journal = Journal(STATE / 'sender.sqlite')
            try:
                engine = Engine(journal)
                if args.command == 'test-channel':
                    channel = channel_id(args.expected_channel, new=True)
                    request = {'protocol': PROTOCOL, 'channel': channel, 'parse_mode': 'HTML',
                               'text': TEST_TEXT, 'idempotency_key': 'owner-channel-test-v1:' + channel}
                    result = engine.handle(request, owner_test=True)
                    print(json.dumps(result))
                    return 0 if result['status'] == 200 else 1
                user = pwd.getpwnam('vivameda-early-lane')
                parent = SOCKET.parent.lstat()
                if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != 0 or parent.st_mode & 0o022:
                    raise Refused('unsafe_socket_parent')
                if SOCKET.exists() or SOCKET.is_symlink():
                    st = SOCKET.lstat()
                    if not stat.S_ISSOCK(st.st_mode) or st.st_uid != 0: raise Refused('unsafe_socket')
                    SOCKET.unlink()
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
                    server.bind(str(SOCKET)); os.chown(SOCKET, 0, user.pw_gid); os.chmod(SOCKET, 0o660)
                    server.listen(8)
                    print('early_lane_sender_ready', flush=True)
                    while True:
                        conn, _ = server.accept()
                        with conn: serve_connection(conn, engine, user.pw_uid)
            finally:
                journal.close()
    except Exception:
        print('early_lane_sender_failed_closed', flush=True)
        return 1

if __name__ == '__main__': raise SystemExit(main())
