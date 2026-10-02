<template>
  <view class="page">
    <view class="profile card-shadow">
      <view class="avatar">{{ avatarText }}</view>
      <view class="profile-main">
        <text class="name">{{ user.nickname || user.username || "普通用户" }}</text>
        <text class="meta">账号：{{ user.username || "-" }}</text>
        <text class="meta">角色：普通用户</text>
      </view>
    </view>

    <view class="panel card-shadow">
      <text class="panel-title">我的服务</text>
      <view class="menu-list">
        <view class="menu-item" @click="goOrders">
          <text>我的订单</text>
          <text class="arrow">></text>
        </view>
        <view class="menu-item" @click="refreshOrders">
          <text>刷新订单统计</text>
          <text class="arrow">></text>
        </view>
      </view>
      <view class="stats">
        <view class="stat-cell">
          <text class="stat-num">{{ stats.total }}</text>
          <text class="stat-label">订单总数</text>
        </view>
        <view class="stat-cell">
          <text class="stat-num">{{ stats.pending }}</text>
          <text class="stat-label">待支付</text>
        </view>
        <view class="stat-cell">
          <text class="stat-num">{{ stats.toTravel }}</text>
          <text class="stat-label">待出行</text>
        </view>
        <view class="stat-cell">
          <text class="stat-num">{{ stats.completed }}</text>
          <text class="stat-label">已完成</text>
        </view>
      </view>
    </view>

    <view class="panel card-shadow">
      <text class="panel-title">账号操作</text>
      <button class="logout-btn" @click="switchAccount">退出登录</button>
    </view>
  </view>
</template>

<script>
import { api } from "@/common/api";
import { getCurrentUser, hasLogin, logout } from "@/common/auth";

export default {
  data() {
    return {
      user: {},
      stats: {
        total: 0,
        pending: 0,
        toTravel: 0,
        completed: 0,
      },
    };
  },
  computed: {
    avatarText() {
      const source = this.user.nickname || this.user.username || "U";
      return source.substring(0, 1).toUpperCase();
    },
  },
  async onShow() {
    if (!hasLogin()) {
      uni.reLaunch({ url: "/pages/login/index" });
      return;
    }
    this.user = getCurrentUser() || {};
    if (this.user.role === "merchant") {
      uni.reLaunch({ url: "/pages/merchant/dashboard" });
      return;
    }
    if (this.user.role === "admin") {
      uni.reLaunch({ url: "/pages/admin/index" });
      return;
    }
    await this.refreshOrders();
  },
  methods: {
    async refreshOrders() {
      try {
        const pageSize = 50;
        let page = 1;
        let items = [];
        while (page <= 40) {
          const res = await api.getOrderList({ page, pageSize });
          const batch = res.items || [];
          items = items.concat(batch);
          const total = (res.pagination && res.pagination.total) || 0;
          if (!batch.length || batch.length < pageSize || (total && items.length >= total)) {
            break;
          }
          page += 1;
        }
        this.stats.total = items.length;
        this.stats.pending = items.filter((item) => item.status === "pending_payment").length;
        this.stats.toTravel = items.filter((item) => item.status === "to_travel").length;
        this.stats.completed = items.filter((item) => item.status === "completed").length;
      } catch (error) {
        uni.showToast({
          title: error.message || "加载失败",
          icon: "none",
        });
      }
    },
    goOrders() {
      uni.switchTab({
        url: "/pages/order/list",
      });
    },
    switchAccount() {
      logout();
      uni.reLaunch({
        url: "/pages/login/index",
      });
    },
  },
};
</script>

<style>
.page {
  min-height: 100vh;
  background: linear-gradient(180deg, #f2f6fd 0%, #ecf2fb 100%);
  padding: 24rpx;
}

.profile {
  background: linear-gradient(130deg, #1c74f8 0%, #359dff 100%);
  border-radius: 18rpx;
  padding: 24rpx;
  display: flex;
  align-items: center;
}

.avatar {
  width: 86rpx;
  height: 86rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.22);
  color: #ffffff;
  font-size: 42rpx;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.profile-main {
  margin-left: 18rpx;
}

.name {
  display: block;
  color: #ffffff;
  font-size: 32rpx;
  font-weight: 700;
}

.meta {
  display: block;
  margin-top: 8rpx;
  color: rgba(255, 255, 255, 0.9);
  font-size: 22rpx;
}

.panel {
  margin-top: 16rpx;
  background: #ffffff;
  border-radius: 16rpx;
  padding: 18rpx;
}

.panel-title {
  display: block;
  color: #213853;
  font-size: 28rpx;
  font-weight: 700;
}

.menu-list {
  margin-top: 12rpx;
}

.menu-item {
  height: 72rpx;
  border-radius: 12rpx;
  background: #f4f8fd;
  padding: 0 16rpx;
  margin-top: 10rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #315175;
  font-size: 24rpx;
}

.arrow {
  color: #7891b0;
}

.stats {
  margin-top: 16rpx;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10rpx;
}

.stat-cell {
  background: #f7f9fd;
  border-radius: 12rpx;
  padding: 12rpx;
}

.stat-num {
  display: block;
  color: #2d5d98;
  font-size: 30rpx;
  font-weight: 700;
}

.stat-label {
  margin-top: 6rpx;
  display: block;
  color: #7087a5;
  font-size: 22rpx;
}

.logout-btn {
  margin-top: 14rpx;
  border: 0;
  border-radius: 12rpx;
  background: #ffeef0;
  color: #d1495f;
  font-size: 26rpx;
}
</style>
