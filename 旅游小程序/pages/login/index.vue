<template>
  <view class="login-page">
    <view class="login-card card-shadow">
      <text class="card-title">账号登录</text>
      <text class="card-subtitle">请输入账号和密码继续</text>

      <view class="field">
        <text class="field-label">账户</text>
        <input v-model.trim="form.username" class="field-input" placeholder="请输入账号" />
      </view>
      <view class="field">
        <text class="field-label">密码</text>
        <input v-model="form.password" password class="field-input" placeholder="请输入密码" />
      </view>

      <button class="login-btn" :loading="loading" @click="handleLogin">登录</button>
    </view>
  </view>
</template>

<script>
import { loginByAccount } from "@/common/auth";

export default {
  data() {
    return {
      loading: false,
      form: {
        username: "",
        password: "",
      }
    };
  },
  methods: {
    async handleLogin() {
      if (!this.form.username || !this.form.password) {
        uni.showToast({
          title: "请输入账号和密码",
          icon: "none",
        });
        return;
      }
      this.loading = true;
      try {
        const profile = await loginByAccount({
          username: this.form.username,
          password: this.form.password
        });
        const role = profile.user.role;
        const target = role === "admin"
          ? "/pages/admin/index"
          : role === "merchant"
            ? "/pages/merchant/dashboard"
            : "/pages/index/index";
        uni.reLaunch({
          url: target,
        });
      } catch (error) {
        uni.showToast({
          title: error.message || "登录失败",
          icon: "none",
        });
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style>
.login-page {
  min-height: 100vh;
  background: linear-gradient(165deg, #e8f2ff 0%, #f7fbff 42%, #f0f8ff 100%);
  padding: 32rpx;
  display: flex;
  align-items: center;
}

.login-card {
  width: 100%;
  background: #ffffff;
  border-radius: 28rpx;
  padding: 40rpx 28rpx;
}

.card-title {
  display: block;
  font-size: 36rpx;
  color: #18375e;
  font-weight: 800;
}

.card-subtitle {
  margin-top: 12rpx;
  display: block;
  font-size: 24rpx;
  color: #5d7596;
}

.field {
  margin-top: 22rpx;
}

.field-label {
  font-size: 24rpx;
  color: #4f6583;
}

.field-input {
  margin-top: 10rpx;
  height: 78rpx;
  border-radius: 14rpx;
  background: #f5f8fd;
  padding: 0 18rpx;
  color: #203a5a;
  font-size: 26rpx;
}

.login-btn {
  margin-top: 34rpx;
  height: 84rpx;
  line-height: 84rpx;
  border-radius: 14rpx;
  border: 0;
  background: linear-gradient(120deg, #1a74f7 0%, #2e90ff 100%);
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
}
</style>
