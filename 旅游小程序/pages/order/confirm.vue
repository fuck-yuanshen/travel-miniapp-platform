<template>
  <view class="page" v-if="order.orderNo">
    <view class="card card-shadow">
      <text class="title">订单号：{{ order.orderNo }}</text>
      <text class="status" :class="statusClass">{{ displayStatusLabel }}</text>
      <text class="time">创建时间：{{ order.createdAt }}</text>
      <text class="time">收货日期：{{ order.travelDate }}</text>
    </view>

    <view class="card card-shadow" v-if="order.status === 'to_travel'">
      <text class="tip-title">收货说明</text>
      <text class="tip-text">1. 商品已进入待收货状态。</text>
      <text class="tip-text">2. 收到商品后，点击下方“确认收货”。</text>
      <text class="tip-text">3. 如有问题，可联系商家处理售后。</text>
    </view>

    <view class="card card-shadow" v-for="item in order.items" :key="item.product_id + item.sku_date">
      <text class="name">{{ item.title }}</text>
      <view class="kv-line">
        <text class="info">单价：¥{{ item.unit_price }}</text>
        <text class="info">人数：{{ item.qty }}</text>
      </view>
      <text class="info">收货日期：{{ item.sku_date }}</text>
    </view>

    <view class="card card-shadow">
      <view class="kv-line">
        <text class="amount-label">订单金额</text>
        <text class="amount">¥{{ order.amount }}</text>
      </view>
      <view class="kv-line">
        <text class="amount-label">支付金额</text>
        <text class="amount">¥{{ order.payAmount }}</text>
      </view>
    </view>

    <view class="card card-shadow" v-if="order.status === 'completed'">
      <text class="tip-title">商品评价</text>

      <view v-if="order.review" class="review-readonly">
        <text class="review-score">评分：{{ starText(order.review.score) }}（{{ order.review.score }}分）</text>
        <text class="review-content" v-if="order.review.content">{{ order.review.content }}</text>
        <text class="review-content" v-else>该订单未填写文字评价</text>
        <text class="review-time">评价时间：{{ order.review.created_at }}</text>
        <view class="merchant-reply" v-if="order.review.reply">
          <text class="reply-title">商家回复</text>
          <text class="reply-content">{{ order.review.reply }}</text>
        </view>
      </view>

      <view v-else-if="canReview">
        <view class="score-row">
          <text class="score-label">评分</text>
          <view class="stars">
            <text
              v-for="n in 5"
              :key="n"
              class="star"
              :class="{ active: reviewForm.score >= n }"
              @click="setScore(n)"
            >★</text>
          </view>
        </view>
        <textarea
          v-model.trim="reviewForm.content"
          class="review-input"
          placeholder="请填写对商品和服务的评价（可选）"
        ></textarea>
        <button class="btn-primary" :loading="reviewSubmitting" @click="submitReview">提交评价</button>
      </view>

      <view v-else class="review-readonly">
        <text class="review-content">当前角色不可提交评价</text>
      </view>
    </view>

    <view class="actions">
      <button class="btn-primary" v-if="order.status === 'pending_payment'" @click="handlePay">模拟支付</button>
      <button class="btn-danger" v-if="order.status === 'pending_payment'" @click="handleCancel">取消订单</button>
      <button class="btn-primary" v-if="order.status === 'to_travel'" @click="handleConfirmTravel">确认收货</button>
      <button class="btn-default" v-if="order.status !== 'pending_payment' && order.status !== 'to_travel'" @click="goOrders">返回订单列表</button>
    </view>
  </view>
</template>

<script>
import { api } from "@/common/api";
import { getCurrentUser } from "@/common/auth";

