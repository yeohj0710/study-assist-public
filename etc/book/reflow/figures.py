from layout import *


def tile(x,y,w,h,title,detail='',color=GREEN,fill=WHITE):
    rect(x,y,w,h,fill,LINE,7)
    txt(x+w/2,y+8,title,11.5,'ExtraBold',color,'center')
    if detail:
        paragraph(x+8,y+28,detail,w-16,9.6,13.1,GRAY,align=1)


def phone(x,y,w,h,label):
    rect(x,y,w,h,DARK,radius=9)
    rect(x+4,y+8,w-8,h-17,WHITE,radius=5)
    circle(x+w/2,y+4,1.6,YELLOW)
    txt(x+w/2,y+h/2-7,label,10.4,'Bold',GREEN,'center')


def laptop(x,y,w,h,label):
    rect(x+8,y,w-16,h-10,DARK,radius=7)
    rect(x+13,y+5,w-26,h-20,WHITE,radius=4)
    rect(x,y+h-11,w,11,'#6D9083',radius=3)
    txt(x+w/2,y+h/2-10,label,11,'Bold',GREEN,'center')


def book(x,y,w,h):
    poly([(x,y+5),(x+w/2,y+1),(x+w,y+5),(x+w,y+h),(x+w/2,y+h-4),(x,y+h)], WHITE)
    line(x+w/2,y+1,x+w/2,y+h-4,GREEN,1)
    for i in range(4):
        yy=y+12+i*(h-16)/5
        line(x+5,yy,x+w/2-5,yy,LINE,1.3)
        line(x+w/2+5,yy,x+w-5,yy,LINE,1.3)


def overview(x,y,w,h):
    base=y+27
    book(x+10,base+19,90,55)
    txt(x+55,base+83,'펼친 책',10.5,'Bold',GREEN,'center')
    tile(x+153,base+16,130,62,'카메라 + Pi','카메라는 Pi와 리본으로 연결')
    laptop(x+w-139,base+7,138,81,'노트북 / 풀이 API')
    arrow(x+103,base+45,x+150,base+45,BLUE)
    arrow(x+286,base+35,x+w-144,base+35,BLUE,(4,3))
    arrow(x+w-144,base+64,x+286,base+64,PURPLE,(4,3))
    txt(x+315,base+17,'사진',9.6,'Bold',BLUE)
    txt(x+306,base+69,'진동 명령',9.6,'Bold',PURPLE)
    arrow(x+218,base+80,x+218,base+108,PURPLE)
    tile(x+151,base+111,134,50,'진동 모듈','번호와 답')
    txt(x+w-6,y+5,'점선 = Wi-Fi',10,'Bold',BLUE,'right')


def hotspot(x,y,w,h,reverse=False):
    phone(x+24,y+8,99,102,'휴대폰')
    laptop(x+w-172,y+12,155,96,'Windows')
    arrow(x+129,y+61,x+w-178,y+61,BLUE,(4,4))
    txt(x+w/2,y+38,'같은 Wi-Fi',11,'ExtraBold',BLUE,'center')
    txt(x+w/2,y+67,'사진은 휴대폰 → 노트북',9.7,'Bold',GRAY,'center')
    txt(x+74,y+119,'사진을 찍어 보냄',10.2,'Bold',GREEN,'center')
    txt(x+w-94,y+119,'사진을 받아 저장',10.2,'Bold',GREEN,'center')
    owner=x+w-96 if reverse else x+72
    txt(owner,y+135,'여기서 핫스팟 켜기',9.8,'Bold',PURPLE,'center')


def optics(x,y,w,h):
    lens=(x+75,y+43)
    rect(x+42,y+20,32,112,DARK,radius=9)
    circle(*lens,5,BLUE)
    end=y+145
    poly([lens,(x+134,end),(x+373,end)],MINT)
    line(*lens,x+253,end,BLUE,1.85,(4,4))
    line(*lens,x+134,end,GREEN,1.4)
    line(*lens,x+373,end,GREEN,1.4)
    line(x+64,end+9,x+w-10,end+9,GRAY,2)
    book(x+184,end-20,150,30)
    txt(x+30,y+4,'가슴',10.5,'Bold',GREEN)
    txt(x+225,y+38,'책 중앙을 향하게',11.8,'ExtraBold',BLUE)
    txt(x+254,end+21,'A4 두 쪽 42 × 29.7cm',10.8,'Bold',GREEN,'center')
    txt(x+w-7,end+8,'책상',9.8,'Bold',GRAY,'right')


