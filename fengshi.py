# -*- coding: utf-8 -*-
import requests
from datetime import datetime, timedelta
import json
import time
from typing import List
import hashlib
import schedule

COOKIE = {
    'fsUss':'',
    'sensorsdata2015jssdkcross':'',
    'sa_jssdk_2015_fs_sf-express_com':'',
    'sajssdk_2015_new_user_fs_sf-express_com':'1'
}
# E区二层餐区
addressId = <your addressId>
businessDistrictId = <your businessDistrictId>
companyId = <your companyId>
commonHeaders = {
    "Cookie": "; ".join([str(x)+"="+str(y) for x,y in COOKIE.items()]),
    "Accept": "application/json",
    "Refer": "https://servicewechat.com/wx1b8683fbb22af097/344/page-frame.html",
    "Accept-Encoding": "gzip,compress,br,deflate",
    "Content-Type": "application/json;charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.20(0x18001432) NetType/WIFI Language/zh_CN"
}


class Shop:
    shop_id: int
    sub_shop_id: int
    settled_shop_id: int
    settled_shop_type: int
    settled_shop_name: str
    shop_logo: str
    menu_id: int
    address: str


class Food:
    skuBaseId: int
    name: str
    subtitle: str
    image: List[dict]
    stock: int
    sales: int


class DishTime:
    type: int
    name: str
    time: str
    deliveryStartTime: str
    orderTime: str
    available: bool


class Welfare:
    welfareName: str
    welfareId: int
    welfareEmployeeId: int


class OrderDetail:
    receiverAddress: str
    takeMealCode: str
    subShopName: str
    skuList: List[dict]


def fetchDishTimes() -> List[DishTime]:
    dishTimes = []
    for i in range(0,7): # 一周内的菜品
        date = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
        resp = requests.post("http://fs.sf-express.com/fsweb/fs/shopping/merchant/getCalendarsAndDishTimes", headers=commonHeaders, json={
            'lat': '40.010313',
            'lng': '116.352818',
            'businessDistrictId': businessDistrictId,
            'date': date,
            "showTab": 0,
            "workOvertimeMeal": 0,
            "orderChannel": 9,
            "addrId": addressId,
        })
        body = resp.json()

        if body['errno']:
            raise ValueError(f"{body['errno']}-{body['errmsg']}")

        ds = body['data']["dishTimes"]
        ds = [d for d in ds if d['available']]
        for d in ds:
            d['date'] = date
        dishTimes += ds
    return dishTimes

# 查询餐厅列表
# mealType 2: 午餐 4: 晚餐
def fetchShops(mealType: int, type: int, date: str) -> List[Shop]:
    resp = requests.post("http://fs.sf-express.com/fsweb/fs/shopping/merchant/tuancanshoplistV2", headers=commonHeaders, json={
        "page": 1,
        "pageSize": 20,
        "shopListSource": 2,
        "lat": "40.010313",
        "lng": "116.352818",
        "date": date,
        "type": type,
        "mealType": mealType,
        "showTab": 0,
    })
    body = resp.json()
    if body['errno']:
        raise ValueError(f"{body['errno']}-{body['errmsg']}")
    shops = body['data']['list']
    shops = list(filter(lambda x: x["limitStatus"]==0, shops))
    return shops


def fetchMenu(shops: List[Shop], dishTime: DishTime) -> List[Food]:
    menus = []
    for shop in shops:
        resp = requests.post(
            "http://fs.sf-express.com/fsweb/fs/shopping/merchant/querySkuByMenuId",
            headers=commonHeaders,
            json={
                "menuId": shop["menuId"],
                "type": 1,
                "shopId": shop["shopId"],
                "subShopId": shop["subShopId"],
                "requireStatus": 0,
                "mealType": dishTime["mealType"],
                "mealTimeId": dishTime["type"],
                "date": dishTime["date"],
            }
        )
        body = resp.json()

        if not body.get("errno"):
            menus1 = body['data']['list']
            for menu in menus1:
                menu['shop'] = shop # 保存餐厅信息，下单的时候用
            menus += menus1
        time.sleep(0.5) # 等待1秒，防止下单太快被封
    #   过滤不可选菜品
    menus = list(filter(lambda x: x["stock"]>0, menus))
    return menus

