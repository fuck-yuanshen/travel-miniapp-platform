# 旅游小程序（uni-app + Flask）

## 项目结构

- `旅游小程序/`：uni-app 前端工程（用户端 + 商家/管理员入口页面）
- `backend-flask/`：Flask 后端服务（SQLite）

## 前端说明

前端默认请求地址在 `旅游小程序/common/config.js`：

```js
const BASE_URL = "http://127.0.0.1:5000/api";
```

如果使用真机调试，请改成你电脑的局域网 IP。

## 后端启动

```bash
cd backend-flask
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

启动后可访问：`GET /api/health`

## 已实现功能（按功能文档）

- 用户端 P0：登录、Banner、分类、商品列表/详情、创建订单、模拟支付、订单列表/详情、取消订单
- 商家端：商品列表/新增/修改/库存日历、订单状态更新、销售看板
- 管理员端：数据面板、用户增删改查、商家审核、商品管理、订单数据查看、类目管理、Banner 配置
- 系统能力：统一鉴权、订单状态机、幂等（支付）、库存原子扣减、操作日志
- P1 扩展：退款申请/审核、评价创建/回复

## 本地演示账号

请通过数据库初始化脚本在本地创建测试账号。仓库不保存固定密码；登录后系统按账号角色进入用户端、商家端或管理员端。

## 接口测试

后端启动后执行：

```bash
cd backend-flask/tests
node api-test.mjs
```

最新测试报告见：`backend-flask/tests/latest-test-report.md`

## 2026-02 Incremental Update

- Added user order confirmation flow: after payment (`to_travel`), user can call `POST /api/orders/:orderNo/confirm` to finish the trip.
- Order list and profile order stats now fetch all pages, not only first page.
- Merchant publish page now supports image upload and category selection.
- Added upload API: `POST /api/upload/image` (merchant/admin), response returns permanent `url`.
