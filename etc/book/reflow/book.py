from layout import *
from figures import *
from purchase import *

chapters=[
    (91,'01','사진과 진동의 왕복','진동 신호 / 폰과 렌즈 선택 / 세로와 가로 거치', '3~8'),
    (93,'02','집 노트북과 앱 연결','Tailscale / Windows 서버 / 앱 설치', '9~11'),
    (94,'03','첫 촬영과 문제지 실습','진동 숫자표 / 폰 데이터 / 기출과 조합 / 고정 각도 사진', '12~16'),
    (95,'04','풀이 확인과 긴 시간 사용','노트북 진행 화면 / 듣기 파일 / 진행 기록 / 전원', '17~21'),
    (4,'부록','라즈베리파이 제작','국내외 구매 / 배선 / 설치 / 시험 / 착용', '22~51'),
]


c.bookmarkPage('p1')
c.addOutlineEntry('01  표지','p1',0)
rect(0,0,W,H,'#F2F8F3',radius=0)
rect(0,0,W,376,DARK,radius=0)
txt(55,54,'갤럭시 S25 울트라 + 집 노트북',13.5,'Bold','#D7EEDA')
txt(52,99,'학습 보조기',44,'ExtraBold',WHITE)
txt(52,157,'제작 가이드',44,'ExtraBold',WHITE)
paragraph(55,233,'휴대폰으로 연습문제를 찍고 답을 진동으로 받습니다.\n앱 설치부터 집 밖 연결까지 따라 합니다.',440,17,26,'#E1F2E8')
line(55,314,R,314,'#6B9280',1)
txt(55,330,'전면 카메라   /   Tailscale 연결   /   문항번호와 진동',12,'Bold','#D7EEDA')
rect(54,409,485,298,WHITE,LINE,14)
from phone_body import home_loop
home_loop(74,441,445,223)
txt(75,673,'라즈베리파이 구매와 조립은 뒤 부록',11,'Bold',GRAY)
rect(0,764,W,78,'#F2F8F3',radius=0)
txt(55,789,'처음이라면 2쪽 차례에서 시작',13,'ExtraBold',BLUE)
jump(2,50,785,270,815)
txt(R,807,f'제작 가이드  {VERSION}',9.5,'Bold',GREEN,'right')
c.showPage()

p=Page(2,'00 읽는 순서','차례와 실습 순서','폰 렌즈부터 찾고, 집 노트북에 연결한 뒤 첫 진동을 시험합니다. 장 제목을 누르면 해당 페이지가 열립니다.')
for page,n,title,detail,range_label in chapters:
    top=p.y
    rect(M,top,CW,58,SKY if n=='부록' else PALE if n in ('01','03') else WHITE,radius=5)
    txt(M+10,top+9,n,13,'ExtraBold',BLUE if n=='부록' else GREEN)
    txt(M+48,top+7,title,14,'ExtraBold',INK)
    txt(R-11,top+9,range_label+'쪽',10.6,'Bold',BLUE,'right')
    paragraph(M+48,top+31,detail,CW-74,10.5,14,GRAY)
    jump(page,M,top,R,top+58)
    line(M,top+58,R,top+58)
    p.y+=66
p.y+=7
p.note('준비물','**안드로이드 폰, 전원이 켜진 Windows 노트북, 개인 연습용 문제지.** 먼저 앱의 연결 확인과 진동 시험을 실행합니다.')
p.note('부품을 사서 만들 때','책 뒤 **라즈베리파이 제작 부록**에서 국내외 부품표, 배선, 설치와 실측까지 이어서 봅니다. 상세 부록 안쪽에 찍힌 쪽 번호는 원래 판의 번호입니다.','why')
p.finish(91,'사진에서 진동까지')

from phone_body import write_phone_pages
write_phone_pages()

p = Page(4, '부록 라즈베리파이 제작', '라즈베리파이 상세 제작',
         '별도 카메라와 진동 모듈을 써 보고 싶을 때 이 부록을 펼칩니다.',
         ('국내외 부품', '배선과 설치', '착용과 실측'))
p.table(('찾을 내용', '이 PDF의 쪽'), (CW-106, 106), [
    ('핫스팟 연결과 광각 계산', '23~28쪽'),
    ('국내와 해외 부품 구매 및 호환', '29~33쪽'),
    ('카메라, 진동 배선과 운영체제 설치', '34~38쪽'),
    ('사진 전송, 문항 풀이와 진동 시험', '39~45쪽'),
    ('착용, 배터리와 합격표', '46~51쪽'),
], size=12)
p.note('쪽 번호 읽기', 'PDF 뷰어에는 **23~51쪽**으로 표시됩니다. 상세 부록에 인쇄된 **14~42쪽** 번호와 내부 이동 링크는 원래 판을 유지합니다.', 'why')
txt(M, p.y, '상세 부록 열기', 13, 'Bold', BLUE)
line(M, p.y+18, M+84, p.y+18, BLUE, .8)
p.finish()
c.save()

import pymupdf

appendix = HERE.parent / 'phone-first-draft' / 'stage' / '라즈베리파이 상세 부록.pdf'
guide_path = OUTPUT_DIR / PDF_NAME
assembled = guide_path.with_suffix('.assembled.pdf')
with pymupdf.open(guide_path) as guide, pymupdf.open(appendix) as original:
    offset = len(guide)
    outline = guide.get_toc()
    guide.insert_pdf(original, links=True)
    outline.extend([level + 1, title, page + offset] for level, title, page in original.get_toc())
    guide.set_toc(outline)
    guide[offset - 1].insert_link({
        'kind': pymupdf.LINK_GOTO,
        'from': guide[offset - 1].search_for('상세 부록 열기')[0],
        'page': offset,
        'to': pymupdf.Point(0, 0),
    })
    guide.save(assembled, garbage=3, deflate=True)
assembled.replace(guide_path)