def ports(x,y,w,h):
    board_y=y+24
    for i,(label,pin_count,ports_w) in enumerate([('Pi 3 B+',15,171),('Zero 2 WH',22,146)]):
        left=x+18+i*249
        rect(left,board_y,ports_w,90 if i==0 else 72,'#3D805F',DARK,8)
        for pin in range(20):
            circle(left+11+pin*5.4,board_y+12,1.8,YELLOW)
            circle(left+11+pin*5.4,board_y+19,1.8,YELLOW)
        px=left+100 if i==0 else left+ports_w-6
        rect(px,board_y+34,9,22,'#DFB64D',radius=1)
        power_x=left+16 if i==0 else left+109
        rect(power_x,board_y+(86 if i==0 else 67),23,11,'#ABD5F1',radius=2)
        if i==1:
            rect(left+75,board_y+67,21,11,'#C7D6D2',radius=2)
            rect(left-5,board_y+28,11,27,'#C7D6D2',radius=2)
            txt(left+75,board_y+83,'USB',8.1,'Bold',GRAY)
        txt(left,board_y-19,label,12.5,'ExtraBold',GREEN)
        txt(left+47,board_y+29,'40핀 GPIO',9.8,'Bold',WHITE)
        txt(left+19 if i==0 else left+47,board_y+52,f'CSI {pin_count}핀',9.9,'Bold',WHITE)
        arrow(left+69 if i==0 else left+101,board_y+57,px,board_y+49,'#FFF0A4')
        txt(power_x+11,board_y+(111 if i==0 else 103),'PWR IN',10.2,'Bold',BLUE,'center')
        arrow(power_x+11,board_y+(109 if i==0 else 102),power_x+11,board_y+(98 if i==0 else 80),BLUE)


def wiring(x,y,w,h):
    tile(x+57,y,137,48,'Camera Module 3','15핀 카메라 단자')
    tile(x+55,y+78,142,48,'라즈베리파이','보드의 CAMERA / CSI')
    tile(x+55,y+156,142,48,'micro-USB 전원','벽 전원 또는 5V 팩',BLUE,SKY)
    tile(x+339,y+72,139,50,'Grove 모듈','진동 모듈',PURPLE,LILAC)
    arrow(x+125,y+48,x+125,y+77,AMBER)
    arrow(x+125,y+156,x+125,y+128,BLUE)
    arrow(x+198,y+98,x+336,y+98,PURPLE)
    txt(x+215,y+77,'전원과 신호 3가닥',10.1,'Bold',PURPLE)
    txt(x+142,y+57,'카메라 리본',9.8,'Bold',AMBER)
    txt(x+138,y+134,'전원',9.8,'Bold',BLUE)


def pins(x,y,w,h):
    left=x+13; right=x+w-172
    rect(left,y+23,160,144,WHITE,LINE,8)
    rect(right,y+23,159,144,WHITE,LINE,8)
    txt(left+7,y+3,'Pi 물리 핀 번호',11.8,'ExtraBold',GREEN)
    txt(right+12,y+3,'Grove 변환선',11.8,'ExtraBold',PURPLE)
    for i,(a,b,color) in enumerate((
        ('1   3.3V','빨강 VCC','#A6383D'),
        ('6   GND','검정 GND','#4B5460'),
        ('12  GPIO18','노랑 SIG',AMBER)
    )):
        yy=y+38+31*i
        txt(left+14,yy,a,11.7,'Bold',color)
        txt(right+20,yy,b,11.7,'Bold',color)
        circle(left+149,yy+8,4,color)
        arrow(left+155,yy+8,right+15,yy+8,color)
    txt(right+20,y+132,'흰색 NC는 사용 안 함',9.8,'Bold',GRAY)


