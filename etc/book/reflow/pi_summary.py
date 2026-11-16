from figures import hotspot, pins
from layout import CW, Page
from phone_first_text import PI_APPENDIX
from purchase import CAM_DOC, CAM_HW, DK_SHIPPING, GROVE_DOC, MOTOR_DOC, PI3_KR, ZERO_KR

PI = '부록 라즈베리파이 제작'
DETAIL = '라즈베리파이 상세 부록.pdf'


def write_pi_summary():
    p = Page(4, PI, '라즈베리파이 구성',
             '폰과 분리된 소형 카메라가 필요할 때 별도 보드를 씁니다. 책상에서는 먼저 카메라와 진동 모듈의 동작을 확인합니다.',
             ('책상형 Pi 3 B+', '착용형 Zero 2 WH', '상세 PDF'))
    p.flow([('카메라', 'Camera Module 3 Wide'), ('Pi 보드', 'Wi-Fi로 사진 전송'),
            ('Windows', '노트북에서 문제지 확인'), ('진동 모듈', '세 가닥 연결')],
           '**그림 1**  미리 맞는 리본, 전원, 조립 공간을 확인합니다.', 98)
    p.steps(PI_APPENDIX[:2])
    p.note('실습 ZIP의 상세 부록', f'**{DETAIL}**에 구입 항목별 가격과 배송비 예시, 설치 사진과 핀 확대 그림, 코드 실습을 넣었습니다. 보존한 인쇄 번호는 **14~42쪽**입니다. 가격과 재고는 당시 확인값입니다.', 'why')
    p.links([('카메라 공식 사양', CAM_HW), ('카메라 연결 안내', CAM_DOC)])
    p.finish(5, '핫스팟 사진 실습')

    p = Page(5, PI, '핫스팟 사진 실습',
             '보드를 사기 전에 갖고 있는 폰과 노트북으로 사진 두 장이 넘어오는지 시험합니다.',
             ('2.4GHz', '같은 Wi-Fi', 'PowerShell'))
    p.figure(163, '**그림 2**  첫 실습에서는 휴대폰 핫스팟에 Windows를 연결합니다.', hotspot)
    p.steps([
        PI_APPENDIX[4],
        ('사진 수신 서버 켜기', '실습 ZIP의 hotspot_test.py가 있는 폴더에서 PowerShell을 엽니다. **ipconfig**에서 노트북의 Wi-Fi IPv4를 확인하고 아래 예시 주소를 바꿉니다.'),
        ('브라우저에서 두 장 보내기', 'PowerShell에 표시된 전체 주소를 폰 브라우저에 넣습니다. 문항이 나뉜 앞과 뒤 사진을 차례로 보냅니다. Windows의 **hotspot_photos**에 저장됐는지 확인합니다.'),
    ], size=11.4)
    p.code('PowerShell / 예시 주소는 내 노트북 주소로 바꿈', [
        'ipconfig', 'python -X utf8 ./hotspot_test.py --ip 192.168.43.10',
    ])
    p.note('연결 오류', '같은 Wi-Fi와 주소를 먼저 확인합니다. Windows에서만 열리면 Windows 모바일 핫스팟으로 바꾸고, 그 주소를 다시 넣습니다. 실습을 끝내면 서버 창에서 **Ctrl+C**를 누릅니다.', 'warning')
    p.finish(8, '국내와 해외 구매')

    p = Page(8, PI, '국내와 해외 구매',
             '보드, 호환 리본, 카메라, 진동 모듈이 모두 출고되는지 먼저 확인하고 배송비를 더합니다.',
             ('국내 혼합 주문', '해외 주문', '호환과 재고'))
    p.table(('구매 경로', '확인 순서'), (124, CW-124), [
        ('국내 중심', '에쿠나 디바이스마트에서 보드와 헤더 출고를 확인합니다. 국내에 없는 카메라나 케이블은 별도 판매처에서 받을 수 있습니다.'),
        ('해외 책상형', 'Pi 3 B+, 카메라, 모터와 변환선을 해외 판매처에서 같은 장바구니에 담아 상품 합계와 배송비를 비교합니다.'),
        ('해외 착용형', 'Zero 2 WH의 40핀 헤더가 달려 있는지, 15↔22핀 리본과 보조 배터리용 전원선까지 확보할 수 있는지 확인합니다.'),
    ], size=11.55)
    p.steps(PI_APPENDIX[2:4])
    p.note('부품표 위치', f'**{DETAIL}**의 **21~24쪽**에서 국내 혼합, 해외 책상형, 해외 착용형 견적과 호환표를 봅니다. 세금과 주문처별 배송비를 장바구니에서 다시 확인합니다.', 'why')
    p.links([('Pi 3 B+ 국내 판매처', PI3_KR), ('Zero 2 WH 국내 판매처', ZERO_KR), ('DigiKey 배송 안내', DK_SHIPPING)])
    p.finish(13, '카메라와 진동 배선')

    p = Page(13, PI, '카메라와 진동 배선',
             '전원을 뽑은 상태에서 단자를 확인합니다. 사진이 보이면 Pi를 끈 뒤 진동 모듈을 연결합니다.',
             ('15핀과 22핀', '물리 핀 1, 6, 12', '전원 분리'))
    p.table(('품목', '맞는 부품과 연결'), (130, CW-130), [
        ('카메라', '가시광 Camera Module 3 Wide **SC1224**. Pi 3 B+와 Pi 4에는 **15↔15핀**, Zero 2 WH에는 **15↔22핀** 리본을 씁니다.'),
        ('진동 모듈', 'Grove Vibration Motor **105020003**과 암 소켓 변환 케이블 **110990028**. 모듈에 큰 플러그를 꽂습니다.'),
        ('보드의 물리 핀', '빨강 **1번(3.3V)**, 검정 **6번(GND)**, 노랑 **12번(GPIO18)**. 흰색은 연결하지 않고 절연합니다. 지정 케이블의 색과 모듈 표기를 대조합니다.'),
    ], size=11.45)
    p.figure(178, '**그림 3**  40핀 헤더의 1번 표시부터 찾아 실물의 물리 핀 위치를 맞춥니다.', pins)
    p.note(PI_APPENDIX[5][0], PI_APPENDIX[5][1] + f' 리본의 금속 접점 방향과 걸쇠는 **{DETAIL}** 25~26쪽 그림도 확인합니다.', 'warning')
    p.links([('Grove 진동 모듈', MOTOR_DOC), ('Grove 케이블 표기', GROVE_DOC)])
    p.finish(17, 'Pi 전원과 첫 작동')

    p = Page(17, PI, 'Pi 전원과 첫 작동',
             '보드에 맞는 전원선으로 켜고, 카메라 사진을 띄운 뒤 진동을 시험합니다.',
             ('microSD', 'PWR IN', '첫 사진과 첫 진동'))
    p.table(('보드', '전원 입력'), (132, CW-132), [
        ('Pi 3 B+', 'micro-USB **5V 2.5A급**. 실습용 벽 전원 예시는 SC0624입니다.'),
        ('Zero 2 WH', 'micro-USB **5V 2.5A급**, 기판의 **PWR IN** 포트. 착용형은 USB-C에서 micro-USB로 이어지는 규격에 맞는 보조 배터리 전원선을 씁니다.'),
        ('Pi 4', 'USB-C **5V 3A급**.'),
    ], size=11.55)
    p.steps([
        ('운영체제 설치', 'Raspberry Pi Imager로 microSD에 보드에 맞는 Raspberry Pi OS를 설치합니다. 사용할 Wi-Fi와 SSH 접속을 설정합니다. SSH는 노트북에서 Pi에 명령을 보내는 접속 방식입니다.'),
        ('첫 사진 확인', 'microSD와 리본을 연결한 뒤 전원을 넣습니다. 노트북에서 접속해 카메라 목록과 시험 JPEG를 확인합니다.'),
        ('진동 확인', 'Pi를 종료하고 전원을 뽑습니다. 핀 연결을 마친 뒤 다시 켜고 실습 파일에서 진동을 세 번 울려 봅니다.'),
    ])
    p.note('조립 실습 위치', f'**{DETAIL}**의 **27~29쪽**에 microSD 설치, 시험 사진, 진동 실행 명령이 있습니다. 팩 교체와 긴 시간 시험은 **40~41쪽**에 이어집니다.', 'why')
    p.links([('Raspberry Pi Imager', 'https://www.raspberrypi.com/software/')])
    p.finish()
