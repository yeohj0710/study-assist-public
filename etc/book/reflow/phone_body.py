from layout import *
from figures import book, tile
from reportlab.lib.utils import ImageReader
from phone_extension import (write_decision, write_install, write_vibration_numbers, write_practice,
                             write_fixed_angle, write_monitor, write_listening, write_history)

SAMSUNG='https://www.samsung.com/sec/smartphones/galaxy-s25-ultra/specs/'
REPAIR='https://www.samsung.com/us/support/answer/ANS10007620/'
VIEW_ANGLES='https://news.samsung.com/uk/samsung-galaxy-s25-series-sets-the-standard-of-ai-phone-as-a-true-ai-companion'
WINDOWS='https://tailscale.com/docs/install/windows'
ANDROID='https://tailscale.com/docs/install/android'
SERVE='https://tailscale.com/docs/reference/tailscale-cli/serve'
PRACTICE='https://wdown.ebsi.co.kr/W61001/01exam/20250903/go3/s_ssnyr_mun_6M5D497U.pdf'
TAILSCALE_PATH="$ts = Join-Path $env:ProgramFiles 'Tailscale/tailscale.exe'"
PHONE='01 폰과 렌즈 준비'
NETWORK='02 집 노트북과 앱 연결'
PRACTICE_CHAPTER='03 첫 촬영과 문제지 실습'
WORK='04 풀이 확인과 긴 시간 사용'


def home_loop(x,y,w,h):
    right=x+w-163
    tile(x+5,y+9,139,112,'밖의 휴대폰','책을 3~6초마다 촬영\n검은 화면으로 유지\n답은 진동으로 수신',GREEN,WHITE)
    tile(right,y+9,158,112,'집의 Windows 노트북','사진 비교\nCodex로 문항 확인\n답을 한 문항씩 정리',BLUE,SKY)
    arrow(x+151,y+44,right-8,y+44,BLUE)
    txt(x+w/2-12,y+21,'책 사진',10.7,'Bold',BLUE,'center')
    arrow(right-8,y+93,x+151,y+93,PURPLE)
    txt(x+w/2-12,y+67,'진동 신호',10.7,'Bold',PURPLE,'center')
    arrow(right+80,y+130,right+80,y+153,GREEN)
    tile(right,y+157,158,58,'GPT-6.1 Sol high','새 문항마다 풀이 세션',GREEN,WHITE)
    txt(x+5,y+163,'두 장치를 Tailscale로 연결',11.6,'ExtraBold',GREEN)
    txt(x+5,y+183,'노트북은 전원에 연결해 둡니다.',10.4,'Medium',GRAY)


def lens_map(x,y,w,h):
    front=x+5
    left=x+103
    rect(front,y+9,83,174,'#263832',radius=9)
    rect(front+3,y+12,77,168,'#182521',radius=6)
    circle(front+41.5,y+22,6,AMBER)
    circle(front+41.5,y+22,3,'#0D1B16')
    txt(front+41,y+146,'전면 1개',10.7,'ExtraBold',WHITE,'center')
    txt(front+41,y+163,'앱에서 사용',8.5,'Bold','#F1E1AC','center')
    rect(left,y+9,83,174,'#2A3A36',radius=10)
    for cx,cy,radius in [(left+22,y+32,11),(left+22,y+62,11),(left+22,y+92,11),
                         (left+49,y+32,7),(left+49,y+62,7)]:
        circle(cx,cy,radius,'#0D1B16')
        circle(cx,cy,radius*.58,'#435F52')
    circle(left+49,y+47,3,'#F1E1AC')
    for pos,lab in [((22,32),'1'),((22,62),'2'),((22,92),'3'),((49,62),'4'),((49,32),'5')]:
        txt(left+pos[0],y+pos[1]-7,lab,8.5,'Bold',WHITE,'center')
    txt(left+63,y+41,'6',8.7,'Bold','#F1E1AC','center')
    txt(left+42,y+146,'후면',10.5,'ExtraBold',WHITE,'center')
    txt(left+42,y+164,'렌즈 4개 + 센서',8.2,'Bold','#B9D1C4','center')
    rows=[
        ('1','초광각 0.6×','50MP, 120°',INK),
        ('2','광각 1×','200MP, 가운데',INK),
        ('3','망원 5×','50MP, 왼쪽 아래',INK),
        ('4','망원 3×','10MP, 오른쪽 아래 작은 원',INK),
        ('5','레이저 AF','오른쪽 위, 초점 거리 감지',GRAY),
        ('6','LED 플래시','두 작은 원 사이',GRAY),
    ]
    for i,(n,title,detail,tone) in enumerate(rows):
        at=y+7+30*i
        txt(x+208,at,n,10.8,'ExtraBold',tone)
        txt(x+228,at,title,11.4,'ExtraBold',tone)
        txt(x+324,at+1,detail,10.3,'Medium',tone)
        line(x+203,at+22,x+w-9,at+22,LINE,.7)


