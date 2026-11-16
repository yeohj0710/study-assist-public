import math
import os
import re
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent
TITLE = '학습 보조기 제작 가이드'
VERSION = '2611152300'
PDF_NAME = f'{TITLE}_{VERSION}.pdf'
ZIP_NAME = f'학습 보조기 실습_{VERSION}.zip'
W, H = A4
M = 42
R = W - M
CW = R - M
INK = '#172623'
GRAY = '#465A55'
GREEN = '#176246'
DARK = '#103F32'
MINT = '#DDF2E5'
PALE = '#EFF7F2'
LINE = '#CCDAD4'
YELLOW = '#FFF0A4'
AMBER = '#844604'
CREAM = '#FFF4E7'
BLUE = '#205397'
SKY = '#EAF2FD'
PURPLE = '#603A97'
LILAC = '#F2ECFC'
WHITE = '#FFFFFF'

for face in ('Regular', 'Medium', 'SemiBold', 'Bold', 'ExtraBold'):
    pdfmetrics.registerFont(TTFont(face, str(ASSETS / f'Pretendard-{face}.ttf')))
for face in ('Regular', 'Medium', 'SemiBold', 'Bold', 'ExtraBold'):
    pdfmetrics.registerFontFamily(face, normal=face, bold='Bold', italic=face, boldItalic='Bold')

OUTPUT_DIR = Path(os.environ.get('STUDY_GUIDE_OUTPUT_DIR', HERE))
c = canvas.Canvas(str(OUTPUT_DIR / PDF_NAME), pagesize=A4, pageCompression=1)
c.setTitle(TITLE)
c.setSubject('갤럭시 촬영과 진동 실습, Tailscale과 집 노트북 연결, 라즈베리파이 제작 부록')


PAGE_ORDER = (1, 2, 91, 103, 92, 96, 97, 102, 93, 98, 104, 94, 110,
              100, 105, 106, 95, 107, 108, 109, 101, 4)


def printed_page(number):
    return PAGE_ORDER.index(number) + 1


def styled(text):
    text = escape(str(text)).replace('\n', '<br/>')
    for pattern, start, end in (
        (r'\*\*(.+?)\*\*', '<b>', '</b>'),
        (r'==(.+?)==', '<span backColor="#FFF0A4"><b>', '</b></span>'),
        (r'__(.+?)__', '<u><b>', '</b></u>'),
        (r'\[\[(.+?)\]\]', '<font color="#176246"><b>', '</b></font>'),
    ):
        text = re.sub(pattern, lambda match: start + match[1] + end, text)
    return text


def txt(x, y, text, size=12, weight='Regular', color=INK, align='left'):
    c.setFillColor(HexColor(color))
    c.setFont(weight, size)
    method = {'left': c.drawString, 'center': c.drawCentredString, 'right': c.drawRightString}[align]
    method(x, H-y-size, text)


def paragraph(x, y, text, width=CW, size=12, leading=None, color=INK, align=0, raw=False):
    style = ParagraphStyle('body', fontName='Regular', fontSize=size, leading=leading or size*1.45,
                           textColor=HexColor(color), alignment=align, wordWrap='CJK', splitLongWords=0)
    p = Paragraph(text if raw else styled(text), style)
    _, height = p.wrap(width, H)
    p.drawOn(c, x, H-y-height)
    return height


def rect(x, y, width, height, fill=WHITE, stroke=None, radius=8):
    if fill:
        c.setFillColor(HexColor(fill))
    if stroke:
        c.setStrokeColor(HexColor(stroke))
        c.setLineWidth(.8)
    c.roundRect(x, H-y-height, width, height, radius, fill=bool(fill), stroke=bool(stroke))


def line(x, y, x2, y2, color=LINE, width=1, dash=()):
    c.setStrokeColor(HexColor(color))
    c.setLineWidth(width)
    c.setDash(list(dash))
    c.line(x,H-y,x2,H-y2)
    c.setDash([])


def circle(x, y, radius, fill):
    c.setFillColor(HexColor(fill))
    c.circle(x, H-y, radius, fill=1, stroke=0)


