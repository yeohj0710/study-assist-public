from layout import *
from figures import *
from purchase import *

A='부록 C 조립과 첫 부팅'

p=Page(13,A,'카메라 리본과 전원 단자','두 보드는 카메라 단자가 다른 곳에 있습니다. **전원을 뺀 상태에서** 그림을 보고 리본부터 끼웁니다.',('CAMERA / CSI','15핀 / 22핀','PWR IN'))
p.figure(180,'**그림 9**  단자 위치를 이해하기 위한 모식도입니다. 실제 기판의 인쇄와 제조사 사진으로 다시 맞춥니다.',ports)
p.steps([
    ('카메라 뒤에서 15핀 단자 찾기','렌즈 반대편의 납작한 연결 부위가 15핀입니다. **Pi 3 B+와 Pi 4**는 양끝 15핀 리본, **Zero 2 WH**는 좁은 22핀 끝을 Pi에 꽂는 리본을 고릅니다.'),
    ('걸쇠를 열고 리본을 똑바로 넣기','걸쇠 양쪽을 조금씩 고르게 열고 리본을 평행하게 넣습니다. 카메라 쪽 금속 접점은 기판을 향합니다. Pi 쪽은 보드마다 방향이 달라 아래 **제조사 설치 사진**에 맞춥니다.'),
    ('전원선은 맞는 포트에 준비만','Pi 3 B+는 **SC0624 벽 전원**, Zero는 **A1653 옆 USB-C → USB2CUB50CM → micro-USB PWR IN**, Pi 4는 **USB-C 5V 3A급**입니다. 전원 연결은 16쪽에서 합니다.'),
])
p.note('여기서 끼우지 말아야 할 곳','Zero 쪽의 micro-USB 두 개 중 **PWR IN**이 전원입니다. 15핀 리본을 좁은 22핀 단자에 억지로 넣지 마세요.','warning')
p.links([('제조사 설치 사진과 방향',CAM_DOC),('StarTech 전원선 규격',STAR_KR)])
p.finish(14,'진동 모듈 연결')

p=Page(14,A,'진동 모듈 꽂기','**납땜 없이** 완성 모듈과 변환 케이블을 결합합니다. Pi에 꽂는 번호는 보드의 **물리 위치**입니다.',('물리 1번 전원','6번 GND','12번 GPIO18'))
p.figure(176,'**그림 10**  Grove 4핀 플러그는 모듈에, 반대편의 암 소켓 3개는 라즈베리파이에 꽂습니다.',pins)
p.steps([
    ('모듈과 케이블 품번 확인','모터가 붙은 **Grove Vibration Motor 105020003**과 **110990028 암 소켓 변환 케이블** 1개를 씁니다. 한쪽에 큰 플러그, 다른 쪽에 따로 움직이는 암 소켓 네 개가 달려 있습니다.'),
    ('세 자리만 꽂기','빨강 **물리 1번(3.3V)**, 검정 **6번(GND)**, 노랑 **12번(GPIO18)**입니다. 흰색은 빈 상태로 절연합니다. 선 색은 지정한 정품 케이블 기준이며 모듈의 표기도 대조합니다.'),
    ('첫 사진을 확인한 뒤 연결','16쪽에서 카메라를 확인하고 **Pi 종료 → 전원 분리 → 진동 모듈 연결** 순서로 진행합니다. 전원을 다시 넣고 17쪽에서 진동을 확인하세요.'),
])
p.figure(76,'**핀 1 근처 확대**  홀수와 짝수는 서로 다른 줄에 있습니다. 실물의 핀 1 표시부터 찾습니다.',pin_corner)
p.links([('Seeed 모듈과 핀',MOTOR_DOC),('Grove 케이블 색 순서',GROVE_DOC),('Pi 물리 핀','https://www.raspberrypi.com/documentation/computers/raspberry-pi.html')])
p.finish(15,'SD와 로그인 준비')

p=Page(15,A,'microSD에 운영체제 넣기','**microSD**는 Pi의 저장 카드입니다. Windows에 카드를 꽂고 **Raspberry Pi Imager**로 Pi가 처음 켜질 환경을 씁니다.',('Imager','Lite 64비트','SSH 공개 키'))
p.flow([('빈 카드','카드 리더 연결'),('Imager','기기와 OS 선택'),('Wi-Fi / SSH','핫스팟 이름과 공개 키')],'**그림 11**  SSH는 노트북에서 Pi에 접속해 명령을 실행하는 통로입니다.',94)
p.code('Windows PowerShell / SSH 키가 없을 때만 새로 생성',[
    'ssh -V','ssh-keygen -t ed25519','Get-Content "$env:USERPROFILE/.ssh/id_ed25519.pub"'])
