# fengshi
顺丰 丰食自动点餐

使用步骤：
1. git clone <url>
2. 安装依赖 pip install -r requirements.txt
3. fengshi.py 中的cookie、addressId、businessDistrictId、companyId需要替换成自己的。可以使用抓包工具，在pc端丰食走一遍订餐流程，抓到这些参数。
3. 运行 python fengshi.py，首先执行一次，之后每隔45分钟执行一次，直到订餐成功。




fengshi.py 主体代码
<br />
入口函数 main
<br />
主体函数 orderDish
<br />
参数：foodNames: List[str] 喜欢的餐品名称列表
<br />
主要逻辑：
<br />
1. 获取用餐时间列表
2. 对每个用餐时间，获取商店列表，和商店下的菜品列表
3. 根据喜欢的餐品名称过滤菜品列表，取出第一个匹配的餐品
4. 添加购物车，校验福利券，结账