def poly(points, fill):
    path = c.beginPath()
    path.moveTo(points[0][0], H-points[0][1])
    for x, y in points[1:]:
        path.lineTo(x, H-y)
    path.close()
    c.setFillColor(HexColor(fill))
    c.drawPath(path, fill=1, stroke=0)


def arrow(x, y, x2, y2, color=GREEN, dash=()):
    line(x,y,x2,y2,color,1.65,dash)
    angle = math.atan2(y2-y, x2-x)
    poly([(x2,y2),(x2-8*math.cos(angle-.45),y2-8*math.sin(angle-.45)),
          (x2-8*math.cos(angle+.45),y2-8*math.sin(angle+.45))],color)


def wrapped_image(path, x, y, width, height):
    c.drawImage(str(path), x, H-y-height, width, height, mask='auto')


def jump(page, x1, y1, x2, y2):
    c.linkRect('', f'p{page}', (x1, H-y2, x2, H-y1), relative=0, thickness=0)


def href(label, address):
    return f'<link href={quoteattr(address)} color="{BLUE}"><u><b>{escape(label)}</b></u></link>'


class Page:
    def __init__(self, number, chapter, title, intro, keywords=()):
        self.number = number
        self.title = title
        c.bookmarkPage(f'p{number}')
        c.addOutlineEntry(f'{printed_page(number):02d}  {title}', f'p{number}', 0)
        group=chapter.split(' ', 1)[0]
        self.appendix=group.startswith('부록')
        rect(M,35,38,23,BLUE if self.appendix else GREEN,radius=4)
        txt(M+19,38,group,9.8 if self.appendix else 11,'ExtraBold',WHITE,'center')
        txt(M+48,39,chapter.split(' ', 1)[1],11.2,'Bold',GREEN)
        txt(M,61,title,29,'ExtraBold')
        line(M,105,R,105,GREEN,1.8)
        x = M
        for keyword in keywords:
            width = pdfmetrics.stringWidth(keyword,'Bold',9.7)+19
            rect(x,115,width,20,PALE,LINE,8)
            txt(x+9,119,keyword,9.7,'Bold',GREEN)
            x += width+6
        top = 146 if keywords else 118
        self.y = top+paragraph(M,top,intro,size=12.3)+17

    def head(self, text):
        line(M,self.y+2,M,self.y+19,GREEN,3)
        txt(M+9,self.y,text,15,'ExtraBold')
        self.y += 25

    def body(self, text, pad=10, size=12):
        if self.appendix:
            text=text.replace('**그림 ','**부록 그림 ')
        self.y += paragraph(M,self.y,text,size=size)+pad

    def note(self, title, text, tone='green'):
        background, accent = {
            'green':(PALE,GREEN),'warning':(CREAM,AMBER),'why':(SKY,BLUE),'violet':(LILAC,PURPLE)
        }[tone]
        size = 11.7
        style=ParagraphStyle('measure',fontName='Regular',fontSize=size,leading=size*1.45,wordWrap='CJK')
        _, height=Paragraph(styled(text),style).wrap(CW-32,H)
        total=height+47
        rect(M,self.y,CW,total,background)
        line(M+2,self.y+5,M+2,self.y+total-5,accent,3)
        txt(M+15,self.y+9,title,12.6,'ExtraBold',accent)
        paragraph(M+15,self.y+31,text,CW-32,size)
        self.y += total+13

    def steps(self, entries, size=11.75):
        start=self.y
        for index,(title,desc) in enumerate(entries,1):
            y=self.y
            circle(M+11,y+9,10,GREEN)
            txt(M+11,y+2,str(index),10.2,'ExtraBold',WHITE,'center')
            txt(M+31,y,title,13,'ExtraBold')
            height=paragraph(M+31,y+21,desc,CW-32,size)
            self.y += height+36
            if index < len(entries):
                line(M+11,y+20,M+11,self.y-2,LINE,1.3)
        if self.y == start:
            raise ValueError('Empty step list')

    def code(self, label, lines):
        height=42+18*len(lines)
        rect(M,self.y,CW,height,'#17332C')
        txt(M+13,self.y+9,label,10,'Bold','#BDE7D5')
        for i,row in enumerate(lines):
            if pdfmetrics.stringWidth(row,'Medium',10.1)>CW-28:
                raise ValueError(f'Page {self.number} command too wide: {row}')
            txt(M+13,self.y+28+18*i,row,10.1,'Medium',WHITE)
        self.y += height+13

    def links(self, links):
        x=M
        y=self.y
        size=10.5
        for label,url in links:
            width=pdfmetrics.stringWidth(label,'Bold',size)
            if x+width>R:
                x=M
                y+=18
            txt(x,y,label,size,'Bold',BLUE)
            line(x,y+size+2,x+width,y+size+2,BLUE,.6)
            c.linkURL(url,(x,H-y-size-4,x+width,H-y+2),relative=0,thickness=0)
            x+=width+18
        self.y=y+23

    def figure(self, height, description, draw, fill=PALE):
        if self.appendix:
            description=description.replace('**그림 ','**부록 그림 ')
        y=self.y
        rect(M,y,CW,height,fill,LINE)
        draw(M+13,y+12,CW-26,height-24)
        self.y += height+7
        self.y += paragraph(M,self.y,description,size=10.5,color=GRAY)+15

    def flow(self, nodes, description, height=87, tones=None):
        def draw(x,y,w,h):
            spacing=21
            width=(w-spacing*(len(nodes)-1))/len(nodes)
            for i,(title,detail) in enumerate(nodes):
                start=x+(width+spacing)*i
                color,fill=(tones or [(GREEN,WHITE)]*len(nodes))[i]
                rect(start,y,width,h,fill,LINE,7)
                txt(start+width/2,y+8,title,11.9,'ExtraBold',color,'center')
                paragraph(start+6,y+27,detail,width-12,9.9,13.6,GRAY,align=1)
                if i+1 < len(nodes):
                    arrow(start+width+2,y+h/2,start+width+spacing-2,y+h/2,color)
        self.figure(height,description,draw)

    def table(self, headings, widths, rows, x=M, size=11, price=False):
        if abs(sum(widths)-CW)>.02:
            raise ValueError(f'Page {self.number} table widths do not fit')
        self.y+=3
        for n,row in enumerate([headings,*rows]):
            ps = []
            is_total=price and str(row[0]).startswith('합계')
            for i,(val,width) in enumerate(zip(row,widths)):
                use_raw = isinstance(val, tuple)
                source = href(*val) if use_raw else styled(str(val))
                if n==0 or is_total:
                    source=f'<b>{source}</b>'
                align = 2 if price and i >= 2 else 0
                style=ParagraphStyle('cell',fontName='Regular',fontSize=size,leading=size*1.31,
                                     textColor=HexColor(GREEN if n==0 or is_total else INK),
                                     wordWrap='CJK',alignment=align,splitLongWords=0)
                p=Paragraph(source,style)
                _,height=p.wrap(width-15,H)
                ps.append((p,height,width))
            row_h=max(h for _,h,_ in ps)+13
            fill = MINT if n==0 or is_total else WHITE if n%2 else '#F5F8F6'
            rect(x,self.y,CW,row_h,fill,radius=3)
            col=x
            for cell,height,width in ps:
                cell.drawOn(c,col+7,H-self.y-6-height)
                col+=width
            line(x,self.y+row_h,R,self.y+row_h,LINE,.6)
            self.y+=row_h
        self.y+=13

    def finish(self, next_page=None, next_label=None):
        if self.y > 790:
            raise ValueError(f'Page {self.number} content ends at {self.y:.1f}')
        line(M,796,R,796)
        txt(M,806,TITLE,8.7,'Medium',GRAY)
        if self.number != 2:
            txt(M+145,806,'차례',8.8,'Bold',BLUE)
            jump(2,M+143,803,M+175,822)
        if next_page is not None:
            label=f'다음  {next_label}  →'
            txt(R-32,806,label,9.2,'Bold',BLUE,'right')
            jump(next_page,R-38-pdfmetrics.stringWidth(label,'Bold',9.2),802,R-21,822)
        txt(R,804,f'{printed_page(self.number):02d}',11,'ExtraBold',GREEN,'right')
        c.showPage()