p.table(('Imager 항목','입력할 값'),(153,CW-153),[
    ('기기','구매한 모델을 고릅니다. Zero 2 WH는 **Raspberry Pi Zero 2 W**입니다.'),
    ('OS / 저장 장치','**Raspberry Pi OS Lite (64-bit)** / 지금 꽂은 microSD'),
    ('이름 / 계정','호스트 이름 **bookcam**, 사용자 **study**, 새 비밀번호, 시간대 Seoul'),
    ('Wi-Fi','4쪽의 핫스팟 이름과 비밀번호. 국가 옵션이 있으면 **KR**.'),
    ('SSH','**Enable SSH → Use public key authentication**. 방금 확인한 .pub 내용만 붙여넣습니다.'),
],size=10.7)
p.note('쓰기 전 두 가지 확인','이 단계는 선택한 카드의 내용을 지웁니다. **카드 이름과 용량**을 확인하고 쓰기를 시작하세요. 키 파일을 덮어쓸지 묻는다면 취소하고 기존 공개 키를 씁니다.','warning')
p.links([('Imager 설치','https://www.raspberrypi.com/software/'),('Pi 첫 설치 문서','https://www.raspberrypi.com/documentation/computers/getting-started.html'),('Windows OpenSSH','https://learn.microsoft.com/ko-kr/windows-server/administration/openssh/openssh_install_firstuse')])
p.finish(16,'첫 JPEG 확인')

p=Page(16,A,'Pi를 켜고 첫 사진 받기','카메라 리본과 microSD만 연결한 뒤 전원을 꽂습니다. 처음 켜질 때는 몇 분 걸릴 수 있습니다.',('bookcam.local','imx708','test.jpg'))
p.flow([('전원 연결','Pi가 부팅'),('Pi에 접속','Windows에서 SSH'),('사진 촬영','Pi에서 rpicam'),('가져오기','Windows에서 scp')],'**그림 12**  어떤 창에 명령을 입력할지 제목을 확인하세요.',91)
p.code('Windows PowerShell / 노트북도 같은 핫스팟에 연결',[
    'Test-NetConnection bookcam.local -Port 22','ssh study@bookcam.local'])
p.body('**TcpTestSucceeded가 True**면 접속 가능한 상태입니다. 이름으로 안 되면 핫스팟 기기 목록에서 Pi의 IP를 찾아 **bookcam.local** 대신 넣습니다.',size=11.3)
p.code('SSH로 접속한 Pi 창',['hostname -I','rpicam-hello --list-cameras','rpicam-still -n --autofocus-mode auto --autofocus-on-capture -o test.jpg'])
p.code('새 Windows PowerShell / 사진을 내려받고 열기',['scp study@bookcam.local:~/test.jpg ./test.jpg','Invoke-Item ./test.jpg'])
p.note('성공과 오류 구분','카메라 목록의 ==imx708==과 열린 **test.jpg**를 확인합니다. 목록에 카메라가 없으면 **sudo poweroff**로 종료하고 전원을 뺀 뒤 리본과 걸쇠를 다시 확인합니다.','why')
p.body('rpicam 명령이 없다면 Pi에서 **sudo apt update** 후 **sudo apt install -y rpicam-apps-lite**를 실행합니다. SSH가 막히면 6쪽의 Windows 핫스팟을 시험하세요.',size=10.7)
p.finish(17,'첫 진동 확인')

p=Page(17,A,'Pi가 세 번 울리는지 확인','사진이 확인됐으면 Pi를 종료하고 전원을 뺍니다. **14쪽 핀 표**대로 Grove를 연결한 뒤 켭니다.',('GPIO18','PWM 55%부터','진동 3회'))
p.flow([('전원 뺀 상태','세 가닥 꽂기'),('Pi에서 설치','GPIO 도구 두 개'),('노트북에서 실행','파일 복사 후 3회 시험')],'**그림 13**  사진을 먼저 성공시킨 뒤 진동을 연결하면 막힌 지점을 구분하기 쉽습니다.',90)
p.code('SSH로 접속한 Pi 창',['sudo apt update','sudo apt install -y python3-gpiozero python3-lgpio'])
p.body('**PWM**은 신호를 짧게 켰다 끄며 켜지는 비율로 진동을 조절하는 방식입니다. 이 구성은 **GPIO18**을 사용합니다.',size=11.25)
p.code('Windows PowerShell / ZIP을 푼 폴더',['scp ./pi_haptic.py study@bookcam.local:~/','ssh study@bookcam.local "python3 ~/pi_haptic.py 3 55"'])
p.note('옷 안에서 가장 낮은 작동 강도 찾기','**3은 횟수, 55는 켜지는 비율(%)**입니다. 세 번이 느껴지지 않으면 핀과 전원을 확인한 뒤 65%로 한 번 시험합니다. 작동하면 조금씩 낮추고, 책상에 놓은 상태와 옷에 고정한 상태의 소리를 비교하세요.')
p.finish(18,'두 쪽 실습')
