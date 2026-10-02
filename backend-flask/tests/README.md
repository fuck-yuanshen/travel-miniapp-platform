# 接口测试说明

## 1. 运行方式

先启动 Flask 服务，再执行：

```bash
cd backend-flask/tests
node api-test.mjs
```

可选环境变量：

```bash
API_BASE_URL=http://127.0.0.1:5000/api node api-test.mjs
```

## 2. 覆盖范围

脚本覆盖以下接口（含正向/异常用例）：

1. `GET /api/health`
2. `POST /api/auth/login`（user/merchant/admin/错误密码）
3. `GET /api/banners`
4. `GET /api/categories`
5. `GET /api/products`
6. `GET /api/products/:id`
7. `POST /api/orders`
8. `GET /api/orders`
9. `GET /api/orders/:orderNo`
10. `POST /api/orders/:orderNo/cancel`
11. `POST /api/pay/mock-success`
12. `GET /api/pay/query`
13. `POST /api/orders/:orderNo/status`
14. `POST /api/refunds/apply`
15. `POST /api/refunds/:refundNo/audit`
16. `POST /api/reviews`
17. `POST /api/reviews/:id/reply`（异常）
18. `GET /api/merchant/dashboard`
19. `GET /api/merchant/products`
20. `POST /api/merchant/products`
21. `PUT /api/merchant/products/:id`
22. `POST /api/merchant/products/:id/calendar`
23. `GET /api/admin/merchants`
24. `POST /api/admin/merchants/:id/audit`
25. `POST /api/admin/categories`
26. `POST /api/admin/banners`
27. `GET /api/admin/dashboard`
28. `GET /api/admin/users`
29. `POST /api/admin/users`
30. `PUT /api/admin/users/:id`
31. `DELETE /api/admin/users/:id`
32. `GET /api/admin/orders`
33. `GET /api/admin/products`
34. `PUT /api/admin/products/:id`
35. `DELETE /api/admin/products/:id`
36. `GET /api/admin/categories`
37. `DELETE /api/admin/categories/:id`
38. `GET /api/admin/banners`

## 3. 期望结果

- 成功请求统一返回：
  - `HTTP 200`
  - `{"code": 0, "message": "ok", "data": ...}`
- 鉴权失败：
  - `HTTP 401`，如 `code=40101/40102/40111`
- 参数错误：
  - `HTTP 400`，对应接口定义业务码
- 资源不存在：
  - `HTTP 404`，如 `code=40411/40431`

脚本会输出每个测试项的 `PASS/FAIL` 和最终通过率统计。

## 2026-02 Added Cases

- `POST /api/orders/:orderNo/confirm` (user confirms trip completion)
- `POST /api/upload/image` (merchant/admin image upload)
- `GET /api/merchant/reviews` (merchant review list)
- `POST /api/reviews/:id/reply` (merchant reply success)
- `DELETE /api/merchant/products/:id` (merchant delete product)
