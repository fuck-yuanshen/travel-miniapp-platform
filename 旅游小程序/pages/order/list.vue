<template>
  <view class="page">
    <view class="summary card-shadow">
      <text class="summary-title">我的订单</text>
      <text class="summary-sub">共 {{ total }} 条记录</text>
    </view>

    <scroll-view class="tab-scroll" scroll-x>
      <view class="tabs">
        <view
          v-for="item in tabs"
          :key="item.value"
          class="tab-item"
          :class="{ active: status === item.value }"
          @click="changeStatus(item.value)"
        >
          {{ item.label }}
        </view>
      </view>
    </scroll-view>

    <view class="order-list">
      <view class="order-card card-shadow" v-for="item in orders" :key="item.orderNo" @click="goDetail(item.orderNo)">
        <view class="head">
          <text class="no text-ellipsis">{{ item.orderNo }}</text>
          <text class="status" :class="statusClass(item.status)">{{ displayStatus(item) }}</text>
        </view>
        <text class="title text-ellipsis">{{ item.productTitle || "旅游商品" }}</text>
        <view class="meta">
          <text>收货：{{ item.travelDate }}</text>
          <text>数量：{{ item.itemQty }}</text>
        </view>
        <view class="meta">
          <text>金额：¥{{ item.amount }}</text>
          <text>{{ item.createdAt }}</text>
        </view>
        <text class="tip" v-if="item.status === 'to_travel'">待收货订单可进入详情页点击“确认收货”</text>
        <view class="card-actions" v-if="item.status === 'to_travel'">
          <button class="confirm-btn" size="mini" @click.stop="handleConfirmTravel(item.orderNo)">确认收货</button>
        </view>
      </view>
      <view class="empty" v-if="orders.length === 0">
        当前暂无订单
      </view>
    </view>
  </view>
</template>

<script>
import { api } from "@/common/api";

export default {
  data() {
    return {
      status: "",
      orders: [],
      total: 0,
      loading: false,
      tabs: [
        { label: "全部", value: "" },
        { label: "待支付", value: "pending_payment" },
        { label: "待收货", value: "to_travel" },
        { label: "已完成", value: "completed" },
        { label: "已取消", value: "cancelled" },
        { label: "退款中", value: "refunding" },
        { label: "已退款", value: "refunded" },
      ],
    };
  },
  onShow() {
    this.loadOrders();
  },
  methods: {
    displayStatus(item) {
      if (item.status === "to_travel") {
        return "待收货";
      }
      return item.statusLabel || item.status || "";
    },
    statusClass(status) {
      const map = {
        pending_payment: "st-pending",
        to_travel: "st-active",
        completed: "st-done",
        cancelled: "st-cancel",
        refunding: "st-pending",
        refunded: "st-cancel",
      };
      return map[status] || "";
    },
    async loadOrders() {
      if (this.loading) {
        return;
      }
      this.loading = true;
      try {
        uni.showLoading({ title: "加载中" });
        const pageSize = 50;
        let page = 1;
        let allItems = [];
        let total = 0;
        while (page <= 40) {
          const params = { page, pageSize };
          if (this.status) {
            params.status = this.status;
          }
          const res = await api.getOrderList(params);
          const items = res.items || [];
          total = (res.pagination && res.pagination.total) || total;
          allItems = allItems.concat(items);
          if (!items.length || items.length < pageSize || (total && allItems.length >= total)) {
            break;
          }
          page += 1;
        }
        this.orders = allItems;
        this.total = total || allItems.length;
      } catch (error) {
        uni.showToast({
          title: error.message || "加载失败",
          icon: "none",
        });
      } finally {
        this.loading = false;
        uni.hideLoading();
      }
    },
    changeStatus(next) {
      this.status = next;
      this.loadOrders();
    },
    goDetail(orderNo) {
      uni.navigateTo({
        url: `/pages/order/confirm?orderNo=${orderNo}`,
      });
    },
    async handleConfirmTravel(orderNo) {
      try {
        uni.showLoading({ title: "提交中" });
        await api.confirmOrder(orderNo);
        uni.showToast({ title: "已完成", icon: "success" });
        await this.loadOrders();
      } catch (error) {
        uni.showToast({
          title: error.message || "确认失败",
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
  background: linear-gradient(180deg, #f1f6fd 0%, #edf3fb 100%);
}

.summary {
  margin: 16rpx 18rpx 0;
  border-radius: 16rpx;
  background: linear-gradient(130deg, #1b75f8 0%, #2f95ff 100%);
  padding: 20rpx;
}

.summary-title {
  display: block;
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 700;
}

.summary-sub {
  margin-top: 8rpx;
  display: block;
  color: rgba(255, 255, 255, 0.88);
  font-size: 22rpx;
}

.tab-scroll {
  padding: 18rpx 18rpx 0;
  white-space: nowrap;
}

.tabs {
  display: inline-flex;
  gap: 12rpx;
}

.tab-item {
  padding: 10rpx 20rpx;
  border-radius: 999rpx;
  background: #e6eef9;
  color: #4d6484;
  font-size: 24rpx;
}

.tab-item.active {
  background: #2b7fff;
  color: #ffffff;
}

.order-list {
  padding: 14rpx 18rpx 22rpx;
}

.order-card {
  background: #ffffff;
  border-radius: 16rpx;
  margin-bottom: 14rpx;
  padding: 18rpx;
  border: 1rpx solid #e8eef8;
}

.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.no {
  font-size: 22rpx;
  color: #6f84a2;
  max-width: 380rpx;
}

.status {
  font-size: 24rpx;
  font-weight: 600;
}

.st-pending {
  color: #ff8a1f;
}

.st-active {
  color: #0f8afc;
}

.st-done {
  color: #19a35b;
}

.st-cancel {
  color: #8f9caf;
}

.title {
  margin-top: 10rpx;
  display: block;
  font-size: 28rpx;
  color: #18314f;
  font-weight: 600;
}

.meta {
  margin-top: 8rpx;
  display: flex;
  justify-content: space-between;
  color: #6a809e;
  font-size: 23rpx;
}

.tip {
  margin-top: 10rpx;
  display: block;
  color: #3f6ea6;
  font-size: 22rpx;
}

.card-actions {
  margin-top: 10rpx;
  display: flex;
  justify-content: flex-end;
}

.confirm-btn {
  background: #eaf4ff;
  color: #175fc8;
  border: 1rpx solid #ccdef7;
}

.empty {
  text-align: center;
  padding: 60rpx 0;
  color: #8ba0bc;
  font-size: 24rpx;
}
</style>