export default {
  data() {
    return {
      orderNo: "",
      order: {},
      user: {},
      reviewSubmitting: false,
      reviewForm: {
        score: 5,
        content: "",
      },
    };
  },
  onLoad(query) {
    this.orderNo = query.orderNo || "";
    this.user = getCurrentUser() || {};
    if (!this.orderNo) {
      uni.showToast({
        title: "缺少订单号",
        icon: "none",
      });
      return;
    }
    this.loadOrder();
  },
  computed: {
    displayStatusLabel() {
      if (this.order.status === "to_travel") {
        return "待收货";
      }
      return this.order.statusLabel || this.order.status || "";
    },
    statusClass() {
      const map = {
        pending_payment: "st-pending",
        to_travel: "st-active",
        completed: "st-done",
        cancelled: "st-cancel",
        refunded: "st-cancel",
      };
      return map[this.order.status] || "st-active";
    },
    canReview() {
      return ["user", "admin"].includes(this.user.role);
    },
  },
  methods: {
    starText(score) {
      const s = Number(score || 0);
      return `${"★".repeat(Math.max(0, Math.min(5, s)))}${"☆".repeat(Math.max(0, 5 - s))}`;
    },
    setScore(score) {
      this.reviewForm.score = score;
    },
    async loadOrder() {
      try {
        uni.showLoading({ title: "加载中" });
        const res = await api.getOrderDetail(this.orderNo);
        this.order = res.order || {};
      } catch (error) {
        uni.showToast({
          title: error.message || "加载失败",
          icon: "none",
        });
      } finally {
        uni.hideLoading();
      }
    },
    async submitReview() {
      if (this.reviewSubmitting) {
        return;
      }
      if (!this.canReview) {
        uni.showToast({ title: "当前角色不可评价", icon: "none" });
        return;
      }
      this.reviewSubmitting = true;
      try {
        uni.showLoading({ title: "提交中" });
        await api.createReview({
          orderNo: this.orderNo,
          score: this.reviewForm.score,
          content: this.reviewForm.content,
          images: [],
        });
        uni.showToast({ title: "评价成功", icon: "success" });
        this.reviewForm.content = "";
        await this.loadOrder();
      } catch (error) {
        uni.showToast({
          title: error.message || "评价失败",
          icon: "none",
        });
      } finally {
        this.reviewSubmitting = false;
        uni.hideLoading();
      }
    },
    async handlePay() {
      try {
        uni.showLoading({ title: "支付中" });
        await api.mockPay(this.orderNo);
        uni.showToast({ title: "支付成功", icon: "success" });
        this.loadOrder();
      } catch (error) {
        uni.showToast({
          title: error.message || "支付失败",
          icon: "none",
        });
      } finally {
        uni.hideLoading();
      }
    },
    async handleCancel() {
      try {
        uni.showLoading({ title: "取消中" });
        await api.cancelOrder(this.orderNo);
        uni.showToast({ title: "已取消", icon: "none" });
        this.loadOrder();
      } catch (error) {
        uni.showToast({
          title: error.message || "取消失败",
          icon: "none",
        });
      } finally {
        uni.hideLoading();
      }
    },
    async handleConfirmTravel() {
      try {
        uni.showLoading({ title: "提交中" });
        await api.confirmOrder(this.orderNo);
        uni.showToast({ title: "已完成", icon: "success" });
        this.loadOrder();
      } catch (error) {
        uni.showToast({
          title: error.message || "确认失败",
          icon: "none",
        });
      } finally {
        uni.hideLoading();
      }
    },
    goOrders() {
      uni.switchTab({
        url: "/pages/order/list",
      });
    },
  },
};
</script>

<style>
.page {
  min-height: 100vh;
  background: linear-gradient(180deg, #f0f5fb 0%, #edf3fb 100%);
  padding: 20rpx;
}

.card {
  background: #ffffff;
  border-radius: 16rpx;
  padding: 20rpx;
  margin-bottom: 16rpx;
}

.title {
  display: block;
  font-size: 28rpx;
  color: #23364f;
  font-weight: 600;
}

.status {
  display: block;
  margin-top: 12rpx;
  font-size: 30rpx;
  font-weight: 700;
}

.st-pending {
  color: #ff8a1f;
}

.st-active {
  color: #1882f7;
}

.st-done {
  color: #16aa58;
}

.st-cancel {
  color: #8e9bad;
}

.tip-title {
  display: block;
  color: #1f3f63;
  font-size: 26rpx;
  font-weight: 700;
}

.tip-text {
  display: block;
  margin-top: 8rpx;
  color: #4f6784;
  font-size: 23rpx;
}

.time,
.info {
  display: block;
  margin-top: 8rpx;
  color: #5e7390;
  font-size: 24rpx;
}

.name {
  display: block;
  color: #193256;
  font-size: 28rpx;
  font-weight: 600;
}

.kv-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10rpx;
}

.amount {
  font-size: 34rpx;
  color: #ea5f30;
  font-weight: 700;
}

.amount-label {
  color: #637791;
  font-size: 24rpx;
}

.review-readonly {
  margin-top: 12rpx;
}

.review-score {
  display: block;
  color: #235187;
  font-size: 24rpx;
  font-weight: 700;
}

.review-content {
  margin-top: 8rpx;
  display: block;
  color: #4f6784;
  font-size: 23rpx;
}

.review-time {
  margin-top: 8rpx;
  display: block;
  color: #8b9bb0;
  font-size: 21rpx;
}

.score-row {
  margin-top: 10rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.score-label {
  color: #425f82;
  font-size: 24rpx;
}

.stars {
  display: flex;
  gap: 8rpx;
}

.star {
  color: #d2d9e3;
  font-size: 36rpx;
  line-height: 1;
}

.star.active {
  color: #ffb11f;
}

.review-input {
  margin-top: 12rpx;
  width: 100%;
  box-sizing: border-box;
  min-height: 150rpx;
  background: #f3f7fc;
  border-radius: 12rpx;
  padding: 14rpx;
  color: #1f3653;
}

.merchant-reply {
  margin-top: 14rpx;
  padding: 12rpx;
  border-radius: 12rpx;
  background: #f3f8ff;
}

.reply-title {
  display: block;
  color: #225fa8;
  font-size: 23rpx;
  font-weight: 700;
}

.reply-content {
  margin-top: 6rpx;
  display: block;
  color: #345477;
  font-size: 23rpx;
}

.actions button {
  margin-top: 14rpx;
  border-radius: 12rpx;
  font-size: 26rpx;
}

.btn-primary {
  background: linear-gradient(130deg, #1b75f8 0%, #2f95ff 100%);
  color: #ffffff;
  border: 0;
}

.btn-danger {
  background: #ffecee;
  color: #d64056;
  border: 1rpx solid #ffd2d8;
}

.btn-default {
  background: #f0f4fa;
  color: #4e6888;
  border: 1rpx solid #dde6f3;
}
</style>
