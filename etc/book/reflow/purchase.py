from layout import CW

DK='https://www.digikey.kr/en/products/detail/'
DM='https://www.devicemart.co.kr/goods/view?no='
DK_SHIPPING='https://www.digikey.kr/ko/help-support/delivery-information/delivery-time-and-cost'
CUSTOMS='https://www.customs.go.kr/kcs/ad/tax/BuyTaxCalculation.do'
ANKER='https://www.anker.com/products/a1653-usb-c-portable-charger-5000mah'
CAM_DOC='https://www.raspberrypi.com/documentation/accessories/camera-software.html'
CAM_HW='https://www.raspberrypi.com/documentation/accessories/camera.html'
MOTOR_DOC='https://wiki.seeedstudio.com/Grove-Vibration_Motor/'
GROVE_DOC='https://wiki.seeedstudio.com/Grove_System/'
MOTOR=DK+'seeed-technology-co-ltd/105020003/5482591'
MOTOR_LEAD='https://www.digikey.kr/ko/products/detail/seeed-technology-co-ltd/110990028/5482559'
CAMERA_15=DK+'adafruit-industries-llc/1648/7035020'
CASE_Z='https://icfactory.co.kr/product/detail.html?product_no=1709'
FIX='https://www.falconshop.co.kr/shop/goods/goods_view.php?category=033005005&goodsno=100094148'
PI3_KR='https://www.eku.co.kr/product/detail.html?product_no=209'
ZERO_KR=DM+'15548740'
ZERO_KIT='https://www.seeedstudio.com/Raspberry-Pi-Zero-2-W-with-Header-Basic-Kit-p-6351.html'
BATT_KR='https://shop.kt.com/accessory/accsProductView.do?prodNo=AC00076141'
BATT_AB='https://web.croket.co.kr/seller/product/655b1c93b4d4217da9285fcd'
STAR_KR='https://kr.element14.com/startech/usb2cub50cm/usb-cable-type-c-plug-micro-b/dp/4291865'
STAR_AB=DK+'startech-com/USB2CUB50CM/22160410'
RIB_30=DK+'raspberry-pi/SC1129/21658260'
SD_AB='https://www.bhphotovideo.com/c/product/1638656-REG/sandisk_sdsqunr_032_gn3ma_32gb_ultra_uhs_i_microsd.html'
READER='https://www.bhphotovideo.com/c/product/1128200-REG/transcend_ts_rdf5w_usb_3_0_card_reader.html'

# name, price source, displayed status, one unit in won, quantity
motor=('Grove Vibration Motor 105020003',MOTOR,'DigiKey 재고 표시',3066,1)
lead=('Grove → 암 점퍼 110990028',MOTOR_LEAD,'DigiKey, 20cm 5개 묶음',4878,1)
camera=('Camera Module 3 Wide SC1224',DK+'raspberry-pi/SC1224/17278644','DigiKey 재고 표시',51433,1)
local = [
    ('Pi 4 Model B 3GB',DM+'16063616','디바이스마트 주문 버튼',151800,1),
    camera,
    motor,
    ('Anker A1653 5,000mAh',BATT_KR,'KT샵 주문 버튼',43900,1),
    ('삼성 microSD 64GB','https://www.samsungsvc.co.kr/shop/product/0000044823','삼성전자서비스 표시가',12000,1),
    ('USB-C ↔ USB-C',ANKER,'A1653 동봉 케이블',0,1),
    ('15↔15핀 리본 30cm 1648',CAMERA_15,'DigiKey, 길이 여유용',2866,1),
    lead,
    ('케이스 및 고정재',FIX,'묶음 예산',12000,1),
]
desk = [
    ('Pi 3 B+  SC0073',DK+'raspberry-pi/SC0073/8571724','DigiKey 재고 표시',55744,1),
    camera,
    motor,
    ('공식 전원 SC0624',DK+'raspberry-pi/SC0624/15298145','DigiKey 재고 표시',11149,1),
    lead,
    ('Pi 3 케이스 SC0062',DK+'raspberry-pi/SC0062/6674283','DigiKey 재고 표시',7202,1),
    ('microSD와 리더',SD_AB,'기존 물품 사용',0,1),
]
wear = [
    ('Zero 2 WH  SC0721',DK+'raspberry-pi/SC0721/24627135','DigiKey 재고 0, 견적용',25085,1),
    desk[1],
    desk[2],
    desk[4],
    ('Anker A1653 5,000mAh',BATT_AB,'크로켓 해외배송 표시',49800,1),
    ('30cm 리본 SC1129',RIB_30,'DigiKey 재고 표시',2787,1),
    ('USB2CUB50CM 전원선',STAR_AB,'DigiKey, StarTech 50cm',19371,1),
    ('절연 받침 및 고정재',DK+'adafruit-industries-llc/3252/6573322','3252 바닥 예시, 27쪽',12000,1),
    ('microSD와 리더',SD_AB,'기존 물품 사용',0,1),
]


def price_rows(page, entries, label, size=10.6, delivery=()):
    rows=[((name,url),status,f'{unit:,}',str(count),f'{unit*count:,}')
          for name,url,status,unit,count in entries]
    subtotal=sum(unit*count for _,_,_,unit,count in entries)
    rows.append((f'합계 {label}','상품가','', '',f'{subtotal:,}'))
    if delivery:
        for seller,amount in delivery:
            rows.append((seller,'배송비','','',f'{amount:,}'))
        total=subtotal+sum(amount for _,amount in delivery)
        rows.append(('합계 상품 + 배송','세금 등 제외','','',f'{total:,}'))
    page.table(('부품 / 구매 링크','판매처 / 상태','단가(원)','수량','금액(원)'),
               (175,125,69,43,CW-412),rows,size=size,price=True)
    return subtotal


assert sum(row[-2] for row in local)==281943
assert sum(row[-2] for row in desk)==133472
assert sum(row[-2] for row in wear)==168420
