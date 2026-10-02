# Flask 后端（旅游小程序）

## 1. 运行方式

```bash
cd backend-flask
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

默认监听：`http://127.0.0.1:5000`

## 2. 演示账号（账号密码）

- 用户：`user01 / 123456`
- 商家：`merchant01 / 123456`
- 管理员：`admin01 / 123456`

通过 `POST /api/auth/login` 传入 `username + password` 获取 token。

## 3. 已实现能力

- P0：登录、商品列表/详情、创建订单、订单列表/详情、取消订单、模拟支付、支付查询、订单状态更新
- 商家：商品管理（列表/新增/修改/日历维护）、看板统计
- 管理员：数据面板、用户增删改查、商家审核、商品管理、订单数据查询、类目配置、Banner 配置
- P1：退款申请/审核、评价与回复
- 系统：统一鉴权、状态机校验、支付幂等、库存原子扣减、操作日志

## 4. 接口自动化测试

```bash
cd backend-flask/tests
node api-test.mjs
```

测试说明：`backend-flask/tests/README.md`  
最新报告：`backend-flask/tests/latest-test-report.md`

## 2026-02 Incremental Update

- New endpoint: `POST /api/orders/<order_no>/confirm` (user/admin) for `to_travel -> completed`.
- New endpoint: `POST /api/upload/image` (merchant/admin) for product cover upload.
- Public uploaded files are served at `/uploads/<filename>`.
- API tests updated to cover user confirm and image upload paths.
