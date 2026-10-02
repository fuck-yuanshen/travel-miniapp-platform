<template>
  <view class="page">
    <view class="hero card-shadow">
      <text class="hero-title">评论管理</text>
      <text class="hero-sub">查看用户评价并进行回复</text>
    </view>

    <view class="card card-shadow">
      <view class="summary-row">
        <text class="title">用户评价</text>
        <text class="summary">共 {{ total }} 条</text>
      </view>

      <view class="review-item" v-for="item in reviews" :key="item.id">
        <text class="review-head">#{{ item.id }} · {{ item.product_title || "商品" }} · {{ item.user_nickname || "用户" }}</text>
        <text class="review-time">{{ item.created_at }}</text>
        <text class="review-score">评分：{{ starText(item.score) }}（{{ item.score }}分）</text>
        <text class="review-content">{{ item.content || "用户未填写文字评价" }}</text>

        <view class="reply-box" v-if="item.reply">
          <text class="reply-label">已回复：</text>
          <text class="reply-content">{{ item.reply }}</text>
        </view>

        <view v-else class="reply-box">
          <button v-if="activeReplyId !== item.id" class="open-reply-btn" size="mini" @click="openReply(item.id)">回复评论</button>

          <view v-else>
            <textarea
              class="reply-input"
              v-model.trim="replyDrafts[item.id]"
              placeholder="请输入回复内容"
              :focus="focusReplyId === item.id"
            ></textarea>
            <view class="reply-actions">
              <button
                class="reply-btn"
                size="mini"
                :loading="replyLoadingId === item.id"
                @click="submitReply(item)"
              >提交回复</button>
              <button class="cancel-btn" size="mini" @click="cancelReply">取消</button>
            </view>
          </view>
        </view>
      </view>

      <view class="empty" v-if="reviews.length === 0">暂无评价</view>
    </view>

    <view class="merchant-tabbar">
      <view class="merchant-tab" @click="goHome">
        <text class="tab-label">首页</text>
      </view>
      <view class="merchant-tab active">
        <text class="tab-label">评论</text>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from "@/common/api";
import { getCurrentUser } from "@/common/auth";

export default {
  data() {
    return {
      user: {},
      reviews: [],
      total: 0,
      replyDrafts: {},
      activeReplyId: 0,
      focusReplyId: 0,
      replyLoadingId: 0,
    };
  },
  onShow() {
    this.user = getCurrentUser() || {};
    if (this.user.role !== "merchant") {
      uni.showToast({ title: "无权限访问评论页", icon: "none" });
      return;
    }
    this.loadReviews();
  },
  methods: {
    starText(score) {
      const s = Number(score || 0);
      return `${"★".repeat(Math.max(0, Math.min(5, s)))}${"☆".repeat(Math.max(0, 5 - s))}`;
    },
    async loadReviews() {
      try {
        uni.showLoading({ title: "加载中" });
        const res = await api.getMerchantReviews({ page: 1, pageSize: 100 });
        this.reviews = (res && res.items) || [];
        this.total = (res && res.pagination && res.pagination.total) || this.reviews.length;
      } catch (error) {
        uni.showToast({
          title: error.message || "加载失败",
          icon: "none",
        });
      } finally {
        uni.hideLoading();
      }
    },
    openReply(id) {
      this.activeReplyId = id;
      if (typeof this.replyDrafts[id] !== "string") {
        this.replyDrafts = { ...this.replyDrafts, [id]: "" };
      }
      this.focusReplyId = 0;
      this.$nextTick(() => {
        this.focusReplyId = id;
      });
    },
    cancelReply() {
      this.activeReplyId = 0;
      this.focusReplyId = 0;
    },
    async submitReply(item) {
      const reply = (this.replyDrafts[item.id] || "").trim();
      if (!reply) {
        uni.showToast({ title: "请输入回复内容", icon: "none" });
        return;
      }
      if (this.replyLoadingId) {
        return;
      }
      this.replyLoadingId = item.id;
      try {
        await api.replyReview(item.id, reply);
        uni.showToast({ title: "回复成功", icon: "success" });
        this.replyDrafts[item.id] = "";
        this.activeReplyId = 0;
        this.focusReplyId = 0;
        await this.loadReviews();
      } catch (error) {
        uni.showToast({
          title: error.message || "回复失败",
          icon: "none",
        });
      } finally {
        this.replyLoadingId = 0;
      }
    },
    goHome() {
      uni.redirectTo({ url: "/pages/merchant/dashboard" });
    },
  },
};
</script>

<style>
.page {
  min-height: 100vh;
  background: linear-gradient(180deg, #eef4fb 0%, #eaf1fa 100%);
  padding: 20rpx;
  padding-bottom: 150rpx;
}

.hero {
  background: linear-gradient(130deg, #1368f0 0%, #2591ff 100%);
  border-radius: 18rpx;
  padding: 24rpx;
  margin-bottom: 16rpx;
}

.hero-title {
  display: block;
  color: #ffffff;
  font-size: 34rpx;
  font-weight: 700;
}

.hero-sub {
  margin-top: 8rpx;
  display: block;
  color: rgba(255, 255, 255, 0.9);
  font-size: 23rpx;
}

.card {
  background: #ffffff;
  border-radius: 16rpx;
  padding: 20rpx;
  margin-bottom: 16rpx;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title {
  font-size: 28rpx;
  font-weight: 700;
  color: #182f4e;
}

.summary {
  color: #6f85a2;
  font-size: 23rpx;
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

.review-time {
  margin-top: 6rpx;
  display: block;
  color: #8a9bb2;
  font-size: 21rpx;
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

.reply-box {
  margin-top: 10rpx;
}

.reply-label {
  color: #255ea2;
  font-size: 23rpx;
  font-weight: 700;
}

.reply-content {
  margin-top: 6rpx;
  display: block;
  color: #36577d;
  font-size: 23rpx;
}

.open-reply-btn {
  background: #e8f1ff;
  color: #1d68cc;
  border: 1rpx solid #ccdefa;
}

.reply-input {
  width: 100%;
  box-sizing: border-box;
  min-height: 110rpx;
  background: #eef4fd;
  border-radius: 10rpx;
  padding: 12rpx;
}

.reply-actions {
  margin-top: 8rpx;
  display: flex;
  gap: 10rpx;
}

.reply-btn {
  background: #e8f1ff;
  color: #1d68cc;
  border: 1rpx solid #ccdefa;
}

.cancel-btn {
  background: #f0f4fa;
  color: #4e6888;
  border: 1rpx solid #dde6f3;
}

.empty {
  margin-top: 16rpx;
  text-align: center;
  color: #8197b2;
  font-size: 24rpx;
}

.merchant-tabbar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 50;
  display: flex;
  background: #ffffff;
  border-top: 1rpx solid #dde6f2;
  padding-bottom: env(safe-area-inset-bottom);
}

.merchant-tab {
  flex: 1;
  text-align: center;
  padding: 18rpx 0 14rpx;
  color: #6f85a2;
}

.merchant-tab.active {
  color: #1d74f7;
  font-weight: 700;
}

.tab-label {
  font-size: 24rpx;
}
</style>