# 清空购物车
def dropTrolley():
    resp = requests.post(
        "http://fs.sf-express.com/fsweb/fs/multitrolley/drop",
        headers=commonHeaders,
        json={
            "businessDistrictId": businessDistrictId,
            "isFx": 0,
            "dropType": 0
        }
    )
    body = resp.json()
    if body.get("errno"):
        raise Exception(f"{body.get('errno')}-{body.get('errmsg')}")


def addTrolley(dishTime, shop, food) -> List[str]:
    resp = requests.post(
        "http://fs.sf-express.com/fsweb/fs/multitrolley/add",
        headers=commonHeaders,
        json={
            "shopId": shop["shopId"],
            "subShopId": shop["subShopId"],
            "mealTimeId": dishTime["type"],
            "date": dishTime["date"],
            "businessDistrictId": businessDistrictId,
            "sku": {
                "skuBaseId": food["skuBaseId"],
                "trolleyKey": "29a25d4676b42e9d2dc23debc2be62c6",
                "skuCount": 1,
            },
        }
    )
    body = resp.json()

    if body.get("errno"):
        raise Exception(f"{body.get('errno')}-{body.get('errmsg')}")

    return [food["name"] for food in body.get("data", {}).get("trolleyList", [])]


def preOrder(shopId: int, subShopId: int, menuId: int):
    url = "https://fs.sf-express.com/fsweb/app/merchant/checkTrolleySkuNum"
    data = {
        "shopId": str(shopId),
        "subShopId": str(subShopId),
        "mealType": 4,
        "menuId": menuId,
        "menu_id": menuId,
        "businessDistrictId": businessDistrictId,
        "businessType": 1,
    }
    resp = requests.post(url, headers=commonHeaders, data=json.dumps(data))
    body = resp.json()
    if body["errno"]:
        raise Exception(f"{body['errno']}-{body['errmsg']}")


def getOrderWelfares():
    url = "http://fs.sf-express.com/fsweb/fs/shopping/trade/calculatemultiorderprice"
    data = {
        "choice_logistics": 1,
        "is_tuancan": 1,
        "useChannel": 2,
        "isFx": 0,
        "source": 9,
        "orderFlag": 1,
        "workOvertimeMeal": 0,
        "businessDistrictId": businessDistrictId,
        "companyId": companyId,
        "wantong_status": -1,
        "award_status": -1,
        "benefit_status": -1,
        "canka_status": -1,
        "companyBalanceStatus": -1,
        "customerGroupStatus": -1,
        "isConfirmDetailAddress": 0,
        "choice_addr_id": addressId,
        "calculatePriceList": [],
    }
    resp = requests.post(url, headers=commonHeaders, data=json.dumps(data))
    body = resp.json()
    if body["errno"]:
        raise Exception(f"{body['errno']}-{body['errmsg']}")
    calcSubOrderList = body["data"]["calcSubOrderList"]
    if calcSubOrderList:
        return calcSubOrderList[0]["welfareList"]
    return []


# 下单
def create_order(
        shop_id: int,
        sub_shop_id: int,
        welfare_id: int,
        welfare_employee_id: int,
        dish_type: int,
        date: str,
        start_time: str,
        end_time: str
) -> int:
    url = "http://fs.sf-express.com/fsweb/fs/shopping/trade/multiOrderCreate"
    data = {
        "addrId": addressId,
        "dispatchMethod": 1,
        "source": 9,
        "longitude": "116.352818",
        "latitude": "40.010313",
        "businessDistrictId": businessDistrictId,
        "workOvertimeMeal": 0,
        "fsPayTypes": [],
        "shopOrderList": [{
            "shopId": shop_id,
            "subShopId": sub_shop_id,
            "remark": "",
            "reduceList": [0],
            "platformCouponId": 0,
            "welfareId": welfare_id,
            "welfareEmployeeId": welfare_employee_id,
            "welfareBirthdayId": 0,
            "welfareCardChoose": [],
            "couponId": 0,
            "fsPayTypes": [],
            "isInvoice": 0,
            "diningNum": 1,
            "mealTimeId": dish_type,
            "deliveryTime": {
                "date": date,
                "from": start_time,
                "to": end_time
            }
        }],
    }
    resp = requests.post(url, headers=commonHeaders, json=data)
    body = resp.json()
    if body.get("errno"):
        raise Exception(f"{body['errno']}-{body['errmsg']}")
    return body.get("data")['orderId']