def pin_corner(x,y,w,h):
    for col in range(6):
        for row in range(2):
            number=col*2+row+1
            cx=x+26+30*col
            cy=y+16+25*row
            fill=GREEN if number in (1,6,12) else '#DDD7D1'
            circle(cx,cy,10,fill)
            txt(cx,cy-7,str(number),10,'Bold',WHITE if number in (1,6,12) else GRAY,'center')
    txt(x+210,y+8,'핀 1에서 홀수 줄을 셉니다',10.7,'Bold',GREEN)
    txt(x+210,y+33,'반대편 줄에서 핀 6과 12를 찾습니다',10.7,'Bold',GRAY)


def split_pages(x,y,w,h):
    x_positions=[x+8,x+143]
    for idx,left in enumerate(x_positions):
        rect(left,y+3,104,99,WHITE,LINE,7)
        txt(left+9,y+13,('42쪽 하단','43쪽 상단')[idx],11,'ExtraBold',GREEN)
        for j in range(4):
            yy=y+40+j*12
            line(left+12,yy,left+90-(j%2)*12,yy,LINE,1.6)
        rect(left+8,y+(65 if not idx else 34),88,24,MINT,radius=4)
        txt(left+52,y+(70 if not idx else 39),('17번 지문','17번 보기')[idx],10,'Bold',GREEN,'center')
    arrow(x+115,y+55,x+140,y+55)
    arrow(x+250,y+55,x+278,y+55)
    tile(x+283,y+23,193,65,'17번 한 문항','42쪽 지문 + 43쪽 보기\n두 장을 순서대로 보냄',BLUE,SKY)


def pulse_chart(x,y,w,h):
    data=[
        ('시작',0,(150,110,150),GRAY),
        ('1',1060,(180,),GREEN),
        ('7',1890,(400,240,180,240,180),GREEN),
        ('답 ③',4330,(180,240,180,240,180),BLUE),
    ]
    left=x+11
    scale=(w-22)/5350
    txt(left,y+2,'17번의 답 ③',14,'ExtraBold',GREEN)
    line(left,y+75,left+5350*scale,y+75,LINE,1.3)
    for label,start,segments,color in data:
        txt(left+(start+sum(segments)/2)*scale,y+37,label,10.6,'Bold',color,'center')
        time=start
        for i,interval in enumerate(segments):
            if i%2==0:
                rect(left+time*scale,y+59,interval*scale,30,color,radius=3)
            time+=interval
    for label,start in [('0.65초',735),('0.65초',1565),('1.2초',3730)]:
        txt(left+start*scale,y+96,label,9.6,'Bold',GRAY,'center')


def outfit(x,y,w,h):
    # A technical outline with a transparent garment panel and separate attachment points.
    for i,name in enumerate(('겉에서 본 모습','옷의 안쪽 단면')):
        left=x+12+i*247
        txt(left+124,y+4,name,11.8,'ExtraBold',GREEN,'center')
        circle(left+91,y+54,21,'#B5CEC3')
        poly([(left+24,y+97),(left+61,y+77),(left+91,y+87),(left+123,y+77),
              (left+161,y+98),(left+149,y+139),(left+133,y+127),(left+134,y+209),
              (left+49,y+209),(left+50,y+127),(left+33,y+139)],'#283A36')
        line(left+91,y+87,left+91,y+207,'#5D7D70',1.4)
        circle(left+90,y+111,5,'#B0D4C3')
        circle(left+90,y+111,3,DARK)
        if not i:
            arrow(left+177,y+105,left+99,y+110,BLUE)
            txt(left+181,y+96,'렌즈',10,'Bold',BLUE)
        else:
            c.saveState()
            c.setFillAlpha(.82)
            rect(left+53,y+120,76,82,'#D2E8DA',radius=6)
            c.restoreState()
            line(left+90,y+116,left+90,y+145,AMBER,2.6)
            line(left+90,y+161,left+113,y+183,BLUE,2.6)
            line(left+81,y+152,left+64,y+174,PURPLE,2.6)
            rect(left+76,y+143,31,20,GREEN,radius=4)
            rect(left+99,y+179,30,18,BLUE,radius=4)
            rect(left+57,y+168,15,16,PURPLE,radius=3)
            for yy,word,point,color in [(138,'보드',(106,152),GREEN),
                                       (168,'진동',(70,177),PURPLE),
                                       (193,'배터리',(128,188),BLUE)]:
                arrow(left+165,y+yy,left+point[0],y+point[1],color)
                txt(left+168,y+yy-8,word,10.6,'Bold',color)
