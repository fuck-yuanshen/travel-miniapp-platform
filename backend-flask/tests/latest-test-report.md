# 接口测试报告（最新）

- 测试入口：`backend-flask/tests/api-test.mjs`
- 测试日志：`backend-flask/tests/latest-test.log`
- 测试基地址：`http://127.0.0.1:5000/api`
- 结果汇总：`46 通过 / 0 失败`

## 1. 登录与公共接口

| 接口 | 期望 | 实际 |
|---|---|---|
| `GET /api/health` | `HTTP 200` + `code=0` | 通过 |
| `POST /api/auth/login`（user/merchant/admin） | `HTTP 200` + `token` | 通过 |
| `POST /api/auth/login`（错误密码） | `HTTP 401` + `code=40111` | 通过 |
| `GET /api/banners` | `HTTP 200` + 列表 | 通过 |
| `GET /api/categories` | `HTTP 200` + 列表 | 通过 |
| `GET /api/products` | `HTTP 200` + 列表非空 | 通过 |
| `GET /api/products/:id` | `HTTP 200` + `skuCalendar` 非空 | 通过 |

## 2. 用户交易主链路

| 接口 | 期望 | 实际 |
|---|---|---|
| `POST /api/orders` | 新建订单状态 `pending_payment` | 通过 |
| `GET /api/orders`（用户） | 可查到刚创建订单 | 通过 |
| `GET /api/orders/:orderNo` | 订单详情完整 | 通过 |
| `GET /api/pay/query`（支付前） | `payInfo` 可为空 | 通过 |
| `POST /api/pay/mock-success` | 状态更新为 `to_travel` | 通过 |
| `POST /api/pay/mock-success`（幂等） | 不重复写入支付 | 通过 |
| `GET /api/pay/query`（支付后） | `payInfo` 非空 | 通过 |
| `POST /api/orders/:orderNo/status`（商家） | 合法流转至 `completed` | 通过 |
| `POST /api/orders/:orderNo/cancel` | 待支付订单可取消并回滚库存 | 通过 |

## 3. 退款与评价

| 接口 | 期望 | 实际 |
|---|---|---|
| `POST /api/reviews` | 已完成订单可评价 | 通过 |
| `POST /api/reviews/:id/reply`（不存在） | `HTTP 404` + `code=40431` | 通过 |
| `POST /api/refunds/apply` | 生成 `refundNo` | 通过 |
| `POST /api/refunds/:refundNo/audit` | 商家可审核通过 | 通过 |

## 4. 商家接口

| 接口 | 期望 | 实际 |
|---|---|---|
| `GET /api/merchant/dashboard` | 返回订单与 GMV 统计 | 通过 |
| `GET /api/merchant/products` | 返回商家商品列表 | 通过 |
| `POST /api/merchant/products` | 新增商品成功 | 通过 |
| `PUT /api/merchant/products/:id` | 更新价格/状态成功 | 通过 |
| `POST /api/merchant/products/:id/calendar` | 日历库存更新成功 | 通过 |

## 5. 管理员接口（用户与数据库 CRUD）

| 接口 | 期望 | 实际 |
|---|---|---|
| `GET /api/admin/dashboard` | 返回全站统计面板 | 通过 |
| `GET /api/admin/users` | 返回用户列表（分页） | 通过 |
| `POST /api/admin/users` | 可新增用户 | 通过 |
| `PUT /api/admin/users/:id` | 可修改用户信息 | 通过 |
| `DELETE /api/admin/users/:id` | 可禁用用户 | 通过 |
| `GET /api/admin/orders` | 返回订单数据列表 | 通过 |
| `GET /api/admin/products` | 返回商品数据列表 | 通过 |
| `PUT /api/admin/products/:id` | 可修改商品信息 | 通过 |
| `DELETE /api/admin/products/:id` | 可停用商品 | 通过 |
| `GET /api/admin/categories` | 返回类目列表 | 通过 |
| `POST /api/admin/categories` | 类目新增/更新成功 | 通过 |
| `DELETE /api/admin/categories/:id` | 可删除无商品关联类目 | 通过 |
| `GET /api/admin/banners` | 返回 banner 列表 | 通过 |
| `POST /api/admin/banners` | banner 配置保存成功 | 通过 |
| `GET /api/admin/merchants` | 返回商家列表 | 通过 |
| `POST /api/admin/merchants/:id/audit` | 可审核商家状态 | 通过 |
