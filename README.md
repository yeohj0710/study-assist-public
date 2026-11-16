# 학습 보조기

Android 폰으로 개인 연습문제를 비추면 Windows PC가 사진을 받아 문항을 읽고 풉니다. 폰은 문항번호와 보기를 진동으로 알립니다. PC의 진행 화면에서 사진, 풀이 근거와 폰의 수신 상태를 확인할 수 있습니다.

## 시작

1. [릴리스](https://github.com/yeohj0710/study-assist-public/releases/latest)에서 **study-assist.apk**와 **study-assist-guide.pdf**를 받습니다. 앱은 Android 9 이상에서 설치할 수 있습니다.
2. 저장소를 내려받고 Windows PowerShell에서 아래 명령을 실행합니다. 처음에는 연결 시험 모드에서 폰과 PC의 통신을 확인하세요.

```powershell
python -m pip install -r requirements.txt
cd etc/phone
./start_phone.ps1 -Demo
```

3. [PC 진행 화면](http://127.0.0.1:8787/)을 엽니다. 폰 설정에는 PC의 **Tailscale 주소**와 서버가 만든 **connection.key**의 값을 입력합니다. 주소 연결 방법은 [폰 설치 안내](etc/phone/README.md)에 있습니다.
4. 실제 풀이에는 로그인된 [Codex CLI](https://developers.openai.com/codex/cli/)가 필요합니다. 연결 시험을 끝내고 -Demo 없이 서버를 켭니다. AgentRouter를 쓸 때는 내 API 키를 환경 변수로 지정합니다.

사진은 PC에 저장됩니다. 실제 풀이를 켜면 선택한 모델 제공자에게 문항 판별과 풀이에 필요한 이미지가 전달됩니다. 연결 시험은 외부 모델을 호출하지 않습니다.

## 연습 자료

[연습 문제와 정답표](examples/README.md)에 직접 만든 예제와 수능 모의평가 및 듣기 문제의 공식 다운로드 페이지를 모았습니다.

## 제작과 검증

- [Android 앱과 PC 서버](etc/phone/README.md)
- [라즈베리파이 실습](etc/pi/README.md)
- PDF 원본은 etc/book/reflow/book.py에서 만듭니다. Python에 Pillow, reportlab과 pymupdf를 설치하고 저장소 루트에서 해당 스크립트를 실행합니다. Pretendard 글꼴은 [SIL 오픈 폰트 라이선스](etc/book/Pretendard-OFL.txt)를 따릅니다.
- Windows에서 JAVA_HOME과 ANDROID_HOME을 지정하고 Android SDK Platform 35와 SDK Build-Tools를 설치합니다. etc/phone/build.ps1을 실행하면 etc/phone/build/study-assist.apk에 로컬 서명 APK를 만듭니다.
- 폰 서버 시험은 etc/phone, 라즈베리파이 시험은 etc/pi에서 python -m unittest discover로 실행합니다.