def pay_sign(data, n):
    if data is None or data == "":
        raise ValueError("Illegal argument " + data)

    data = data.encode('utf-8')
    hashed_data = hashlib.md5(data).digest()

    if n and n.get('asBytes'):
        return hashed_data
    elif n and n.get('asString'):
        return hashed_data.decode('utf-8')
    else:
        return hashed_data.hex()


# 支付
def pay(order_id: int):
    url = "http://fs.sf-express.com/fsweb/fs/shopping/trade/wxpay"
    data = {
        "source": 9,
        "orderId": order_id,
        "order_id": order_id,
        "orderType": 0,
        "orderChannel": 9,
        "sign": pay_sign(f"source=9&order_id={order_id}&MIV4c3HZwREev", None),
    }
    commonHeaders["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
    print(commonHeaders)
    resp = requests.post(url, headers=commonHeaders, data=data)
    commonHeaders["Content-Type"] = "application/json;charset=UTF-8"
    body = resp.json()
    if body.get("errno"):
        raise Exception(f"{body['errno']}-{body['errmsg']}")


# 取当天的用餐时间表 午餐、晚餐分别订餐 -> 这里后续可以改成所有可用的日期
# 取某天的午餐或者晚餐对应的所有商家，并遍历取出商家所有可用的菜单，组合在一起
# 根据提供的关键字过滤菜单，取出对应的菜品，之后加购物车并下单
def orderDish(foodNames: List[str]) -> dict:
    # 取用餐时间表 午餐、晚餐
    dishTimes = fetchDishTimes()
    for dishTime in dishTimes:
        print(f"{datetime.now().strftime('%Y-%m-%d, %H:%M:%S')} 开始订餐！{dishTime['date']}-{dishTime['name']}")
        # 取商家列表
        shops = fetchShops(dishTime["mealType"], dishTime["type"], dishTime["date"])
        print(f"可用的商家列表：{shops}")
        # 获取菜品列表
        menus = fetchMenu(shops, dishTime)

    #     根据菜名关键字过滤偏好的菜品
        like_menu = next(filter(lambda x: any([f in x["name"] for f in foodNames]), menus), None)
        food = like_menu if like_menu else next((m for m in menus), None)
        print(f"选择的菜品：{food}")
        if not food:
            # 没有找到菜品，继续下一个循环
            continue
        shop = food["shop"] # 菜品对应的商家
        # 清空购物车
        dropTrolley()
        # 加购物车
        itemNames = addTrolley(dishTime, shop, food)

        # preOrder(shop["shopId"], shop["subShopId"], shop["menuId"])

        welfares = getOrderWelfares()
        welfare = next(filter(lambda x: x["welfareName"] == dishTime['name'] and x['isAvailable'], welfares), None)
        if not welfare:
            print(f"没有可用的福利券：{dishTime['date']}-{dishTime['name']}")
            continue
        time.sleep(1) # 等待1秒，防止下单太快被封
        orderId = create_order(
            shop["shopId"],
            shop["subShopId"],
            welfare["welfareId"],
            welfare["welfareEmployeeId"],
            dishTime["type"],
            dishTime["date"],
            dishTime["deliveryStartTime"],
            dishTime["time"]
        )
        time.sleep(1) # 等待1秒，防止下单太快被封
        if not orderId:
            raise Exception("下单失败！")

        print(f"下单成功！{dishTime['date']}-{dishTime['name']}-{orderId}")

        pay(orderId)
        print(f"支付成功，预定完成！{dishTime['date']}-{dishTime['name']}")
        time.sleep(1) # 等待1秒，防止下单太快被封


# 1. 获取用餐时间
# 2. 获取商店列表

# 3. 获取商店菜单
# 4. 获取商店用餐时间
# 过滤偏好餐品，添加到购物车，结账
def main():
    try:
        orderDish(["酥皮牛肉饼", "芥菜薄皮包子", "犟", "鸡腿堡", "鸡腿"])
    except Exception as e:
        print(e)


main()  # 执行一次
schedule.every(45).minutes.do(main)
while True:
    schedule.run_pending()
    time.sleep(1)
