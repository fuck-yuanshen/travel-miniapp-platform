<template>
  <view class="page" v-if="product.id">
    <view class="hero">
      <image :src="product.cover" class="cover" mode="aspectFill"></image>
      <view class="hero-mask"></view>
      <view class="hero-info">
        <text class="hero-price">¥{{ product.base_price }} 起</text>
        <text class="hero-city">{{ product.depart_city || "-" }} 出发</text>
      </view>
    </view>

    <view class="card card-shadow">
      <text class="title">{{ product.title }}</text>
      <text class="detail">{{ product.detail }}</text>
      <text class="merchant">商家：{{ product.merchant_name }}</text>
      <text class="base-price">分类：{{ product.category_name || "未分类" }}</text>
    </view>

    <view class="card card-shadow" v-if="!isNormalProduct">
      <text class="section-title">选择出行日期</text>
      <view class="date-list">
        <view
          v-for="item in skuCalendar"
          :key="item.date"
          class="date-item"
          :class="{ active: form.travelDate === item.date, disabled: item.stock <= 0 }"
          @click="pickDate(item)"
        >
          <text>{{ item.date }}</text>
          <text>¥{{ item.price }} / 库存{{ item.stock }}</text>
        </view>
      </view>
      <view class="picked-line" v-if="form.travelDate">已选日期：{{ form.travelDate }}</view>
    </view>
    <view class="card card-shadow" v-else>
      <text class="section-title">收货说明</text>
      <text class="picked-line">普通商品默认按当日下单时间处理收货</text>
    </view>

    <view class="card order-card card-shadow">
      <text class="section-title">下单信息</text>
      <view class="row">
        <text class="row-label">人数</text>
        <view class="stepper">
          <view class="step-btn" @click="changeQty(-1)">-</view>
          <text class="qty">{{ form.qty }}</text>
          <view class="step-btn" @click="changeQty(1)">+</view>
        </view>
      </view>
      <view class="row">
        <text class="row-label">联系人</text>
        <input v-model="form.contactName" placeholder="请输入姓名" />
      </view>
      <view class="row">
        <text class="row-label">手机号</text>
        <input v-model="form.contactPhone" placeholder="请输入手机号" />
      </view>
      <view class="row">
        <text class="row-label">备注</text>
        <input v-model="form.remark" placeholder="可选" />
      </view>
      <button class="submit-btn" @click="submitOrder" :disabled="!canCreateOrder">提交订单</button>
    </view>

    <view class="card card-shadow">
      <text class="section-title">用户评价</text>
      <view class="review-item" v-for="item in reviews" :key="item.id">
        <text class="review-head">{{ item.user_nickname || "匿名用户" }} · {{ item.created_at }}</text>
        <text class="review-score">评分：{{ starText(item.score) }}（{{ item.score }}分）</text>
        <text class="review-content">{{ item.content || "该用户未填写文字评价" }}</text>
        <view class="merchant-reply" v-if="item.reply">
          <text class="reply-title">商家回复</text>
          <text class="reply-content">{{ item.reply }}</text>
        </view>
      </view>
      <view class="empty" v-if="reviews.length === 0">暂无评价</view>
    </view>
  </view>
</template>

<script>
import { api } from "@/common/api";
import { getCurrentUser } from "@/common/auth";

export default {
  data() {
    return {
      productId: 0,
      product: {},
      skuCalendar: [],
      reviews: [],
      user: {},
      form: {
        travelDate: "",
        qty: 1,
        contactName: "",
        contactPhone: "",
        remark: "",
      },
    };
  },
  computed: {
    canCreateOrder() {
      return this.user.role === "user" || this.user.role === "admin";
    },
    isNormalProduct() {
      const tags = this.product.tags || [];
      return Array.isArray(tags) && tags.includes("普通商品");
    },
  },
  onLoad(query) {
    this.productId = Number(query.id || 0);
    this.user = getCurrentUser() || {};
    this.form.contactName = this.user.nickname || "";
    this.form.contactPhone = this.user.phone || "";
    if (!this.productId) {
      uni.showToast({ title: "参数错误", icon: "none" });
      return;
    }
    this.loadDetail();
  },
  methods: {
    starText(score) {
      const s = Number(score || 0);
      return `${"★".repeat(Math.max(0, Math.min(5, s)))}${"☆".repeat(Math.max(0, 5 - s))}`;
    },
    todayDate() {
      const d = new Date();
      const y = d.getFullYear();
      const m = `${d.getMonth() + 1}`.padStart(2, "0");
      const day = `${d.getDate()}`.padStart(2, "0");
      return `${y}-${m}-${day}`;
    },
    async loadDetail() {
      try {
        uni.showLoading({ title: "加载中" });
        const res = await api.getProductDetail(this.productId);
        this.product = res.product || {};
        this.skuCalendar = res.skuCalendar || [];
        this.reviews = res.reviews || [];
        if (this.isNormalProduct) {
          this.form.travelDate = this.todayDate();
        } else {
          const firstValid = this.skuCalendar.find((item) => item.stock > 0);
          this.form.travelDate = firstValid ? firstValid.date : "";
        }
      } catch (error) {
        uni.showToast({
          title: error.message || "加载失败",
          icon: "none",
        });
      } finally {
        uni.hideLoading();
      }
    },
    pickDate(item) {
      if (item.stock <= 0) {
        return;
      }
      this.form.travelDate = item.date;
    },
    changeQty(step) {
      const next = this.form.qty + step;
      if (next < 1 || next > 9) {
        return;
      }
      this.form.qty = next;
    },
    async submitOrder() {
      if (!this.canCreateOrder) {
        uni.showToast({
          title: "当前角色不可下单",
          icon: "none",
        });
        return;
      }
      if (!this.form.contactName || !this.form.contactPhone) {
        uni.showToast({
          title: "请填写联系人和手机号",
          icon: "none",
        });
        return;
      }
      if (!this.form.travelDate) {
        if (this.isNormalProduct) {
          this.form.travelDate = this.todayDate();
        } else {
          uni.showToast({
            title: "请选择出行日期",
            icon: "none",
          });
          return;
        }
      }
      try {
        uni.showLoading({ title: "提交中" });
        const res = await api.createOrder({
          productId: this.productId,
          travelDate: this.form.travelDate,
          qty: this.form.qty,
          contactName: this.form.contactName,
          contactPhone: this.form.contactPhone,
          remark: this.form.remark,
          clientReqNo: `${this.productId}-${Date.now()}`,
        });
        const orderNo = res.order.orderNo;
        if (this.isNormalProduct) {
          try {
            await api.mockPay(orderNo);
          } catch (_error) {
            // 自动支付失败时，仍保留订单并进入详情页手动处理
          }
        }
        uni.navigateTo({
          url: `/pages/order/confirm?orderNo=${orderNo}`,
        });
      } catch (error) {
        uni.showToast({
          title: error.message || "下单失败",
          icon: "none",
        });
      } finally {
        uni.hideLoading();
      }
    },
  },
};
</script>

