import argparse
import base64
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4


CAMERA = ('rpicam-still -n -t 1100 --autofocus-mode auto '
          '--autofocus-on-capture --width 4608 --height 2592 --encoding jpg -o -')
MAX_PAGES = 6
MAX_JPEG = 6_000_000
MAX_AUDIO = 10_000_000
AUDIO_TYPES = {'.wav': 'audio/wav', '.mp3': 'audio/mpeg', '.m4a': 'audio/mp4'}
HOST = re.compile(r'[a-z_][a-z0-9_\-]*@[a-zA-Z0-9][a-zA-Z0-9.\-]*\Z')


@dataclass
class Page:
    label: str
    path: Path | None = None


def apply_change(pages, action, index=None, page=None):
    if action == 'a':
        if len(pages) >= MAX_PAGES:
            raise ValueError('한 묶음에 사진은 여섯 장까지 넣을 수 있습니다.')
        return [*pages, page]
    if not 0 <= index < len(pages):
        raise ValueError('목록에 있는 순서를 입력하세요.')
    result = pages.copy()
    if action == 'r':
        result[index] = page
    else:
        result.pop(index)
    return result


def choice_for_vibration(result, request_id):
    if not isinstance(result, dict) or result.get('request_id') != request_id:
        raise ValueError('현재 문제 묶음의 응답 ID가 아닙니다.')
    if result.get('status') in ('missing_pages', 'unreadable', 'missing_audio', 'ambiguous_audio'):
        return None
    choice = result.get('choice')
    if result.get('status') != 'ok' or type(choice) is not int or not 1 <= choice <= 5:
        raise ValueError('API 응답 형식이 올바르지 않습니다.')
    return choice


def ssh(target, command):
    return subprocess.run(
        ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', target, command],
        check=True, capture_output=True, timeout=20,
    ).stdout


def take_page(target, label, folder):
    photo = ssh(target, CAMERA)
    if len(photo) > MAX_JPEG or not photo.startswith(b'\xff\xd8') or not photo.endswith(b'\xff\xd9'):
        raise ValueError('카메라가 유효한 JPEG를 보내지 않았습니다.')
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'{uuid4().hex[:12]}.jpg'
    path.write_bytes(photo)
    return Page(label, path)