def mount_options(x,y,w,h):
    for index,(head,sub) in enumerate([('책상 거치','폰 화면 쪽을 책으로'),('후드티 안쪽','렌즈를 가슴 높이에')]):
        a=x+index*248
        rect(a,y,231,181,WHITE,LINE,8)
        txt(a+14,y+9,head,12.2,'ExtraBold',GREEN)
        txt(a+14,y+28,sub,9.8,'Medium',GRAY)
        line(a+17,y+145,a+211,y+145,GRAY,1.4)
        if index == 0:
            line(a+37,y+144,a+63,y+78,GRAY,4)
            poly([(a+62,y+69),(a+71,y+71),(a+94,y+119),(a+85,y+124)],INK)
            circle(a+69,y+77,4,AMBER)
            arrow(a+72,y+81,a+150,y+131,AMBER)
        else:
            circle(a+60,y+62,14,'#B6CCC0')
            poly([(a+30,y+97),(a+45,y+79),(a+76,y+81),(a+93,y+122),(a+38,y+134)],'#C4DCD1')
            line(a+46,y+82,a+80,y+123,GREEN,4)
            poly([(a+57,y+87),(a+65,y+83),(a+86,y+114),(a+78,y+120)],INK)
            circle(a+66,y+87,4,AMBER)
            arrow(a+69,y+91,a+154,y+132,AMBER)
        book(a+129,y+125,60,20)
        txt(a+15,y+155,'노란 점이 전면 렌즈',9.8,'Bold',AMBER)


def hoodie_cutaway(x,y,w,h):
    txt(x+w/4,y+1,'후드티 겉모습',11,'ExtraBold',GREEN,'center')
    txt(x+3*w/4,y+1,'촬영할 때 옷 안 단면',11,'ExtraBold',GREEN,'center')
    top=y+22
    height=h-22
    asset=HERE/'phone-front-hoodie.png'
    source=ImageReader(str(asset))
    sw,sh=source.getSize()
    scale=max(w/sw,height/sh)
    dw,dh=sw*scale,sh*scale
    c.saveState()
    visible=c.beginPath()
    visible.rect(x,H-top-height,w,height)
    c.clipPath(visible,stroke=0,fill=0)
    c.drawImage(source,x+(w-dw)/2,H-top-height/2-dh/2,dw,dh)
    c.restoreState()
    lens_x=x+(w-dw)/2+.751*dw
    lens_y=top+(height-dh)/2+.278*dh
    arrow(lens_x+35,lens_y,lens_x+8,lens_y,'#F8CB72')
    rect(lens_x+34,lens_y-9,71,18,WHITE,radius=4)
    txt(lens_x+41,lens_y-7,'A 전면 렌즈',9, 'Bold', GREEN)


def lens_clearance(x,y,w,h):
    for index,(heading,gap,color) in enumerate([('천이 가까운 경우',19,GREEN),('천이 유리에서 뜬 경우',57,AMBER)]):
        ax=x+index*248
        rect(ax,y,230,112,WHITE,LINE,7)
        txt(ax+11,y+7,heading,11,'ExtraBold',color)
        apex=(ax+38,y+70)
        line(apex[0],y+45,apex[0],y+95,BLUE,3)
        circle(*apex,4,PURPLE)
        cloth=ax+38+gap
        if index:
            split=32*gap/82
            for sign in (-1,1):
                target_y=apex[1]+sign*32
                clipped_y=apex[1]+sign*split
                line(*apex,cloth,clipped_y,GREEN,1.2)
                line(cloth,clipped_y,ax+120,target_y,GRAY,.8,(2,2))
        else:
            line(*apex,ax+120,y+38,GREEN,1.2)
            line(*apex,ax+120,y+102,GREEN,1.2)
        empty=12
        line(cloth,y+46,cloth,y+70-empty,INK,5)
        line(cloth,y+70+empty,cloth,y+94,INK,5)
        txt(ax+139,y+49,'파랑  유리',9.5,'Bold',BLUE)
        txt(ax+139,y+68,'검정  천',9.5,'Bold',INK)
        txt(ax+139,y+87,'초록  화각',9.5,'Bold',GREEN)