<style>
.page {
  min-height: 100vh;
  background: #f2f6fc;
  padding-bottom: 40rpx;
}

.hero {
  position: relative;
}

.cover {
  width: 100%;
  height: 420rpx;
}

.hero-mask {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 180rpx;
  background: linear-gradient(180deg, rgba(8, 30, 53, 0) 0%, rgba(8, 30, 53, 0.55) 100%);
}

.hero-info {
  position: absolute;
  left: 24rpx;
  bottom: 24rpx;
}

.hero-price {
  display: block;
  color: #ffffff;
  font-size: 42rpx;
  font-weight: 800;
}

.hero-city {
  margin-top: 8rpx;
  display: block;
  color: rgba(255, 255, 255, 0.92);
  font-size: 24rpx;
}

.card {
  margin: 20rpx 24rpx 0;
  background: #ffffff;
  border-radius: 18rpx;
  padding: 20rpx;
}

.title {
  display: block;
  font-size: 34rpx;
  color: #172a43;
  font-weight: 700;
}

.detail {
  display: block;
  margin-top: 14rpx;
  color: #4f627d;
  font-size: 24rpx;
  line-height: 1.6;
}

.merchant,
.base-price {
  display: block;
  margin-top: 12rpx;
  font-size: 24rpx;
  color: #6d7f95;
}

.section-title {
  display: block;
  font-size: 28rpx;
  font-weight: 600;
  color: #1f2d3d;
}

.date-list {
  margin-top: 12rpx;
  display: flex;
  flex-direction: column;
  gap: 10rpx;
  max-height: 500rpx;
  overflow: auto;
}

.date-item {
  padding: 14rpx;
  border-radius: 12rpx;
  background: #f2f6fb;
  color: #2f4a68;
  font-size: 24rpx;
  display: flex;
  justify-content: space-between;
}

.date-item.active {
  background: #2b7fff;
  color: #ffffff;
}

.date-item.disabled {
  background: #f0f0f0;
  color: #adadad;
}

.picked-line {
  margin-top: 14rpx;
  font-size: 23rpx;
  color: #4f6f96;
}

.order-card .row {
  margin-top: 16rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14rpx;
}

.row-label {
  width: 110rpx;
  color: #304d70;
  font-size: 24rpx;
}

.row input {
  flex: 1;
  background: #f5f8fc;
  height: 68rpx;
  border-radius: 12rpx;
  padding: 0 16rpx;
}

.stepper {
  display: flex;
  align-items: center;
  gap: 14rpx;
}

.step-btn {
  width: 48rpx;
  height: 48rpx;
  border-radius: 10rpx;
  background: #e7f0ff;
  color: #2f74d2;
  font-size: 34rpx;
  line-height: 48rpx;
  text-align: center;
}

.qty {
  min-width: 30rpx;
  text-align: center;
  color: #1e3655;
  font-size: 28rpx;
}

.submit-btn {
  margin-top: 24rpx;
  border: 0;
  border-radius: 14rpx;
  background: linear-gradient(130deg, #1b75f8 0%, #2f95ff 100%);
  color: #ffffff;
  font-size: 28rpx;
  font-weight: 600;
}

.review-item {
  margin-top: 12rpx;
  padding: 12rpx;
  border-radius: 12rpx;
  background: #f7f9fd;
}

.review-head {
  display: block;
  color: #4d678a;
  font-size: 22rpx;
}

.review-score {
  margin-top: 8rpx;
  display: block;
  color: #2f4e73;
  font-size: 23rpx;
  font-weight: 600;
}

.review-content {
  margin-top: 8rpx;
  display: block;
  color: #405f83;
  font-size: 23rpx;
}

.merchant-reply {
  margin-top: 10rpx;
  padding: 10rpx;
  border-radius: 10rpx;
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

.empty {
  margin-top: 12rpx;
  text-align: center;
  color: #8ba0bc;
  font-size: 24rpx;
}
</style>
