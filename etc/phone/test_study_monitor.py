import http.client
import importlib
import json
import sqlite3
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('study_monitor'), 'Local monitor is not implemented')
        self.monitor = importlib.import_module('study_monitor')
        sandbox = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(sandbox.cleanup)
        self.base = Path(sandbox.name)
        self.path = self.base / 'events.sqlite3'
        self.trace = self.monitor.TraceStore(self.path)

    def test_trace_round_trip_and_sequence_across_connections(self):
        first = self.trace.emit('photo', 'received', message='1번 사진', run='abc', question=1)
        other = self.monitor.TraceStore(self.path)
        second = other.emit('solve', 'ready', group=2, choices=[1, 2, 3])
        self.assertLess(first, second)
        self.assertEqual([item['id'] for item in other.recent()], [first, second])
        event = self.trace.recent(1)[0]
        self.assertAlmostEqual(event['timestamp'], time.time(), delta=3)
        self.assertEqual((event['stage'], event['status'], event['message']), ('solve', 'ready', ''))
        self.assertEqual((event['group'], event['choices']), (2, [1, 2, 3]))

    def test_concurrent_writers_record_distinct_events(self):
        def record(number):
            store = self.monitor.TraceStore(self.path)
            return store.emit('solve', 'ready', number=number)
        with ThreadPoolExecutor(max_workers=4) as workers:
            ids = list(workers.map(record, range(12)))
        self.assertNotIn(None, ids)
        self.assertEqual(len(set(ids)), 12)
        self.assertEqual({event['number'] for event in self.trace.recent()}, set(range(12)))

    def test_write_failure_does_not_leave_trace_unusable(self):
        self.trace.emit('photo', 'received')
        with closing(sqlite3.connect(self.path)) as lock:
            lock.execute('BEGIN EXCLUSIVE')
            self.assertIsNone(self.trace.emit('photo', 'queued'))
        self.assertIsNotNone(self.trace.emit('photo', 'routed'))
        self.assertEqual([event['status'] for event in self.trace.recent()], ['received', 'routed'])

    def test_model_settings_are_shared_with_authenticated_phone(self):
        from phone_server import Study, create_server

        models = self.monitor.ModelSettings(self.base / 'models.json')
        study = Study(None, 1, False, model_settings=models)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        phone = create_server('127.0.0.1', 0, 'phone-test-token', study)
        pc = self.monitor.make_monitor_server(
            0, self.trace, self.base, self.base / 'dashboard.html',
            state=lambda: {'models': models.get()}, models=models)

        for server in (phone, pc):
            self.addCleanup(server.server_close)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(thread.join)
            self.addCleanup(server.shutdown)

        def request(server, method, path, payload=None, **headers):
            with closing(http.client.HTTPConnection(*server.server_address, timeout=3)) as connection:
                body = json.dumps(payload) if payload is not None else None
                if body is not None:
                    headers['Content-Type'] = 'application/json'
                connection.request(method, path, body, headers)
                response = connection.getresponse()
                return response.status, response.read()

        auth = {'Authorization': 'Bearer phone-test-token'}
        quick = {'route': 'gpt-6-luna', 'solve': 'gpt-6-luna', 'parallel': False}
        self.assertEqual(request(phone, 'GET', '/models')[0], 401)
        self.assertEqual(request(phone, 'POST', '/models', quick)[0], 401)
        self.assertEqual(request(phone, 'GET', '/models', **auth)[0], 200)
        self.assertEqual(request(phone, 'POST', '/models', quick, **auth)[0], 200)
        status, body = request(pc, 'GET', '/state')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['state']['models'], quick)

        mixed = quick | {'solve': 'gpt-6.1-sol', 'parallel': True}
        origin = f'http://127.0.0.1:{pc.server_port}'
        self.assertEqual(request(pc, 'POST', '/settings/models', mixed, Origin=origin)[0], 200)
        status, body = request(phone, 'GET', '/models', **auth)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), mixed)
        self.assertEqual(request(phone, 'POST', '/models', mixed | {'solve': 'unsupported'}, **auth)[0], 400)
        self.assertEqual(self.monitor.ModelSettings(self.base / 'models.json').get(), mixed)

    def test_http_state_and_archived_photo(self):
        html = self.base / 'dashboard.html'
        html.write_text('<h1>실행 현황</h1>', encoding='utf-8')
        photos = self.base / 'photos'
        photos.mkdir()
        filename = '20261116_141000_012345_' + 'a' * 32 + '.jpg'
        jpeg = bytes.fromhex('ffd8ffd9')
        (photos / filename).write_bytes(jpeg)
        (photos / 'unrelated.jpg').write_bytes(jpeg)
        server = self.monitor.make_monitor_server(0, self.trace, photos, html, state=lambda: {'queued': 2})
        self.addCleanup(server.server_close)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.start()
        self.addCleanup(server_thread.join)
        self.addCleanup(server.shutdown)
        ip, port = server.server_address
        self.assertEqual(ip, '127.0.0.1')

        def get(path, **headers):
            connection = http.client.HTTPConnection(ip, port, timeout=3)
            try:
                connection.request('GET', path, headers=headers)
                response = connection.getresponse()
                return response.status, dict(response.getheaders()), response.read()
            finally:
                connection.close()

        self.trace.emit('listen', 'started', provider='whisper')
        status, headers, body = get('/state', Host=f'localhost:{port}')
        self.assertEqual(status, 200)
        self.assertIn('no-store', headers['Cache-Control'])
        payload = json.loads(body)
        self.assertAlmostEqual(payload['now'], time.time(), delta=3)
        self.assertEqual(payload['state'], {'queued': 2})
        self.assertEqual(payload['events'][0]['provider'], 'whisper')
        self.assertEqual(get('/')[2].decode(), '<h1>실행 현황</h1>')
        self.assertEqual(get(f'/photo/{filename}')[2], jpeg)
        self.assertEqual(get('/photo/unrelated.jpg')[0], 404)
        self.assertEqual(get('/photo/%2e%2e/dashboard.html')[0], 404)
        self.assertEqual(get('/state', Host=f'example.org:{port}')[0], 403)
        self.assertEqual(get('/state', Host='localhost:9')[0], 403)