def write_phone_pages():
    p=Page(91,PHONE,'사진에서 진동까지','폰은 문제 사진을 보내고, 노트북은 풀이 결과나 다시 찍을 내용을 돌려줍니다. 폰은 신호를 요청한 뒤 처리 결과를 노트북에 알립니다.',('폰 → 노트북','노트북 → 폰','앱 확인'))
    p.flow([('사진 전송','폰에서 교재 촬영'),('판별과 취합','문항과 보기 확인'),('풀이','읽힌 문항부터 처리'),('진동과 회신','앱이 진동 후 회신')],
           '**그림 1**  PC 진행 화면에서 사진 수신, 문항별 풀이, 폰의 신호 확인을 차례로 볼 수 있습니다.',105)
    p.table(('첫 진동','뜻','뒤에 오는 내용'),(126,112,CW-238),[
        ('**짧게 두 번**','답 도착','문항 번호 → 1.9초 쉼 → 정답 보기'),
        ('**길게 두 번**','다시 촬영','다시 비출 문항 번호. 번호가 없으면 진행 기록을 봅니다.'),
        ('**길게 한 번, 짧게 한 번**','내 답 확인','표시한 답과 풀이 답이 다른 문항 번호 → 1.9초 쉼 → 풀이 답'),
    ],size=10.9)
    p.note('3번의 정답이 ④라면','**짧게 두 번 → 1.1초 쉼 → 짧게 세 번 → 1.9초 쉼 → 짧게 네 번.** 가장 긴 쉼 뒤의 횟수가 보기 번호입니다. 문항번호는 **13쪽 숫자표**를 보세요.','why')
    p.steps([
        ('사진을 보낼 때','앱에서 **촬영 시작**을 누릅니다. 한 장에 여러 문항이 있으면 읽힌 문항부터 풀이에 들어갑니다. 서로 이어지는 지문과 보기는 근거가 맞을 때 합칩니다.'),
        ('답을 받을 때','앱은 진동을 요청하고 결과를 회신합니다. PC의 **앱 확인**은 폰이 신호를 처리했다는 뜻입니다. 진동을 느낄 수 있는지는 **설정 → 짧게와 길게**으로 확인합니다.'),
    ],size=11.1)
    p.finish(103,'폰을 기본으로 고른 이유')
    write_decision()

    p=Page(92,PHONE,'화면에서 전면 렌즈 찾기','폰을 똑바로 세워 **화면**을 보세요. 앱이 쓰는 렌즈는 **화면 위쪽 가운데 작은 원**입니다.',('Galaxy S25 Ultra','SM-S938N','Camera2 ID 1'))
    p.figure(215,'**그림 2**  왼쪽이 앱이 쓰는 전면입니다. 오른쪽 후면의 작은 검은 원 중 5번은 레이저 AF 센서입니다.',lens_map)
    p.table(('앱에서 확인','적용값'),(142,CW-142),[
        ('전면 고정','전면 Camera2 **ID 1**, 실초점거리 **3.3mm**, 삼성 표기 **80°**.'),
        ('사진 크기','**4000 × 3000 JPEG**, 1,200만 화소. 실제 기기에서 이 크기로 설정했습니다.'),
        ('초점','책 가운데 연속 자동초점. 미리보기를 한 번 누르면 중앙에서 다시 맞춥니다.'),
    ],size=11.2)
    p.note('실물에서 확인하는 법','폰 화면이 태블릿을 향하게 합니다. 미리보기에서 화면 위쪽 작은 원을 종이로 가까이 가렸다가 떼어, 화면이 가려졌다 돌아오는지 보세요.','why')
    p.links([('삼성 국내 모델 사양',SAMSUNG),('삼성 카메라 화각',VIEW_ANGLES),('후면 카메라 배치',REPAIR)])
    p.finish(96,'책상에서 위치 잡기')

    p=Page(96,PHONE,'책상에서 위치 잡기','받침은 **폰의 하단과 양옆**을 잡고, 카메라 영역을 열어 두는 형태면 됩니다.',('35~45cm 참고','고정 위치','중앙 연속 자동초점'))
    p.figure(207,'**그림 3**  전면 렌즈가 책을 향하는 위치를 표시했습니다. 고정한 상태에서 미리보기와 원본을 비교하세요.',mount_options)
    p.steps([
        ('빈 받침에 먼저 얹기','스마트폰 거치대나 흔들리지 않는 받침에 폰을 올립니다. USB-C 쪽을 아래에 두면 렌즈가 위에 있습니다. 충전할 계획이면 받침의 USB-C 자리를 확인합니다.'),
        ('한 쪽부터 화면에 맞추기','설치를 시작할 때 렌즈에서 책 중앙까지 **35~45cm**를 참고합니다. 이 거리는 참고값입니다. 촬영은 정해 둔 각도 그대로 시작합니다.'),
        ('작은 글씨로 합격 확인','필요하면 미리보기를 한 번 눌러 초점을 다시 맞춥니다. 같은 위치에서 문항 번호, 지문 첫 줄과 마지막 보기가 기록에 들어왔는지 봅니다.'),
    ],size=11.3)
    p.note('태블릿에서 읽기','고정된 위치에서 PDF를 엽니다. 반사나 줄무늬가 보이면 태블릿 화면 밝기를 조절해 비교합니다. 지문이나 보기가 잘리면 빠진 부분도 들어오도록 문제지를 이어서 보여 줍니다.','why')
    p.finish(97,'후드티 안에 넣기')

    p=Page(97,PHONE,'세로와 가로 거치','세로는 기존 가슴 주머니에 넣고, 가로는 폰 폭을 받칠 수 있는 별도 안쪽 주머니를 씁니다. S25 울트라 본체는 **162.8 × 77.6 × 8.2mm, 218g**입니다.',('세로 가슴 주머니','가로 안쪽 주머니','렌즈 가림 확인'))
    p.figure(256,'**그림 4**  별도 안쪽 거치 구조의 예입니다. 어느 방향이든 화면 쪽 렌즈가 책을 향하고 천이 시야를 가리지 않는지 확인합니다.',hoodie_cutaway)
    p.table(('실측 위치','직접 적는 값과 확인'),(142,CW-142),[
        ('케이스를 씌운 폰','높이 [　]mm, 폭 [　]mm, 돌출부 포함 두께 [　]mm, 부착 도구를 포함한 무게 [　]g.'),
        ('세로로 넣기','가슴 주머니에 폰을 세로로 넣습니다. 전면 렌즈가 주머니 입구 위에 오도록 맞추고 앱 상단에서 **세로**를 고릅니다.'),
        ('가로로 넣기','케이스를 씌운 폰이 들어갈 폭으로 안쪽 주머니를 따로 준비합니다. 하단과 양옆을 받치고 앱 상단에서 **가로**를 고릅니다.'),
    ],size=10.9)
    p.note('가슴에서 쓰는 경우','본체와 케이스 무게를 옷감 한 점에 걸면 자세에 따라 처집니다. 탈착식 받침을 넓게 잡고, 먼저 앉기, 책장 넘김, 상체 숙이기에서 위치가 유지되는지 확인하세요.','warning')
    p.links([('삼성 크기와 무게',SAMSUNG)])
    p.finish(102,'구멍과 초점 시험')

    p=Page(102,PHONE,'구멍과 초점 시험','원형 구멍은 전면 렌즈 중심에 맞춥니다. 천 두께와 들뜸을 포함해, 미리보기에서 네 모서리가 잘리는지 확인하세요.',('전면 80°','후면 초광각 120°','종이로 먼저 확인'))
    p.figure(146,'**그림 5**  렌즈 외부 유리와 천이 멀어질수록, 같은 구멍의 가장자리가 더 많은 빛을 막습니다.',lens_clearance)
    p.steps([
        ('옷 대신 종이로 맞추기','평소 착용하는 자세에서 렌즈 중심을 표시합니다. 검은 종이로 천의 위치를 재현한 뒤 원을 열고 가림이 생기는지 봅니다.'),
        ('들뜬 거리만큼 여유 주기','단순 기하로 전면 **80°**의 경우 천이 1mm 더 멀어질 때 구멍 지름 여유가 **약 1.7mm** 늘어납니다. 후면 초광각 **120°**는 약 **3.5mm**입니다. 이는 이미 잘 보이는 구멍에서 더 필요한 여유이며 최종 지름은 실물 화면으로 잡습니다.'),
        ('가림과 초점을 구분하기','모서리만 검어지면 천을 유리에 더 가까이 두거나 원을 넓힙니다. 가운데 글씨도 흐리면 천을 떼고 터치 재초점부터 합니다. 같은 자리에서 천을 대기 전후를 비교합니다.'),
    ],size=11.15)
    p.note('구멍 크기 결정','기본 카메라 유리는 유지합니다. 천의 끝처리와 착용 중 흔들림까지 넣어 확인한 후 실제 옷의 크기를 정합니다. 전면 렌즈는 한 쪽을 선명하게 담는 쪽으로 구도를 맞춥니다.','why')
    p.links([('삼성 전면과 후면 화각',VIEW_ANGLES)])
    p.finish(93,'Tailscale에 로그인')

    p=Page(93,NETWORK,'Tailscale에 로그인','처음 한 번, 노트북과 폰을 같은 개인 계정으로 연결합니다. 노트북은 집 Wi-Fi, 폰은 LTE나 5G여도 됩니다.',('Windows 앱','Android 앱','같은 계정'))
    p.flow([('집 노트북','Windows 설치와 로그인'),('휴대폰','VPN 요청에 확인'),('장치 확인','같은 개인 계정'),('주소 복사','노트북의 100.x 주소')],'**그림 6**  Tailscale은 폰에서 집 노트북으로 가는 개인 네트워크를 만듭니다.',100)
    p.steps([
        ('Windows','Tailscale을 설치하고 작업표시줄 오른쪽 아이콘에서 **Log in**을 눌러 개인 계정으로 로그인합니다.'),
        ('Android','Play 스토어에서 **Tailscale**을 설치합니다. 처음 보이는 **VPN 연결 요청 → 확인**을 누르고 Windows와 같은 계정으로 로그인합니다.'),
        ('노트북 사설 주소 확인','PowerShell에서 아래 명령을 입력합니다. **ip -4**에 나온 숫자가 학습 보조기 앱에서 사용할 주소입니다.'),
    ])
    p.code('Windows PowerShell',[TAILSCALE_PATH,'& $ts status','& $ts ip -4'])
    p.note('입력할 주소','폰에서는 위 명령이 출력한 내 노트북 주소를 씁니다. 주소 앞에 http://, 뒤에 :8786을 붙입니다.','why')
    p.links([('Tailscale Windows 설치',WINDOWS),('Tailscale Android 설치',ANDROID)])
    p.finish(98,'노트북 서버 열기')

    p=Page(98,NETWORK,'노트북 서버 열기','학습 보조기 서버와 Tailscale을 켜 둡니다.',('로컬 서버 8786','개인 사설망 전달','노트북 절전 확인'))
    p.flow([('폰의 앱','100.x:8786'),('Tailscale','사설망을 통해 전달'),('노트북 서버','127.0.0.1:8786')],'**그림 7**  폰 요청은 Tailscale을 지나 노트북에서 실행 중인 학습 보조기 서버에 도착합니다.',89)
    p.steps([
        ('처음 설치한 PC에서 서버 켜기','실습 ZIP의 **휴대폰** 폴더를 열고 아래 명령을 실행합니다. Python, Pillow와 로그인된 Codex CLI가 필요합니다. 처음 실행할 때 폰 연결 키 파일을 만듭니다.'),
    ])
    p.code('첫 번째 Windows PowerShell / 서버 창을 켜 둠',['python -m pip install Pillow opencv-python-headless','powershell -ExecutionPolicy Bypass -File ./start_phone.ps1'])
    p.code('두 번째 Windows PowerShell / 최초 1회',[TAILSCALE_PATH,'& $ts serve --bg --tcp=8786 tcp://127.0.0.1:8786','& $ts serve status'])
    p.body('폰 **학습 보조기 → 설정**에서 내 노트북의 Tailscale 주소와 연결 키를 저장합니다. 저장소의 **etc/phone**이나 실습 ZIP의 **휴대폰**에서 start_phone.ps1을 실행합니다.',size=10.8)
    p.note('집에서 나가기 전에','노트북을 전원에 연결합니다. Windows 설정에서 **절전**을 검색해 사용 중 시스템을 깨어 있게 합니다. 덮개를 닫으면 절전되는 설정이라면 덮개는 열어 둡니다.','warning')
    p.links([('Tailscale Serve 명령',SERVE)])
    p.finish(104,'앱 설치와 첫 연결')
    write_install()

    p=Page(94,PRACTICE_CHAPTER,'첫 촬영과 진동','미리보기와 진행 기록으로 촬영 상태를 확인합니다. 중앙 상태와 전송, 저장, 촬영 간격을 보고, 진동 파형에서 신호 종류를 확인합니다.',('짧게 0.14초','길게 0.62초','보기 전 1.9초 쉼'))
    p.flow([('짧게 두 번','한 문항의 시작'),('문항번호','숫자별 진동'),('1.9초 쉼','보기 앞 가장 긴 쉼'),('짧게 1~5번','보기 번호')],'**그림 8**  한 묶음 안은 0.24초, 다음 자리 앞은 1.1초, 답 앞은 1.9초 쉽니다.',96)
    p.steps([
        ('진동 시험','**설정 → 짧게와 길게**로 길이를 비교하세요. **17번 답 ③ 시험**에서는 가장 긴 쉼 뒤에 짧게 세 번 울립니다. 진동 세기는 같은 곳에서 조절합니다.'),
        ('화면에서 신호 보기','파형이 **시작 → 문항번호 → 보기 구분 → 보기 번호** 순서로 움직입니다. **마지막 진동 요청**은 앱이 요청한 신호를 보여 줍니다. 느껴지는 세기는 착용한 채 진동 시험으로 확인하세요.'),
        ('17번, 보기 ③ 예시','**시작 두 번 → 숫자 1 → 숫자 7 → 1.9초 쉼 → 짧게 세 번**입니다. 문항번호의 숫자별 진동 조합은 **13쪽 문항번호 진동표**를 보세요.'),
    ])
    p.table(('신호의 첫 진동','뒤에 오는 정보'),(151,CW-151),[
        ('**짧게 두 번**','답 도착. 문항번호 → 보기 구분 → 보기 번호.'),
        ('**길게 두 번**','다시 촬영. 누락 문항번호를 보냅니다. 번호를 읽지 못했다면 첫 신호만 옵니다.'),
        ('**길게 한 번, 짧게 한 번**','내 답 확인. 문항번호 → 보기 구분 → 풀이 답. 체크나 손글씨 답이 두 장에서 같을 때 확인합니다.'),
    ],size=10.7)
    p.note('검은 화면과 사진 목록','촬영하거나 답을 기다릴 때 **화면 끄기**를 누릅니다. **볼륨 올림 → 내림 → 올림 → 내림**을 4초 안에 누르면 돌아옵니다. **받은 사진**은 가로 세 열, 세로 두 열입니다. 상세에서 뒤로 가면 보던 목록으로 돌아옵니다.','why')
    p.finish(110,'문항번호 진동표')
    write_vibration_numbers()

    p=Page(100,PRACTICE_CHAPTER,'폰 데이터로 연결 시험','집에서 먼저 폰의 Wi-Fi만 잠깐 끄고 시험합니다. 노트북은 집 Wi-Fi에 연결해 둡니다.',('LTE 또는 5G','사진 전송 확인','누락 지점 찾기'))
    p.flow([('폰 Wi-Fi 끄기','LTE 또는 5G 표시'),('Tailscale 확인','폰에서 연결됨'),('촬영 시작','책 한 쪽 보여 주기'),('전송 수 확인','가운데 진행 기록')],'**그림 9**  전송 장수와 노트북의 받은 사진을 함께 확인합니다.',96)
    p.table(('화면에 보이는 상태','맞춰 볼 곳'),(151,CW-151),[
        ('사진 전송 실패','두 기기의 Tailscale과 노트북 전원을 확인합니다. 촬영 중에도 **설정 → 연결 확인**에서 주소와 연결 키를 검사할 수 있습니다.'),
        ('문항을 확인하는 중','총괄 세션이 사진에서 풀 문항을 찾는 단계입니다. 진행 기록에서 문항번호가 찍히는지 확인합니다.'),
        ('책 한 쪽을 가운데에','미리보기에서 반사, 손 가림, 지문 잘림을 확인합니다.'),
        ('사진은 갔는데 답이 늦음','PC **작업 대기열**에서 판별 대기와 풀이 대기를 구분합니다. 풀이가 오래 걸리면 **설정 → 모델 설정**에서 빠르게 또는 균형을 고릅니다.'),
    ],size=11.2)
    p.note('촬영을 중지한 뒤','노트북은 대기 중인 사진을 계속 처리합니다. **설정 → 확인할 문항 범위**에 1-10처럼 입력하면 아예 인식하지 못한 끝 번호도 알립니다. **다시 촬영할 문항**의 지문과 보기를 비추세요.','why')
    p.body('**태블릿 시험**  다음 쪽의 기출 자료에서 번호를 두 개 골라 차례로 보여 주고, 답이 도착하면 문제지에 적어 정답표와 대조합니다. 아래 생활과 윤리 PDF로 같은 시험을 할 수도 있습니다.',size=10.8)
    p.links([('EBSi 공개 문제지, 9월 모의평가 생활과 윤리',PRACTICE)])
    p.finish(105,'공개 문제지 실습')
    write_practice()
    write_fixed_angle()

    p=Page(95,WORK,'문항별 풀이와 답 알림','첫 사진부터 문항을 확인하고, 새 문항을 찾으면 번호별로 풀이를 시작합니다.',('GPT 총괄','문항별 세션','한 번에 한 진동'))
    p.flow([('사진 수신','3~6초 간격으로 도착'),('문항 확인','Codex 구독'),('문항별 풀이','17번과 18번 병렬'),('진동','답 먼저 나온 순서')],'**그림 11**  18번 답이 먼저 나오면 18번부터 울립니다. 뒤에 나온 17번 답도 쪽을 넘긴 뒤 받을 수 있습니다.',101)
    p.steps([
        ('새 문제를 발견하면','한 장에 여러 문항이 있으면 읽힌 문항을 각각 풀이에 넣습니다. 기본은 동시 두 문항입니다. 화면의 **설정 → 모델 설정**에서 속도와 풀이 모델을 고릅니다.'),
        ('열이나 쪽에서 끊긴 문제','같은 교재와 문항의 이어지는 사진은 최대 여덟 장까지 취합합니다. 글 몇 줄이 다음 사진에도 보이게 비춥니다. 지문이나 끝 보기가 다 확인될 때 풉니다.'),
        ('답을 놓친 경우','풀이 답은 한 번씩 알리고, 다음 답까지 최소 4초 쉽니다. 폰의 **진행 기록**이나 PC의 **지금 진행**에서 과목, 문항번호, 보기를 확인하세요.'),
    ])
    p.note('영어 듣기 연습','실습 ZIP의 **휴대폰/README.md**에서 문항별 시간표와 음원 파일을 준비합니다. 노트북이 자막을 만든 뒤, 폰이 읽은 문항번호에 맞는 듣기 내용을 사진과 함께 풉니다.','violet')
    p.finish(107,'노트북 진행 화면')
    write_monitor()
    write_listening()
    write_history()

    p=Page(101,WORK,'12시간 전원 시험','S25 울트라 배터리는 **5,000mAh**입니다. 12시간 사용은 외부 전원을 준비해 처음부터 끝까지 실제로 재야 합니다.',('100% → 10%','시간당 7.5%p','2시간 실측'))
    p.flow([('시작 기록','배터리 잔량과 시간'),('두 시간 사용','검은 화면과 절전'),('종료 기록','잔량, 발열, 사진 수'),('12시간 판단','15%p 소모 이하')],'**그림 13**  두 시간 동안 촬영과 전송이 계속됐는지 보고, 소모율로 목표를 가늠합니다.',94)
    p.table(('2시간 소모 예','10%를 남길 때의 단순 환산'),(154,CW-154),[
        ('12%p','시간당 6%p, 약 15시간. 12시간 연속 시험 후보.'),
        ('15%p','시간당 7.5%p, 약 12시간. 여유가 적습니다.'),
        ('20%p','시간당 10%p, 약 9시간. 중간 충전이 필요합니다.'),
    ],size=11.2)
    p.body('장시간 시험에는 USB-C 외부 전원을 준비합니다. 충전 중에 케이블이 받침이나 렌즈를 누르지 않는지 확인하고, 노트북에도 전원을 연결합니다. 시작과 끝의 잔량, 발열, 전송한 사진 수, 휴대폰 데이터 사용량을 적습니다.',size=11.25)
    p.note('12시간 합격 기준','2시간 결과는 예상 범위입니다. 같은 통신 환경과 촬영 간격에서 실제로 **12시간** 동안 연결과 답 수신이 이어지는지 확인해야 합니다. 검은 화면을 써도 촬영과 전송은 전력을 씁니다.','why')
    p.links([('삼성 배터리 사양',SAMSUNG)])
    p.finish(4,'라즈베리파이 구성')
