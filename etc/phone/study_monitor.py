"""Study activity records and the read-only dashboard on this PC."""

import json
import re
import sqlite3
import time
import threading
from collections import OrderedDict
from uuid import uuid4
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

_RETAIN_EVENTS = 8000
_PRUNE_EVERY = 100
_ARCHIVED_JPEG = re.compile(r'[0-9]{8}_[0-9]{6}_[0-9]{6}_[a-f0-9]{32}\.jpg')


class TraceStore:
    def __init__(self, path):
        self.path = Path(path)
        self._ready = False

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=0.25)
        if not self._ready:
            try:
                db.execute('CREATE TABLE IF NOT EXISTS monitor_events ('
                           'id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL)')
            except sqlite3.Error:
                db.close()
                raise
            self._ready = True
        return db

    def emit(self, stage, status, *, message='', **fields):
        event = {**fields, 'timestamp': time.time(), 'stage': stage, 'status': status, 'message': message}
        try:
            data = json.dumps(event, ensure_ascii=False, allow_nan=False)
            with closing(self._connect()) as db, db:
                event_id = db.execute('INSERT INTO monitor_events(data) VALUES (?)', (data,)).lastrowid
                if event_id % _PRUNE_EVERY == 0:
                    db.execute('DELETE FROM monitor_events WHERE id <= ?', (event_id - _RETAIN_EVENTS,))
            return event_id
        except (sqlite3.Error, TypeError, ValueError):
            return None

    def recent(self, limit=1500):
        try:
            with closing(self._connect()) as db:
                rows = db.execute('SELECT id, data FROM monitor_events ORDER BY id DESC LIMIT ?',
                                  (min(max(0, limit), _RETAIN_EVENTS),)).fetchall()
        except sqlite3.Error:
            return []
        return [{**json.loads(data), 'id': event_id} for event_id, data in reversed(rows)]


class LivePhotoStore:
    def __init__(self, capacity=8):
        self.capacity = capacity
        self.items = OrderedDict()
        self.discarded = OrderedDict()
        self.lock = threading.Lock()

    def put(self, jpeg, **fields):
        identifier = uuid4().hex
        with self.lock:
            if self.items and next(reversed(self.items.values()))[0].get('run') != fields.get('run'):
                self.items.clear()
            if (fields.get('run'), fields.get('group')) in self.discarded:
                return
            self.items[identifier] = ({'id': identifier, 'timestamp': time.time(), **fields}, jpeg)
            if len(self.items) > self.capacity:
                self.items.popitem(last=False)

    def remove_group(self, run, group):
        with self.lock:
            self.discarded[run, group] = None
            if len(self.discarded) > 64:
                self.discarded.popitem(last=False)
            for identifier, (entry, _) in tuple(self.items.items()):
                if (entry.get('run'), entry.get('group')) == (run, group):
                    del self.items[identifier]

    def list(self):
        with self.lock:
            return [metadata for metadata, _ in self.items.values()]

    def image(self, identifier):
        with self.lock:
            return self.items.get(identifier, (None, None))[1]


class ModelSettings:
    options = ('gpt-6.1-sol', 'gpt-6-luna', 'gpt-6.1-terra')
    defaults = {'route': options[0], 'solve': options[0], 'parallel': False}

    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.Lock()
        try:
            self.values = self.validate(self.defaults | json.loads(self.path.read_text(encoding='utf-8')))
        except (OSError, ValueError, TypeError):
            self.values = self.defaults.copy()

    @classmethod
    def validate(cls, values):
        if (not isinstance(values, dict) or values.keys() != cls.defaults.keys()
                or any(values[task] not in cls.options for task in ('route', 'solve'))
                or type(values['parallel']) is not bool):
            raise ValueError('모델과 병렬 판별 설정을 확인하세요')
        return values

    def get(self):
        with self.lock:
            return self.values.copy()

    def update(self, values):
        validated = self.validate(values)
        with self.lock:
            temporary = self.path.with_suffix('.tmp')
            temporary.write_text(json.dumps(validated), encoding='utf-8')
            temporary.replace(self.path)
            self.values = validated.copy()
            return self.values.copy()


def make_monitor_server(port, trace, photo_dir, html_file, state=None, previews=None, models=None):
    photo_dir = Path(photo_dir).resolve()
    html_file = Path(html_file)

    class MonitorHandler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def respond(self, status, content_type, body):
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        def send_file(self, path, content_type):
            try:
                body = path.read_bytes()
            except OSError:
                self.respond(404, 'text/plain; charset=utf-8', b'Not found')
                return
            self.respond(200, content_type, body)

        def do_POST(self):
            host = self.headers.get('Host', '').lower()
            port = self.server.server_port
            if (len(self.headers.get_all('Host', [])) != 1 or
                    host not in (f'localhost:{port}', f'127.0.0.1:{port}')
                    or self.headers.get('Origin') != f'http://{host}'):
                self.respond(403, 'text/plain; charset=utf-8', b'Local page required')
                return
            if self.path != '/settings/models' or models is None:
                self.respond(404, 'text/plain; charset=utf-8', b'Not found')
                return
            size = self.headers.get('Content-Length', '')
            if (self.headers.get_content_type() != 'application/json' or not size.isascii()
                    or not size.isdecimal() or len(size) > 4 or not 1 <= int(size) <= 1024):
                self.respond(400, 'text/plain; charset=utf-8', b'Invalid settings')
                return
            try:
                result = models.update(json.loads(self.rfile.read(int(size))))
            except ValueError:
                self.respond(400, 'text/plain; charset=utf-8', b'Invalid settings')
            except OSError:
                self.respond(503, 'text/plain; charset=utf-8', b'Could not save settings')
            else:
                self.respond(200, 'application/json; charset=utf-8', json.dumps(result).encode('utf-8'))

        def do_GET(self):
            port = self.server.server_port
            hosts = self.headers.get_all('Host', [])
            if len(hosts) != 1 or hosts[0].lower() not in (f'localhost:{port}', f'127.0.0.1:{port}'):
                self.respond(403, 'text/plain; charset=utf-8', b'Local host required')
                return
            path = self.path.partition('?')[0]
            if path == '/':
                self.send_file(html_file, 'text/html; charset=utf-8')
                return
            if path == '/favicon.svg':
                self.send_file(html_file.with_name('favicon.svg'), 'image/svg+xml')
                return
            if path == '/state':
                result = {'events': trace.recent(), 'state': (state() or {}) if state else {}, 'now': time.time()}
                body = json.dumps(result, ensure_ascii=False).encode('utf-8')
                self.respond(200, 'application/json; charset=utf-8', body)
                return
            if path.startswith('/live-photo/') and previews is not None:
                identifier = path.removeprefix('/live-photo/')
                if re.fullmatch(r'[0-9a-f]{32}', identifier):
                    jpeg = previews.image(identifier)
                    if jpeg is not None:
                        self.respond(200, 'image/jpeg', jpeg)
                        return
            if path.startswith('/photo/'):
                filename = path.removeprefix('/photo/')
                if _ARCHIVED_JPEG.fullmatch(filename):
                    photo = photo_dir / filename
                    if photo.resolve() == photo:
                        self.send_file(photo, 'image/jpeg')
                        return
            self.respond(404, 'text/plain; charset=utf-8', b'Not found')

    return ThreadingHTTPServer(('127.0.0.1', port), MonitorHandler)