def request_solver(url, problem, pages, request_id, audio=None):
    payload = {
        'request_id': request_id, 'question': problem,
        'pages': [{'order': i, 'label': page.label,
                   'jpeg_base64': base64.b64encode(page.path.read_bytes()).decode('ascii')}
                  for i, page in enumerate(pages, 1)],
    }
    if audio is not None:
        audio_type = AUDIO_TYPES.get(audio.suffix.lower())
        if not audio_type:
            raise ValueError('듣기 파일은 WAV, MP3, M4A 중 하나를 사용하세요.')
        with audio.open('rb') as source:
            sound = source.read(MAX_AUDIO + 1)
        if not sound or len(sound) > MAX_AUDIO:
            raise ValueError('듣기는 문항별로 잘라 10MB 이하의 비어 있지 않은 파일로 넣으세요.')
        payload['audio'] = {'mime_type': audio_type, 'base64': base64.b64encode(sound).decode('ascii')}
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    token = os.environ.get('BOOK_SOLVER_TOKEN')
    if token:
        if not url.lower().startswith('https://'):
            raise ValueError('토큰을 보내려면 HTTPS가 필요합니다.')
        headers['Authorization'] = 'Bearer ' + token
    req = Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
    with urlopen(req, timeout=60) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description='문제별 페이지 촬영, 검토, 풀이')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--demo', action='store_true', help='장비와 API 없이 페이지 흐름 확인')
    mode.add_argument('--pi', metavar='USER@HOST', help='SSH 공개 키를 등록한 라즈베리파이')
    parser.add_argument('--demo-split', action='store_true', help='모의 시험에서 두 장을 요구')
    answer = parser.add_mutually_exclusive_group()
    answer.add_argument('--solver', help='페이지 배열을 받는 풀이 API URL')
    answer.add_argument('--fixed-choice', type=int, choices=range(1, 6))
    parser.add_argument('--strength', type=int, choices=range(25, 101), default=55, metavar='25-100')
    parser.add_argument('--audio', nargs=2, metavar=('QUESTION', 'FILE'),
                        help='지정한 문항에만 WAV, MP3, M4A 파일 첨부')
    args = parser.parse_args()
    if args.pi and (not HOST.fullmatch(args.pi) or not (args.solver or args.fixed_choice)):
        parser.error('--pi USER@HOST와 --fixed-choice 또는 --solver를 함께 입력하세요.')
    if args.demo and args.solver:
        parser.error('--demo는 외부 API를 호출하지 않습니다.')
    if args.demo_split and not args.demo:
        parser.error('--demo-split은 --demo와 함께 사용하세요.')
    if args.audio and (not args.solver or not re.fullmatch(r'[1-9][0-9]{0,2}', args.audio[0])):
        parser.error('--audio 17 파일은 --solver와 함께 사용하세요.')

    pages = []
    problem = ''
    folder = Path.cwd() / 'book_captures' / uuid4().hex[:8]
    print('A 추가  R 다시 찍기  D 삭제  V 사진 열기  S 풀이  N 새 문제  Q 종료')
    while True:
        print(f'\n문제 {problem or "미지정"} | ' + (' → '.join(f'{i}. {p.label}' for i, p in enumerate(pages, 1)) or '사진 없음'))
        try:
            action = input('동작 > ').strip().lower()
            if action == 'q':
                return
            if action == 'n':
                new_problem = input('새 문제 번호 > ').strip()
                if new_problem:
                    pages, problem = [], new_problem
                continue
            if action in ('a', 'r', 'd', 'v', 's') and not problem:
                raise ValueError('N으로 문제 번호를 먼저 입력하세요.')
            if action in ('a', 'r', 'd', 'v'):
                index = None
                if action != 'a':
                    index = int(input('사진 순서 > ').strip()) - 1
                    if not 0 <= index < len(pages):
                        raise ValueError('목록에 있는 순서를 입력하세요.')
                if action == 'v':
                    if pages[index].path:
                        os.startfile(pages[index].path)
                    else:
                        print('모의 사진입니다.')
                    continue
                if action == 'a' and len(pages) >= MAX_PAGES:
                    raise ValueError('한 묶음에 사진은 여섯 장까지 넣을 수 있습니다.')
                page = None
                if action in ('a', 'r'):
                    label = input('페이지 표시, 예: 42 하단 > ').strip()
                    if not label:
                        raise ValueError('페이지 표시를 입력하세요.')
                    page = Page(label) if args.demo else take_page(args.pi, label, folder)
                pages = apply_change(pages, action, index, page)
                continue
            if action != 's':
                continue
            if not pages:
                raise ValueError('A로 사진을 한 장 이상 추가하세요.')
            if input('순서와 본문, 보기를 확인했으면 Y > ').strip().lower() != 'y':
                continue
            request_id = uuid4().hex
            if args.solver:
                clip = Path(args.audio[1]) if args.audio and problem == args.audio[0] else None
                result = request_solver(args.solver, problem, pages, request_id, audio=clip)
            elif args.demo_split and len(pages) < 2:
                result = {'request_id': request_id, 'status': 'missing_pages'}
            else:
                result = {'request_id': request_id, 'status': 'ok', 'choice': args.fixed_choice or 3}
            choice = choice_for_vibration(result, request_id)
            if choice is None:
                print(f'입력 확인 필요 ({result["status"]}). 사진이나 해당 문항의 음원을 확인하세요.')
                continue
            if args.demo:
                print(f'문제 {problem}, 사진 {len(pages)}장, 진동 {choice}회 (모의)')
            else:
                ssh(args.pi, f'python3 ~/pi_haptic.py {choice} {args.strength}')
                print(f'문제 {problem}, 사진 {len(pages)}장, 진동 {choice}회 명령 완료')
        except EOFError:
            return
        except subprocess.CalledProcessError as error:
            print('라즈베리파이 동작 실패:', error.stderr.decode('utf-8', 'replace').strip()[-360:])
        except (ValueError, OSError, subprocess.TimeoutExpired) as error:
            print('확인 필요:', error)


if __name__ == '__main__':
    main()
