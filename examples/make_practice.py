from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

root = Path(__file__).resolve().parent
for face in ('Regular', 'Bold'):
    pdfmetrics.registerFont(TTFont(face, str(root.parent / 'etc' / 'book' / f'Pretendard-{face}.ttf')))

items = [
    ('국어', '도서관은 시험 기간에 열람실을 한 시간 늦게 닫기로 했다. 같은 기간에 안내 데스크는 종전 시간에 업무를 마친다.',
     '윗글에서 알 수 있는 내용은?',
     ['도서관 전체가 늦게 닫는다.', '열람실과 안내 데스크의 운영 시간이 모두 바뀐다.', '안내 데스크는 종전 시간에 업무를 마친다.', '시험 기간에는 도서 대출을 중단한다.', '열람실은 개관 시간을 한 시간 늦춘다.'],
     3, '안내 데스크는 종전 시간에 업무를 마친다고 직접 밝혔다.'),
    ('영어', 'The museum has free admission on Tuesdays. It is closed on Mondays.',
     'When can visitors enter without paying?',
     ['On Mondays', 'On Tuesdays', 'On Wednesdays', 'On Fridays', 'On Sundays'],
     2, '첫 문장은 화요일에 입장료를 받지 않는다고 설명한다.'),
    ('수학', '', '3x + 5 = 20을 만족하는 x는?',
     ['2', '3', '4', '5', '6'], 4, '양변에서 5를 빼면 3x = 15이다. 양변을 3으로 나누면 x = 5이다.'),
    ('한국사', '', '훈민정음을 반포한 왕은?',
     ['태조', '세종', '성종', '영조', '정조'], 2, '세종은 1446년에 훈민정음을 반포했다.'),
    ('사회문화', '한 연구자가 지역 주민 200명에게 같은 문항을 담은 설문지를 배부했다.',
     '연구자가 사용한 자료 수집 방법은?',
     ['참여 관찰법', '면접법', '실험법', '질문지법', '문헌 연구법'],
     4, '여러 사람에게 같은 표준화된 질문을 제시했다. 질문지법에 해당한다.'),
    ('지구과학 I', '', '북반구에서 하루 동안 물체의 그림자가 가장 짧아지는 때는 대체로 언제인가?',
     ['해가 뜨기 직전', '해가 뜬 직후', '태양이 가장 높이 떠 있을 때', '해가 진 직후', '자정'],
     3, '태양이 가장 높이 뜨면 지표면과 햇빛이 이루는 각이 가장 커지고 그림자가 짧아진다.'),
]
ink=colors.HexColor('#172623')
green=colors.HexColor('#176246')
muted=colors.HexColor('#465A55')
W,H=A4

def heading(c, title, subtitle):
    c.setFillColor(green)
    c.setFont('Bold', 26)
    c.drawString(46,H-58,title)
    c.setFillColor(muted)
    c.setFont('Regular', 11)
    c.drawString(46,H-80,subtitle)
    c.setStrokeColor(colors.HexColor('#CCDAD4'))
    c.line(46,H-95,W-46,H-95)

def block(c, text, x, y, w, size=12, face='Regular', color=ink):
    p=Paragraph(text, ParagraphStyle('text',fontName=face,fontSize=size,leading=size+5,textColor=color))
    _, height=p.wrap(w,H)
    p.drawOn(c,x,y-height)
    return y-height

def page_number(c, n):
    c.setFillColor(muted)
    c.setFont('Regular',10)
    c.drawRightString(W-46,32,str(n))

q=canvas.Canvas(str(root/'practice-questions.pdf'),pagesize=A4,pageCompression=1,invariant=1)
q.setTitle('학습 보조기 연습 문제지')
for page in range(2):
    heading(q,'연습 문제지','학습 보조기  /  문제 촬영과 답 알림 연습')
    y=H-121
    for index,(subject,passage,question,options,_,_) in enumerate(items[page*3:page*3+3],page*3+1):
        y=block(q,f'{index}. {subject}',46,y,W-92,14,'Bold',green)-4
        if passage:
            y=block(q,passage,46,y,W-92)-5
        y=block(q,question,46,y,W-92,12,'Bold')-6
        for mark, option in zip('①②③④⑤',options):
            y=block(q,f'{mark} {option}',53,y,W-99,11)-1
        y-=21
    assert y>53
    page_number(q,page+1)
    q.showPage()
q.save()

a=canvas.Canvas(str(root/'practice-answers.pdf'),pagesize=A4,pageCompression=1,invariant=1)
a.setTitle('학습 보조기 연습 정답표')
heading(a,'연습 정답표','학습 보조기  /  풀이 확인')
y=H-120
for index,(subject,_,_,options,answer,explanation) in enumerate(items,1):
    choice='①②③④⑤'[answer-1]
    y=block(a,f'{index}. {subject}    {choice} {options[answer-1]}',46,y,W-92,13,'Bold',green)-7
    y=block(a,explanation,46,y,W-92)-21
assert y>53
page_number(a,1)
a.save()
