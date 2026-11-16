# 라즈베리파이 실습

설치와 구매표는 **학습 보조기 제작 가이드 2611152300**의 부록을 참고합니다. 기본 사용 방식인 휴대폰 앱은 ZIP의 **휴대폰** 폴더에 있습니다.

- **16~18쪽** 휴대폰 사진 두 장으로 핫스팟 시험
- **20~24쪽** 부품 비교와 호환표
- **25~29쪽** 카메라, 무납땜 진동 모듈, 첫 사진과 첫 진동
- **30~36쪽** 두 쪽 문제, 풀이 API, 재생 순서와 듣기 선택
- **37~42쪽** 옷에 고정하는 위치, 케이블 실측, 배터리, Wi-Fi

## 장비 없이 사진과 답을 시험

Windows PowerShell에서 파일을 푼 폴더를 엽니다. Python 3.10 이상을 씁니다.

```powershell
python -X utf8 ./book_session.py --demo --demo-split
python -X utf8 ./page_replay.py
```

첫 프로그램에서 **N → 17 → A → 42 하단**을 입력합니다. **S → Y**를 누르면 `missing_pages`가 표시됩니다. **A → 43 상단 → S → Y**에서는 두 장의 순서와 모의 진동 3회가 표시됩니다. **V**는 사진 열기, **R**은 교체, **D**는 삭제, **Q**는 종료입니다. 두 번째 프로그램은 42쪽을 떠났다가 다시 볼 때 답 순서를 보여 줍니다.

## 휴대폰 핫스팟에서 사진 받기

1. 휴대폰 핫스팟을 2.4GHz로 켭니다. Windows 노트북을 그 Wi-Fi에 연결합니다.
2. `ipconfig`에서 노트북의 Wi-Fi IPv4를 찾습니다. 아래 IP 자리에 넣으세요.

```powershell
python -X utf8 ./hotspot_test.py --ip 192.168.43.10
```

3. 폰에서 표시된 주소를 끝까지 열고 사진 두 장을 보냅니다. `hotspot_photos`에 001, 002가 생겼는지 확인합니다.
4. 기기끼리 접속이 되지 않으면 Windows 모바일 핫스팟을 켜고 폰을 연결합니다. 새 노트북 IPv4로 같은 명령을 실행합니다.
5. 끝나면 **Ctrl+C**를 누릅니다. 휴대폰 사진이 HEIC라면 카메라 포맷에서 높은 호환성을 골라 다시 찍습니다.

## 첫 사진과 첫 진동

1. Pi 전원을 빼고 카메라를 끼웁니다. Wide 카메라 SC1224에 Pi 3 B+ 또는 Pi 4는 **15↔15핀**, Zero 2 WH는 **15↔22핀** 리본을 씁니다. Imager로 Wi-Fi와 SSH 공개 키를 미리 지정하고 부팅합니다.
2. 노트북에서 `ssh study@bookcam.local`로 Pi에 접속하고 아래 두 줄을 실행합니다. 이름이 안 되면 Pi IP를 씁니다.

```sh
rpicam-hello --list-cameras
rpicam-still -n --autofocus-mode auto --autofocus-on-capture -o test.jpg
```

3. 새 PowerShell에서 `scp study@bookcam.local:~/test.jpg ./test.jpg`로 사진을 가져옵니다. 사진이 열리면 Pi에 SSH로 접속해 `sudo poweroff`를 실행하고 Pi 전원을 뺍니다.
4. **Grove 105020003**에 케이블 **110990028**을 꽂습니다. Pi 보드의 **물리 1번(빨강 3.3V), 6번(검정 GND), 12번(노랑 GPIO18)**을 연결하고 흰색은 절연합니다.
5. 전원을 연결하고 Pi에 접속해 `sudo apt update`, `sudo apt install -y python3-gpiozero python3-lgpio`를 실행합니다.
6. Windows PowerShell에서 아래를 실행합니다. 3은 진동 횟수, 55는 세기 조절을 위한 켜짐 비율입니다.

```powershell
scp ./pi_haptic.py study@bookcam.local:~/
ssh study@bookcam.local "python3 ~/pi_haptic.py 3 55"
python -X utf8 ./book_session.py --pi study@bookcam.local --fixed-choice 3
```

촬영은 **N → A**, 제출은 **S → Y**입니다. 사진은 `book_captures`에 남습니다. 사용 중 배터리를 교체하려면 Pi를 먼저 종료합니다.

## 풀이 API와 듣기 선택

기존에 운영하는 풀이 API를 붙이는 선택입니다. HTTPS 주소를 실제 주소로 바꾸고, 인증이 필요하면 Windows 환경변수 `BOOK_SOLVER_TOKEN`을 사용합니다.

```powershell
python -X utf8 ./book_session.py --pi study@bookcam.local `
  --solver https://your-api.example/solve --strength 55
```

듣기 자료는 해당 문항만 포함한 **WAV, MP3, M4A** 파일로 준비합니다. 같은 명령의 끝에 `--audio 17 ./track-17.wav`를 붙이면 17번 제출에만 함께 보냅니다. API에 음성 입력이 필요합니다.

```json
{
  "request_id": "example-request-id",
  "question": "17",
  "pages": [
    {"order": 1, "label": "42 하단", "jpeg_base64": "..."},
    {"order": 2, "label": "43 상단", "jpeg_base64": "..."}
  ],
  "audio": {"mime_type": "audio/wav", "base64": "..."}
}
```

`status: ok`와 `choice: 3`을 응답하면 세 번 진동합니다. 응답의 `request_id`는 원본 그대로, `choice`는 1~5 사이 JSON 정수여야 합니다. 누락이나 흐린 사진은 `missing_pages` 또는 `unreadable`로 표시합니다. 실습은 최대 6장, 장당 원본 6MB, 음성 원본 10MB를 받습니다. Base64 변환 후 전송량은 더 커집니다.

Pi 실습으로는 촬영, 파일 전송, 횟수 진동을 수동으로 확인합니다. 자동 촬영부터 번호 진동까지 구현한 폰 버전은 폰 실습을 참고하세요.
