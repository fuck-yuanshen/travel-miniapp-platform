/* eslint-disable no-console */
const baseUrl = process.env.API_BASE_URL || "http://127.0.0.1:5000/api";

function now() {
  return new Date().toISOString();
}

function randomSuffix() {
  return Math.random().toString(36).slice(2, 8);
}

async function request(path, options = {}) {
  const response = await fetch(`${baseUrl}${path}`, options);
  let body = null;
  try {
    body = await response.json();
  } catch (error) {
    body = { code: -1, message: "鍝嶅簲涓嶆槸 JSON", raw: await response.text() };
  }
  return { status: response.status, body };
}

async function requestWithToken(path, token, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
    ...(options.headers || {}),
  };
  return request(path, { ...options, headers });
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function runCase(name, runner) {
  const start = Date.now();
  try {
    const result = await runner();
    const elapsed = Date.now() - start;
    console.log(`[PASS] ${name} (${elapsed}ms)`);
    return { name, pass: true, elapsed, detail: result || null };
  } catch (error) {
    const elapsed = Date.now() - start;
    console.error(`[FAIL] ${name} (${elapsed}ms) -> ${error.message}`);
    return { name, pass: false, elapsed, detail: { error: error.message } };
  }
}

async function main() {
  const report = {
    startedAt: now(),
    baseUrl,
    cases: [],
  };
  const ctx = {
    tokens: {},
    ids: {},
  };

  report.cases.push(
    await runCase("health", async () => {
      const res = await request("/health");
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      return res.body.data;
    }),
  );

  report.cases.push(
    await runCase("auth.login(user)", async () => {
      const res = await request("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: "user01",
          password: "123456",
          role: "user",
        }),
      });
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      ctx.tokens.user = res.body.data.token;
      return { role: res.body.data.user.role, username: res.body.data.user.username };
    }),
  );

  report.cases.push(
    await runCase("auth.login(merchant)", async () => {
      const res = await request("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: "merchant01",
          password: "123456",
          role: "merchant",
        }),
      });
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      ctx.tokens.merchant = res.body.data.token;
      return { role: res.body.data.user.role, username: res.body.data.user.username };
    }),
  );

  report.cases.push(
    await runCase("auth.login(admin)", async () => {
      const res = await request("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: "admin01",
          password: "123456",
          role: "admin",
        }),
      });
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      ctx.tokens.admin = res.body.data.token;
      return { role: res.body.data.user.role, username: res.body.data.user.username };
    }),
  );

  report.cases.push(
    await runCase("auth.login(wrong_password)", async () => {
      const res = await request("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: "user01",
          password: "bad-password",
        }),
      });
      assert(res.status === 401, `HTTP 鐘舵€佸簲涓?401锛屽疄闄?${res.status}`);
      assert(res.body.code === 40111, `涓氬姟鐮佸簲涓?40111锛屽疄闄?${res.body.code}`);
      return { message: res.body.message };
    }),
  );

  report.cases.push(
    await runCase("banners", async () => {
      const res = await request("/banners");
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      return { count: (res.body.data || []).length };
    }),
  );

  report.cases.push(
    await runCase("categories", async () => {
      const res = await request("/categories");
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      return { count: (res.body.data || []).length };
    }),
  );

  report.cases.push(
    await runCase("products.list", async () => {
      const res = await request("/products?page=1&pageSize=10");
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      const items = res.body.data.items || [];
      assert(items.length > 0, "鍟嗗搧鍒楄〃搴旇嚦灏戞湁 1 鏉?");
      ctx.ids.productId = items[0].id;
      return { count: items.length, productId: ctx.ids.productId };
    }),
  );

  report.cases.push(
    await runCase("products.detail", async () => {
      const res = await request(`/products/${ctx.ids.productId}`);
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      const sku = res.body.data.skuCalendar || [];
      assert(sku.length > 0, "skuCalendar 搴旇嚦灏戞湁 1 鏉?");
      const available = sku.find((item) => item.stock > 0);
      assert(!!available, "搴旇嚦灏戞湁鍙笅鍗曞簱瀛?");
      ctx.ids.travelDate = available.date;
      return { travelDate: ctx.ids.travelDate, stock: available.stock };
    }),
  );

  report.cases.push(
    await runCase("order.create", async () => {
      const res = await requestWithToken("/orders", ctx.tokens.user, {
        method: "POST",
        body: JSON.stringify({
          productId: ctx.ids.productId,
          travelDate: ctx.ids.travelDate,
          qty: 1,
          contactName: "鎺ュ彛娴嬭瘯鐢ㄦ埛",
          contactPhone: "13800009999",
          remark: "api test",
          clientReqNo: `api-create-${Date.now()}-${randomSuffix()}`,
        }),
      });
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      ctx.ids.orderNo = res.body.data.order.orderNo;
      return { orderNo: ctx.ids.orderNo, status: res.body.data.order.status };
    }),
  );

  report.cases.push(
    await runCase("order.list(user)", async () => {
      const res = await requestWithToken("/orders?page=1&pageSize=20", ctx.tokens.user);
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      const found = (res.body.data.items || []).some((item) => item.orderNo === ctx.ids.orderNo);
      assert(found, "璁㈠崟鍒楄〃搴斿寘鍚柊寤鸿鍗?");
      return { total: res.body.data.pagination.total };
    }),
  );

  report.cases.push(
    await runCase("order.detail", async () => {
      const res = await requestWithToken(`/orders/${ctx.ids.orderNo}`, ctx.tokens.user);
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      assert(res.body.data.order.status === "pending_payment", "鏂拌鍗曞簲涓?pending_payment");
      return { status: res.body.data.order.status };
    }),
  );

  report.cases.push(
    await runCase("pay.query(before_pay)", async () => {
      const res = await requestWithToken(`/pay/query?orderNo=${ctx.ids.orderNo}`, ctx.tokens.user);
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      return { payInfo: res.body.data.payInfo };
    }),
  );

  report.cases.push(
    await runCase("pay.mockSuccess", async () => {
      const idemKey = `idem-${Date.now()}-${randomSuffix()}`;
      const res = await requestWithToken("/pay/mock-success", ctx.tokens.user, {
        method: "POST",
        headers: { "Idempotency-Key": idemKey },
        body: JSON.stringify({
          orderNo: ctx.ids.orderNo,
          idemKey,
        }),
      });
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      assert(res.body.data.status === "to_travel", "鏀粯鍚庤鍗曞簲鍙樹负 to_travel");
      ctx.ids.idemKey = idemKey;
      return { status: res.body.data.status };
    }),
  );

  report.cases.push(
    await runCase("pay.mockSuccess(idempotent)", async () => {
      const res = await requestWithToken("/pay/mock-success", ctx.tokens.user, {
        method: "POST",
        headers: { "Idempotency-Key": ctx.ids.idemKey },
        body: JSON.stringify({
          orderNo: ctx.ids.orderNo,
          idemKey: ctx.ids.idemKey,
        }),
      });
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      return { status: res.body.data.status, idempotent: res.body.data.idempotent };
    }),
  );

  report.cases.push(
    await runCase("pay.query(after_pay)", async () => {
      const res = await requestWithToken(`/pay/query?orderNo=${ctx.ids.orderNo}`, ctx.tokens.user);
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      assert(!!res.body.data.payInfo, "宸叉敮浠樿鍗曞簲瀛樺湪 payInfo");
      return { payMethod: res.body.data.payInfo.pay_method };
    }),
  );
  report.cases.push(
    await runCase("order.confirm(user)", async () => {
      const res = await requestWithToken(`/orders/${ctx.ids.orderNo}/confirm`, ctx.tokens.user, {
        method: "POST",
      });
      assert(res.status === 200, `HTTP status should be 200, got ${res.status}`);
      assert(res.body.code === 0, `code should be 0, got ${res.body.code}`);
      assert(res.body.data.order.status === "completed", "order should become completed");
      return { status: res.body.data.order.status };
    }),
  );

  report.cases.push(
    await runCase("order.list(merchant)", async () => {
      const res = await requestWithToken("/orders?page=1&pageSize=20", ctx.tokens.merchant);
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      return { total: res.body.data.pagination.total };
    }),
  );

  report.cases.push(
    await runCase("order.updateStatus(merchant to completed)", async () => {
      const createRes = await requestWithToken("/orders", ctx.tokens.user, {
        method: "POST",
        body: JSON.stringify({
          productId: ctx.ids.productId,
          travelDate: ctx.ids.travelDate,
          qty: 1,
          contactName: "merchant status case",
          contactPhone: "13800006666",
          clientReqNo: `api-merchant-status-${Date.now()}-${randomSuffix()}`,
        }),
      });
      assert(createRes.status === 200 && createRes.body.code === 0, "create order for merchant status failed");
      const merchantOrderNo = createRes.body.data.order.orderNo;

      const payRes = await requestWithToken("/pay/mock-success", ctx.tokens.user, {
        method: "POST",
        body: JSON.stringify({
          orderNo: merchantOrderNo,
          idemKey: `merchant-pay-${Date.now()}-${randomSuffix()}`,
        }),
      });
      assert(payRes.status === 200 && payRes.body.code === 0, "pay order for merchant status failed");

      const res = await requestWithToken(`/orders/${merchantOrderNo}/status`, ctx.tokens.merchant, {
        method: "POST",
        body: JSON.stringify({
          targetStatus: "completed",
          reason: "merchant status test",
        }),
      });
      assert(res.status === 200, `HTTP status should be 200, got ${res.status}`);
      assert(res.body.code === 0, `code should be 0, got ${res.body.code}`);
      assert(res.body.data.order.status === "completed", "order should become completed");
      return { status: res.body.data.order.status };
    }),
  );
  report.cases.push(
    await runCase("review.create", async () => {
      const res = await requestWithToken("/reviews", ctx.tokens.user, {
        method: "POST",
        body: JSON.stringify({
          orderNo: ctx.ids.orderNo,
          score: 5,
          content: "鑷姩鍖栨祴璇曡瘎浠?",
          images: [],
        }),
      });
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      ctx.ids.reviewId = res.body.data.reviewId;
      return { score: res.body.data.score };
    }),
  );

  report.cases.push(
    await runCase("review.reply(non_existent)", async () => {
      const res = await requestWithToken("/reviews/999999/reply", ctx.tokens.merchant, {
        method: "POST",
        body: JSON.stringify({
          reply: "娴嬭瘯鍥炲",
        }),
      });
      assert(res.status === 404, `HTTP 鐘舵€佸簲涓?404锛屽疄闄?${res.status}`);
      assert(res.body.code === 40431, `涓氬姟鐮佸簲涓?40431锛屽疄闄?${res.body.code}`);
      return { message: res.body.message };
    }),
  );

  report.cases.push(
    await runCase("review.reply(success)", async () => {
      const res = await requestWithToken(`/reviews/${ctx.ids.reviewId}/reply`, ctx.tokens.merchant, {
        method: "POST",
        body: JSON.stringify({
          reply: "已收到反馈，感谢评价",
        }),
      });
      assert(res.status === 200, `HTTP status should be 200, got ${res.status}`);
      assert(res.body.code === 0, `code should be 0, got ${res.body.code}`);
      return { reviewId: res.body.data.reviewId };
    }),
  );

  report.cases.push(
    await runCase("order.create(for_cancel)", async () => {
      const res = await requestWithToken("/orders", ctx.tokens.user, {
        method: "POST",
        body: JSON.stringify({
          productId: ctx.ids.productId,
          travelDate: ctx.ids.travelDate,
          qty: 1,
          contactName: "鍙栨秷娴嬭瘯鐢ㄦ埛",
          contactPhone: "13800008888",
          clientReqNo: `api-cancel-${Date.now()}-${randomSuffix()}`,
        }),
      });
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      ctx.ids.cancelOrderNo = res.body.data.order.orderNo;
      return { orderNo: ctx.ids.cancelOrderNo };
    }),
  );

  report.cases.push(
    await runCase("order.cancel", async () => {
      const res = await requestWithToken(`/orders/${ctx.ids.cancelOrderNo}/cancel`, ctx.tokens.user, {
        method: "POST",
        body: JSON.stringify({ reason: "鎺ュ彛娴嬭瘯鍙栨秷璁㈠崟" }),
      });
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      assert(res.body.data.order.status === "cancelled", "璁㈠崟搴斿彉涓?cancelled");
      return { status: res.body.data.order.status };
    }),
  );

  report.cases.push(
    await runCase("order.create(for_refund)", async () => {
      const createRes = await requestWithToken("/orders", ctx.tokens.user, {
        method: "POST",
        body: JSON.stringify({
          productId: ctx.ids.productId,
          travelDate: ctx.ids.travelDate,
          qty: 1,
          contactName: "閫€娆炬祴璇曠敤鎴?",
          contactPhone: "13800007777",
          clientReqNo: `api-refund-${Date.now()}-${randomSuffix()}`,
        }),
      });
      assert(createRes.status === 200 && createRes.body.code === 0, "鍒涘缓閫€娆炬祴璇曡鍗曞け璐?");
      const orderNo = createRes.body.data.order.orderNo;
      const payRes = await requestWithToken("/pay/mock-success", ctx.tokens.user, {
        method: "POST",
        body: JSON.stringify({ orderNo, idemKey: `pay-${Date.now()}-${randomSuffix()}` }),
      });
      assert(payRes.status === 200 && payRes.body.code === 0, "閫€娆炬祴璇曡鍗曟敮浠樺け璐?");
      ctx.ids.refundOrderNo = orderNo;
      return { orderNo };
    }),
  );

  report.cases.push(
    await runCase("refund.apply", async () => {
      const res = await requestWithToken("/refunds/apply", ctx.tokens.user, {
        method: "POST",
        body: JSON.stringify({
          orderNo: ctx.ids.refundOrderNo,
          reason: "鎺ュ彛娴嬭瘯閫€娆?",
        }),
      });
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      ctx.ids.refundNo = res.body.data.refundNo;
      return { refundNo: ctx.ids.refundNo };
    }),
  );

  report.cases.push(
    await runCase("refund.audit(merchant approved)", async () => {
      const res = await requestWithToken(`/refunds/${ctx.ids.refundNo}/audit`, ctx.tokens.merchant, {
        method: "POST",
        body: JSON.stringify({
          approved: true,
          reason: "鎺ュ彛娴嬭瘯鍚屾剰閫€娆?",
        }),
      });
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      assert(res.body.data.result === "approved", "閫€娆惧鏍哥粨鏋滃簲涓?approved");
      return { result: res.body.data.result };
    }),
  );

  report.cases.push(
    await runCase("merchant.dashboard", async () => {
      const res = await requestWithToken("/merchant/dashboard", ctx.tokens.merchant);
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      return {
        totalOrders: res.body.data.totalOrders,
        gmv: res.body.data.gmv,
      };
    }),
  );

  report.cases.push(
    await runCase("merchant.reviews.list", async () => {
      const res = await requestWithToken("/merchant/reviews?page=1&pageSize=20", ctx.tokens.merchant);
      assert(res.status === 200, `HTTP status should be 200, got ${res.status}`);
      assert(res.body.code === 0, `code should be 0, got ${res.body.code}`);
      const hasReview = (res.body.data.items || []).some((item) => item.id === ctx.ids.reviewId);
      assert(hasReview, "merchant reviews should include created review");
      return { total: res.body.data.pagination.total };
    }),
  );

  report.cases.push(
    await runCase("merchant.products.list", async () => {
      const res = await requestWithToken("/merchant/products", ctx.tokens.merchant);
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      return { count: (res.body.data || []).length };
    }),
  );
  report.cases.push(
    await runCase("upload.image", async () => {
      const pngBase64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5jP2QAAAAASUVORK5CYII=";
      const bytes = Buffer.from(pngBase64, "base64");
      const form = new FormData();
      form.append("file", new Blob([bytes], { type: "image/png" }), "tiny.png");

      const response = await fetch(`${baseUrl}/upload/image`, {
        method: "POST",
        headers: { Authorization: `Bearer ${ctx.tokens.merchant}` },
        body: form,
      });
      const body = await response.json();
      assert(response.status === 200, `HTTP status should be 200, got ${response.status}`);
      assert(body.code === 0, `code should be 0, got ${body.code}`);
      assert(!!body.data.url, "upload url should not be empty");
      return { url: body.data.url };
    }),
  );

  report.cases.push(
    await runCase("merchant.products.create", async () => {
      const categoryRes = await request("/categories");
      assert(categoryRes.status === 200 && categoryRes.body.code === 0, "fetch categories failed");
      const firstCategory = (categoryRes.body.data || [])[0];

      const res = await requestWithToken("/merchant/products", ctx.tokens.merchant, {
        method: "POST",
        body: JSON.stringify({
          title: `merchant-product-${Date.now()}`,
          basePrice: 888,
          categoryId: firstCategory ? firstCategory.id : null,
          cover: "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=80",
          departCity: "Shanghai",
          tags: ["api-test"],
          calendar: [],
        }),
      });
      assert(res.status === 200, `HTTP status should be 200, got ${res.status}`);
      assert(res.body.code === 0, `code should be 0, got ${res.body.code}`);
      ctx.ids.newProductId = res.body.data.product.id;
      return {
        productId: ctx.ids.newProductId,
        categoryId: res.body.data.product.category_id,
      };
    }),
  );
  report.cases.push(
    await runCase("merchant.products.update", async () => {
      const res = await requestWithToken(`/merchant/products/${ctx.ids.newProductId}`, ctx.tokens.merchant, {
        method: "PUT",
        body: JSON.stringify({
          status: "off_sale",
          basePrice: 999,
        }),
      });
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      assert(res.body.data.product.status === "off_sale", "鍟嗗搧搴旀洿鏂颁负 off_sale");
      return { status: res.body.data.product.status };
    }),
  );

  report.cases.push(
    await runCase("merchant.products.calendar", async () => {
      const targetDate = new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
      const res = await requestWithToken(
        `/merchant/products/${ctx.ids.newProductId}/calendar`,
        ctx.tokens.merchant,
        {
          method: "POST",
          body: JSON.stringify({
            calendars: [{ date: targetDate, price: 1001, stock: 8, sold: 0 }],
          }),
        },
      );
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      return { count: res.body.data.count };
    }),
  );

  report.cases.push(
    await runCase("merchant.products.delete", async () => {
      const categoryRes = await request("/categories");
      assert(categoryRes.status === 200 && categoryRes.body.code === 0, "fetch categories failed");
      const firstCategory = (categoryRes.body.data || [])[0];

      const createRes = await requestWithToken("/merchant/products", ctx.tokens.merchant, {
        method: "POST",
        body: JSON.stringify({
          title: `merchant-delete-${Date.now()}`,
          basePrice: 666,
          categoryId: firstCategory ? firstCategory.id : null,
          cover: "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=80",
          departCity: "Guangzhou",
          tags: ["delete-case"],
          calendar: [],
        }),
      });
      assert(createRes.status === 200 && createRes.body.code === 0, "create product for delete failed");
      const deleteProductId = createRes.body.data.product.id;

      const delRes = await requestWithToken(`/merchant/products/${deleteProductId}`, ctx.tokens.merchant, {
        method: "DELETE",
      });
      assert(delRes.status === 200, `HTTP status should be 200, got ${delRes.status}`);
      assert(delRes.body.code === 0, `code should be 0, got ${delRes.body.code}`);
      return { productId: delRes.body.data.productId };
    }),
  );

  report.cases.push(
    await runCase("admin.dashboard", async () => {
      const res = await requestWithToken("/admin/dashboard", ctx.tokens.admin);
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      return {
        totalUsers: res.body.data.totalUsers,
        totalOrders: res.body.data.totalOrders,
      };
    }),
  );

  report.cases.push(
    await runCase("admin.users.list", async () => {
      const res = await requestWithToken("/admin/users?page=1&pageSize=50", ctx.tokens.admin);
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      assert((res.body.data.items || []).length > 0, "鐢ㄦ埛鍒楄〃搴旇嚦灏戞湁 1 鏉?");
      return { total: res.body.data.pagination.total };
    }),
  );

  report.cases.push(
    await runCase("admin.users.create", async () => {
      const username = `apitest_${Date.now()}_${randomSuffix()}`;
      const res = await requestWithToken("/admin/users", ctx.tokens.admin, {
        method: "POST",
        body: JSON.stringify({
          username,
          password: "123456",
          nickname: "鎺ュ彛娴嬭瘯鏂板鐢ㄦ埛",
          phone: "13900001111",
          role: "user",
          status: "active",
        }),
      });
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      ctx.ids.newUserId = res.body.data.user.id;
      ctx.ids.newUsername = username;
      return { userId: ctx.ids.newUserId, username };
    }),
  );

  report.cases.push(
    await runCase("admin.users.update", async () => {
      const res = await requestWithToken(`/admin/users/${ctx.ids.newUserId}`, ctx.tokens.admin, {
        method: "PUT",
        body: JSON.stringify({
          nickname: "鎺ュ彛娴嬭瘯鏇存柊鏄电О",
          phone: "13900002222",
          status: "active",
        }),
      });
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      assert(res.body.data.user.nickname === "鎺ュ彛娴嬭瘯鏇存柊鏄电О", "鏄电О鏇存柊鏈敓鏁?");
      return { nickname: res.body.data.user.nickname };
    }),
  );

  report.cases.push(
    await runCase("admin.users.disable", async () => {
      const res = await requestWithToken(`/admin/users/${ctx.ids.newUserId}`, ctx.tokens.admin, {
        method: "DELETE",
      });
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      return { status: res.body.data.status };
    }),
  );

  report.cases.push(
    await runCase("admin.orders.list", async () => {
      const res = await requestWithToken("/admin/orders?page=1&pageSize=50", ctx.tokens.admin);
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      return { total: res.body.data.pagination.total };
    }),
  );

  report.cases.push(
    await runCase("admin.products.list", async () => {
      const res = await requestWithToken("/admin/products?page=1&pageSize=50", ctx.tokens.admin);
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      return { total: res.body.data.pagination.total };
    }),
  );

  report.cases.push(
    await runCase("admin.products.update", async () => {
      const res = await requestWithToken(`/admin/products/${ctx.ids.newProductId}`, ctx.tokens.admin, {
        method: "PUT",
        body: JSON.stringify({
          status: "on_sale",
        }),
      });
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      assert(res.body.data.product.status === "on_sale", "鍟嗗搧鐘舵€佹洿鏂版湭鐢熸晥");
      return { status: res.body.data.product.status };
    }),
  );

  report.cases.push(
    await runCase("admin.products.disable", async () => {
      const res = await requestWithToken(`/admin/products/${ctx.ids.newProductId}`, ctx.tokens.admin, {
        method: "DELETE",
      });
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      return { status: res.body.data.status };
    }),
  );

  report.cases.push(
    await runCase("admin.categories.list", async () => {
      const res = await requestWithToken("/admin/categories", ctx.tokens.admin);
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      return { count: (res.body.data || []).length };
    }),
  );

  report.cases.push(
    await runCase("admin.merchants.list", async () => {
      const res = await requestWithToken("/admin/merchants", ctx.tokens.admin);
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      assert((res.body.data || []).length > 0, "鍟嗗鍒楄〃搴旇嚦灏戞湁 1 鏉?");
      ctx.ids.merchantId = res.body.data[0].id;
      return { merchantId: ctx.ids.merchantId };
    }),
  );

  report.cases.push(
    await runCase("admin.auditMerchant", async () => {
      const res = await requestWithToken(`/admin/merchants/${ctx.ids.merchantId}/audit`, ctx.tokens.admin, {
        method: "POST",
        body: JSON.stringify({
          auditStatus: "approved",
        }),
      });
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      return { auditStatus: res.body.data.merchant.audit_status };
    }),
  );

  report.cases.push(
    await runCase("admin.categories.upsert", async () => {
      const categoryName = `鎺ュ彛娴嬭瘯绫荤洰-${randomSuffix()}`;
      const res = await requestWithToken("/admin/categories", ctx.tokens.admin, {
        method: "POST",
        body: JSON.stringify({
          name: categoryName,
          status: "active",
        }),
      });
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      ctx.ids.newCategoryName = categoryName;
      return { name: categoryName };
    }),
  );

  report.cases.push(
    await runCase("admin.categories.delete", async () => {
      const listRes = await requestWithToken("/admin/categories", ctx.tokens.admin);
      assert(listRes.status === 200 && listRes.body.code === 0, "璇诲彇绫荤洰鍒楄〃澶辫触");
      const target = (listRes.body.data || []).find((row) => row.name === ctx.ids.newCategoryName);
      assert(!!target, "鏈壘鍒板緟鍒犻櫎绫荤洰");
      const delRes = await requestWithToken(`/admin/categories/${target.id}`, ctx.tokens.admin, {
        method: "DELETE",
      });
      assert(delRes.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${delRes.status}`);
      assert(delRes.body.code === 0, `code 搴斾负 0锛屽疄闄?${delRes.body.code}`);
      return { categoryId: delRes.body.data.categoryId };
    }),
  );

  report.cases.push(
    await runCase("admin.banners.config", async () => {
      const res = await requestWithToken("/admin/banners", ctx.tokens.admin, {
        method: "POST",
        body: JSON.stringify({
          banners: [
            {
              title: "鎺ュ彛娴嬭瘯 Banner",
              image: "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=80",
              link: "/pages/index/index",
              sort: 1,
              enabled: true,
            },
          ],
        }),
      });
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      return { count: res.body.data.count };
    }),
  );

  report.cases.push(
    await runCase("admin.banners.list", async () => {
      const res = await requestWithToken("/admin/banners", ctx.tokens.admin);
      assert(res.status === 200, `HTTP 鐘舵€佸簲涓?200锛屽疄闄?${res.status}`);
      assert(res.body.code === 0, `code 搴斾负 0锛屽疄闄?${res.body.code}`);
      assert((res.body.data || []).length > 0, "banner 鍒楄〃搴旇嚦灏戞湁 1 鏉?");
      return { count: (res.body.data || []).length };
    }),
  );

  report.finishedAt = now();
  report.total = report.cases.length;
  report.failed = report.cases.filter((item) => !item.pass).length;
  report.passed = report.total - report.failed;

  console.log("\n================ 娴嬭瘯姹囨€?================");
  console.log(`API Base: ${baseUrl}`);
  console.log(`鎬绘暟: ${report.total}`);
  console.log(`閫氳繃: ${report.passed}`);
  console.log(`澶辫触: ${report.failed}`);
  if (report.failed > 0) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error("娴嬭瘯鑴氭湰寮傚父閫€鍑?", error);
  process.exit(1);
});

