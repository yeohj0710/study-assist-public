import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from hotspot_test import CaptureServer


class HotspotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.server = CaptureServer(('127.0.0.1', 0), self.dir, token='test-key')
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join()
        self.tmp.cleanup()

    def send(self, key, data, note='42'):
        return urlopen(Request(self.base + f'/{key}/photo?label={note}', data=data,
                               headers={'Content-Type': 'application/octet-stream'}), timeout=3)

    def test_two_pages_saved_in_order(self):
        photo = bytes.fromhex('ffd8ffe000044a46ffd9')
        with urlopen(self.base + '/test-key/', timeout=3) as response:
            self.assertIn('사진 보내기', response.read().decode())
        for i, label in enumerate(['42', '43'], 1):
            with self.send('test-key', photo, label) as response:
                result = json.load(response)
                self.assertEqual(result['order'], i)
                self.assertEqual((self.dir / result['filename']).read_bytes(), photo)

    def test_bad_token_and_non_image_are_rejected(self):
        for token, code in [('wrong', 404), ('test-key', 415)]:
            with self.assertRaises(HTTPError) as error:
                self.send(token, b'not an image')
            self.assertEqual(error.exception.code, code)
        self.assertEqual(list(self.dir.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
