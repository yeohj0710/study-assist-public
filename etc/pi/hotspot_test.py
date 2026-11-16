import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import IPv4Address
import json
from pathlib import Path
import re
import secrets
from threading import Lock
from urllib.parse import parse_qs, urlsplit


MAX_BYTES = 12 * 1024 * 1024
PAGE = '''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>핫스팟 사진 시험</title>
<style>
:root { font-family: Pretendard,"Apple SD Gothic Neo","Noto Sans KR",sans-serif; color:#192824; background:#f3f8f5; }
* { box-sizing:border-box; }
main { width:min(100% - 40px,29rem); margin:clamp(32px,8vh,86px) auto; }
header { padding:0 0 22px; border-bottom:1px solid #bed1c7; }
h1 { margin:0 0 9px; font-size:32px; letter-spacing:-.035em; line-height:1.25; }
p,li { line-height:1.6; }
p { margin:0; color:#40594e; }
form { margin:22px 0 28px; display:grid; gap:12px; }
label { display:block; font-weight:700; }
input,button { font:inherit; width:100%; border:1px solid #aec5b8; border-radius:8px; padding:12px; color:inherit; background:#fbfdfa; }
::file-selector-button { font:inherit; margin-right:8px; border:0; background:#e0eee6; padding:7px 10px; border-radius:5px; color:#173f31; }
button { border:0; background:#215b49; color:#fffefa; font-weight:700; min-height:48px; }
button:disabled { opacity:.66; }
:focus-visible { outline:3px solid #1978ad; outline-offset:3px; }
h2 { margin:0 0 9px; font-size:19px; }
#status { min-height:1.6em; }
ol { margin:8px 0 16px; padding-left:1.5em; overflow-wrap:anywhere; }
</style>
</head>
<body><main>
<header><h1>핫스팟 사진 시험</h1><p>휴대폰에서 찍은 사진을 노트북으로 보냅니다.</p></header>
<form id="capture">
  <label for="label">쪽 표시</label>
  <input id="label" maxlength="32" placeholder="예: 42쪽 하단" required>
  <label for="photo">촬영하거나 사진 고르기</label>
  <input id="photo" type="file" accept="image/jpeg,image/png" capture="environment" required>
  <button id="send" type="submit">사진 보내기</button>
</form>
<section aria-labelledby="sent-title">
  <h2 id="sent-title">전송 결과</h2>
  <p id="status" role="status">보낸 사진이 아직 없습니다.</p>
  <ol id="history"></ol>
</section>
</main>
<script>
const form = document.querySelector('#capture');
const labelField = document.querySelector('#label');
const photoField = document.querySelector('#photo');
const button = document.querySelector('#send');
const statusText = document.querySelector('#status');
const sentList = document.querySelector('#history');
form.addEventListener('submit', async event => {
  event.preventDefault();
  const file = photoField.files[0];
  const label = labelField.value.trim();
  if (!file || !label) return;
  button.disabled = true;
  statusText.textContent = '보내는 중입니다.';
  try {
    const url = new URL('photo', window.location.href);
    url.searchParams.set('label', label);
    const response = await fetch(url, {method:'POST', body:file, headers:{'Content-Type':'application/octet-stream'}});
    const result = await response.json();
    if (!response.ok) {
      statusText.textContent = result.error;
      return;
    }
    const row = document.createElement('li');
    row.textContent = result.filename;
    sentList.append(row);
    statusText.textContent = String(result.order) + '번째 사진을 노트북에 저장했습니다.';
    photoField.value = '';
  } catch {
    statusText.textContent = '연결이 끊겼습니다. 노트북 창과 핫스팟을 확인하세요.';
  } finally {
    button.disabled = false;
  }
});
</script>
</body></html>
'''.encode('utf-8')


class CaptureServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, folder, token=None):
        self.folder = folder
        self.token = token or secrets.token_hex(6)
        self.count = 0
        self.lock = Lock()
        super().__init__(address, CaptureHandler)

    def save(self, label, suffix, data):
        with self.lock:
            self.count += 1
            name = f'{self.count:03d}-{label}{suffix}'
            with (self.folder / name).open('xb') as file:
                file.write(data)
            return {'order': self.count, 'filename': name}


class CaptureHandler(BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(15)
        super().setup()

    def log_message(self, _format, *_args):
        pass

    def send_bytes(self, status, data, content_type):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, status, result):
        self.send_bytes(status, json.dumps(result, ensure_ascii=False).encode('utf-8'),
                        'application/json; charset=utf-8')

    def do_GET(self):
        if urlsplit(self.path).path == f'/{self.server.token}/':
            self.send_bytes(HTTPStatus.OK, PAGE, 'text/html; charset=utf-8')
        else:
            self.send_json(HTTPStatus.NOT_FOUND, {'error': 'PowerShell에 새로 표시된 주소를 입력하세요.'})

    def do_POST(self):
        target = urlsplit(self.path)
        if target.path != f'/{self.server.token}/photo':
            self.send_json(HTTPStatus.NOT_FOUND, {'error': 'PowerShell에 새로 표시된 주소를 입력하세요.'})
            return
        label = parse_qs(target.query).get('label', [''])[0].strip()
        if not re.fullmatch(r'[0-9A-Za-z가-힣 _-]{1,32}', label):
            self.send_json(HTTPStatus.BAD_REQUEST, {'error': '쪽 표시에는 글자, 숫자, 띄어쓰기, - 또는 _를 쓰세요.'})
            return
        size = self.headers.get('Content-Length', '')
        if not size.isascii() or not size.isdecimal() or len(size) > 8 or not 0 < int(size) <= MAX_BYTES:
            self.send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {'error': '사진 한 장은 12MB 이하여야 합니다.'})
            return
        data = self.rfile.read(int(size))
        if len(data) == int(size) and data.startswith(b'\xff\xd8\xff') and data.endswith(b'\xff\xd9'):
            suffix = '.jpg'
        elif len(data) == int(size) and data.startswith(b'\x89PNG\r\n\x1a\n') and data.endswith(b'IEND\xaeB\x60\x82'):
            suffix = '.png'
        else:
            self.send_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {'error': 'JPG 또는 PNG 사진을 골라 다시 보내세요.'})
            return
        try:
            result = self.server.save(label, suffix, data)
        except OSError:
            self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {'error': '노트북 저장에 실패했습니다. 폴더와 디스크를 확인하세요.'})
            return
        print('수신:', result['filename'], flush=True)
        self.send_json(HTTPStatus.CREATED, result)


def main():
    parser = argparse.ArgumentParser(description='휴대폰 사진을 Windows로 전송하는 핫스팟 시험')
    parser.add_argument('--ip', required=True, type=IPv4Address, help='ipconfig에 표시된 Windows IPv4 주소')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if args.ip.is_unspecified or args.ip.is_multicast or not 1024 <= args.port <= 65535:
        parser.error('노트북의 실제 IPv4와 1024~65535 포트를 선택하세요.')
    folder = Path.cwd() / 'hotspot_photos' / secrets.token_hex(4)
    folder.mkdir(parents=True, exist_ok=False)
    try:
        with CaptureServer((str(args.ip), args.port), folder) as server:
            print(f'휴대폰 브라우저에 입력: http://{args.ip}:{server.server_port}/{server.token}/', flush=True)
            print(f'저장 폴더: {folder}', flush=True)
            print('종료하려면 Ctrl+C를 누르세요.', flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    except OSError as error:
        parser.exit(1, f'시작 실패: ipconfig 주소와 포트를 확인하세요. ({error})\n')


if __name__ == '__main__':
    main()
