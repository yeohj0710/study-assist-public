import base64
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import unittest

from book_session import Page, apply_change, choice_for_vibration, request_solver


class BookTests(unittest.TestCase):
    def test_replace_keeps_position(self):
        pages = [Page('42 아래'), Page('43 위'), Page('43 아래')]
        result = apply_change(pages, 'r', 1, Page('43 위 재촬영'))
        self.assertEqual([p.label for p in result], ['42 아래', '43 위 재촬영', '43 아래'])
        self.assertEqual(pages[1].label, '43 위')

    def test_remove_only_selected_photo(self):
        pages = [Page('42'), Page('42 중복'), Page('43')]
        self.assertEqual([p.label for p in apply_change(pages, 'd', 1)], ['42', '43'])

    def test_missing_or_unreadable_has_no_haptic(self):
        for state in ('missing_pages', 'unreadable'):
            self.assertIsNone(choice_for_vibration({'status': state, 'request_id': 'id'}, 'id'))

    def test_refuses_unrelated_or_non_integer_result(self):
        for request_id, choice in [('other', 3), ('id', True), ('id', 6)]:
            with self.assertRaises(ValueError):
                choice_for_vibration({'status': 'ok', 'request_id': request_id, 'choice': choice}, 'id')

    def test_real_local_http_preserves_page_order(self):
        seen = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                seen.append(data)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({'request_id': data['request_id'], 'status': 'ok', 'choice': 3}).encode())

            def log_message(self, *args):
                pass

        with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server, TemporaryDirectory() as folder:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                files = [Path(folder) / '42.jpg', Path(folder) / '43.jpg']
                for path in files:
                    path.write_bytes(path.stem.encode())
                result = request_solver(f'http://127.0.0.1:{server.server_port}/solve', '17',
                                        [Page(p.stem, p) for p in files], 'request')
                self.assertEqual(choice_for_vibration(result, 'request'), 3)
                self.assertEqual(seen[0]['question'], '17')
                self.assertEqual([p['order'] for p in seen[0]['pages']], [1, 2])
                self.assertEqual([base64.b64decode(p['jpeg_base64']) for p in seen[0]['pages']], [b'42', b'43'])
            finally:
                server.shutdown()
                thread.join()

    def test_demo_requires_second_page(self):
        script = Path(__file__).with_name('book_session.py')
        response = subprocess.run([sys.executable, '-X', 'utf8', str(script), '--demo', '--demo-split'],
                                  input='n\n17\na\n42\ns\ny\na\n43\ns\ny\nq\n',
                                  capture_output=True, encoding='utf-8', check=True)
        self.assertIn('missing_pages', response.stdout)
        self.assertEqual(response.stdout.count('진동 3회 (모의)'), 1)
        self.assertIn('사진 2장', response.stdout)


if __name__ == '__main__':
    unittest.main()
