import { request } from "./request";
import config from "./config";

export const api = {
  getBanners() {
    return request({ url: "/banners", auth: false });
  },
  getCategories() {
    return request({ url: "/categories", auth: false });
  },
  getProducts(params = {}) {
    return request({ url: "/products", data: params, auth: false });
  },
  getProductDetail(productId) {
    return request({ url: `/products/${productId}`, auth: false });
  },
  createOrder(payload) {
    return request({
      url: "/orders",
      method: "POST",
      data: payload,
    });
  },
  getOrderList(params = {}) {
    return request({ url: "/orders", data: params });
  },
  getOrderDetail(orderNo) {
    return request({ url: `/orders/${orderNo}` });
  },
  cancelOrder(orderNo, reason = "用户主动取消") {
    return request({
      url: `/orders/${orderNo}/cancel`,
      method: "POST",
      data: { reason },
    });
  },
  confirmOrder(orderNo) {
    return request({
      url: `/orders/${orderNo}/confirm`,
      method: "POST",
    });
  },
  createReview(payload) {
    return request({
      url: "/reviews",
      method: "POST",
      data: payload,
    });
  },
  replyReview(reviewId, reply) {
    return request({
      url: `/reviews/${reviewId}/reply`,
      method: "POST",
      data: { reply },
    });
  },
  mockPay(orderNo) {
    return request({
      url: "/pay/mock-success",
      method: "POST",
      data: {
        orderNo,
        idemKey: `${orderNo}-${Date.now()}`,
      },
    });
  },
  getMerchantDashboard() {
    return request({ url: "/merchant/dashboard" });
  },
  getMerchantProducts() {
    return request({ url: "/merchant/products" });
  },
  getMerchantReviews(params = {}) {
    return request({ url: "/merchant/reviews", data: params });
  },
  uploadImage(filePath) {
    const uploadUrl = `${config.BASE_URL.replace(/\/api\/?$/, "")}/api/upload/image`;
    const token = uni.getStorageSync("token");
    return new Promise((resolve, reject) => {
      uni.uploadFile({
        url: uploadUrl,
        filePath,
        name: "file",
        header: token ? { Authorization: `Bearer ${token}` } : {},
        success: (res) => {
          let body = {};
          try {
            body = JSON.parse(res.data || "{}");
          } catch (error) {
            reject(new Error("上传响应解析失败"));
            return;
          }
          if (res.statusCode >= 200 && res.statusCode < 300 && body.code === 0) {
            resolve(body.data);
            return;
          }
          reject(new Error(body.message || "上传失败"));
        },
        fail: (error) => {
          reject(new Error(error.errMsg || "上传失败"));
        },
      });
    });
  },
  createMerchantProduct(payload) {
    return request({
      url: "/merchant/products",
      method: "POST",
      data: payload,
    });
  },
  updateMerchantProduct(productId, payload) {
    return request({
      url: `/merchant/products/${productId}`,
      method: "PUT",
      data: payload,
    });
  },
  deleteMerchantProduct(productId) {
    return request({
      url: `/merchant/products/${productId}`,
      method: "DELETE",
    });
  },
  getAdminMerchants() {
    return request({ url: "/admin/merchants" });
  },
  auditMerchant(merchantId, auditStatus) {
    return request({
      url: `/admin/merchants/${merchantId}/audit`,
      method: "POST",
      data: { auditStatus },
    });
  },
  getAdminDashboard() {
    return request({ url: "/admin/dashboard" });
  },
  getAdminUsers(params = {}) {
    return request({ url: "/admin/users", data: params });
  },
  createAdminUser(payload) {
    return request({
      url: "/admin/users",
      method: "POST",
      data: payload,
    });
  },
  updateAdminUser(userId, payload) {
    return request({
      url: `/admin/users/${userId}`,
      method: "PUT",
      data: payload,
    });
  },
  disableAdminUser(userId) {
    return request({
      url: `/admin/users/${userId}`,
      method: "DELETE",
    });
  },
  getAdminOrders(params = {}) {
    return request({ url: "/admin/orders", data: params });
  },
  getAdminProducts(params = {}) {
    return request({ url: "/admin/products", data: params });
  },
  updateAdminProduct(productId, payload) {
    return request({
      url: `/admin/products/${productId}`,
      method: "PUT",
      data: payload,
    });
  },
  disableAdminProduct(productId) {
    return request({
      url: `/admin/products/${productId}`,
      method: "DELETE",
    });
  },
  getAdminCategories() {
    return request({ url: "/admin/categories" });
  },
  upsertAdminCategory(payload) {
    return request({
      url: "/admin/categories",
      method: "POST",
      data: payload,
    });
  },
  deleteAdminCategory(categoryId) {
    return request({
      url: `/admin/categories/${categoryId}`,
      method: "DELETE",
    });
  },
  getAdminBanners() {
    return request({ url: "/admin/banners" });
  },
  configAdminBanners(payload) {
    return request({
      url: "/admin/banners",
      method: "POST",
      data: payload,
    });
  },
};
