<template>
  <view class="page">
    <view class="hero card-shadow">
      <view>
        <text class="hero-title">管理员数据面板</text>
        <text class="hero-sub">仅管理员可见，覆盖用户与核心业务数据管理</text>
      </view>
      <view class="logout-btn" @click="handleLogout">退出登录</view>
    </view>

    <view class="metrics">
      <view class="metric-card card-shadow">
        <text class="metric-num">{{ dashboard.totalUsers || 0 }}</text>
        <text class="metric-label">用户总数</text>
      </view>
      <view class="metric-card card-shadow">
        <text class="metric-num">{{ dashboard.totalOrders || 0 }}</text>
        <text class="metric-label">订单总数</text>
      </view>
      <view class="metric-card card-shadow">
        <text class="metric-num">¥{{ dashboard.totalGmv || 0 }}</text>
        <text class="metric-label">GMV</text>
      </view>
      <view class="metric-card card-shadow">
        <text class="metric-num">{{ dashboard.pendingRefunds || 0 }}</text>
        <text class="metric-label">待退款</text>
      </view>
    </view>

    <scroll-view class="tab-scroll" scroll-x>
      <view class="tab-row">
        <view
          v-for="item in tabs"
          :key="item.value"
          class="tab-item"
          :class="{ active: activeTab === item.value }"
          @click="activeTab = item.value"
        >
          {{ item.label }}
        </view>
      </view>
    </scroll-view>

    <view class="panel card-shadow" v-if="activeTab === 'users'">
      <text class="panel-title">用户管理（增删改查）</text>
      <view class="search-row">
        <input v-model.trim="userKeyword" class="search-input" placeholder="搜索账号/昵称/手机号" />
        <view class="small-btn primary" @click="loadUsers">查询</view>
      </view>

      <view class="form-grid">
        <input v-model.trim="userForm.username" class="field" placeholder="账号 username" />
        <input v-model="userForm.password" class="field" password placeholder="密码（编辑可不填）" />
        <input v-model.trim="userForm.nickname" class="field" placeholder="昵称" />
        <input v-model.trim="userForm.phone" class="field" placeholder="手机号" />
        <picker class="field picker" :range="roleOptions" range-key="label" @change="pickRole">
          <view>{{ roleText(userForm.role) }}</view>
        </picker>
        <picker class="field picker" :range="statusOptions" range-key="label" @change="pickStatus">
          <view>{{ statusText(userForm.status) }}</view>
        </picker>
        <input v-if="userForm.role === 'merchant'" v-model.trim="userForm.merchantName" class="field" placeholder="商家店铺名称" />
      </view>

      <view class="action-row">
        <view class="small-btn primary" @click="submitUser">{{ editingUserId ? "保存修改" : "新增用户" }}</view>
        <view class="small-btn" @click="resetUserForm">重置</view>
      </view>

      <view class="list-item" v-for="item in users" :key="item.id">
        <view class="item-main">
          <text class="item-title">{{ item.username }}（{{ roleText(item.role) }}）</text>
          <text class="item-sub">昵称：{{ item.nickname || "-" }}，手机号：{{ item.phone || "-" }}</text>
          <text class="item-sub">状态：{{ statusText(item.status) }}，创建：{{ item.created_at }}</text>
        </view>
        <view class="item-actions">
          <view class="small-btn" @click="editUser(item)">编辑</view>
          <view class="small-btn danger" @click="disableUser(item)">禁用</view>
        </view>
      </view>
    </view>

    <view class="panel card-shadow" v-if="activeTab === 'merchants'">
      <text class="panel-title">商家审核</text>
      <view class="list-item" v-for="item in merchants" :key="item.id">
        <view class="item-main">
          <text class="item-title">{{ item.name }}</text>
          <text class="item-sub">负责人：{{ item.owner_nickname }}，状态：{{ item.audit_status }}</text>
        </view>
        <view class="item-actions">
          <view class="small-btn primary" @click="auditMerchant(item.id, 'approved')">通过</view>
          <view class="small-btn warning" @click="auditMerchant(item.id, 'rejected')">拒绝</view>
          <view class="small-btn danger" @click="auditMerchant(item.id, 'disabled')">禁用</view>
        </view>
      </view>
    </view>

    <view class="panel card-shadow" v-if="activeTab === 'products'">
      <text class="panel-title">商品管理</text>
      <view class="list-item" v-for="item in products" :key="item.id">
        <view class="item-main">
          <text class="item-title">{{ item.title }}</text>
          <text class="item-sub">商家：{{ item.merchant_name || "-" }}，价格：¥{{ item.base_price }}</text>
          <text class="item-sub">状态：{{ item.status }}，更新时间：{{ item.updated_at }}</text>
        </view>
        <view class="item-actions">
          <view class="small-btn" @click="toggleProduct(item)">{{ item.status === "on_sale" ? "下架" : "上架" }}</view>
          <view class="small-btn danger" @click="disableProduct(item)">停用</view>
        </view>
      </view>
    </view>

    <view class="panel card-shadow" v-if="activeTab === 'orders'">
      <text class="panel-title">订单数据</text>
      <view class="list-item" v-for="item in orders" :key="item.order_no">
        <view class="item-main">
          <text class="item-title">{{ item.order_no }} · {{ item.status }}</text>
          <text class="item-sub">用户：{{ item.username }}，商品：{{ item.product_title || "-" }}</text>
          <text class="item-sub">金额：¥{{ item.amount }}，出行：{{ item.travel_date }}</text>
        </view>
      </view>
    </view>

    <view class="panel card-shadow" v-if="activeTab === 'categories'">
      <text class="panel-title">类目管理</text>
      <view class="search-row">
        <input v-model.trim="categoryForm.name" class="search-input" placeholder="类目名称" />
        <view class="small-btn primary" @click="saveCategory">新增/更新</view>
      </view>
      <view class="list-item" v-for="item in categories" :key="item.id">
        <view class="item-main">
          <text class="item-title">{{ item.name }}</text>
          <text class="item-sub">状态：{{ item.status }}，创建：{{ item.created_at }}</text>
        </view>
        <view class="item-actions">
          <view class="small-btn warning" @click="changeCategoryStatus(item)">{{ item.status === "active" ? "设为停用" : "设为启用" }}</view>
          <view class="small-btn danger" @click="deleteCategory(item)">删除</view>
        </view>
      </view>
    </view>

    <view class="panel card-shadow" v-if="activeTab === 'banners'">
      <text class="panel-title">Banner 管理</text>
      <view class="banner-form" v-for="(item, index) in banners" :key="index">
        <input v-model.trim="item.title" class="field" placeholder="标题" />
        <input v-model.trim="item.image" class="field" placeholder="图片 URL（可手动输入）" />
        <input v-model.trim="item.link" class="field" placeholder="跳转路径，如 /pages/index/index" />
        <image v-if="item.image" :src="item.image" class="banner-preview" mode="aspectFill"></image>
        <view class="action-row">
          <view class="small-btn primary" @click="uploadBannerImage(index)">{{ uploadingBannerIndex === index ? "上传中..." : "上传图片" }}</view>
          <view class="small-btn warning" @click="item.enabled = !item.enabled">{{ item.enabled ? "已启用" : "已停用" }}</view>
          <view class="small-btn danger" @click="removeBanner(index)">删除</view>
        </view>
      </view>
      <view class="action-row">
        <view class="small-btn" @click="addBanner">新增一条</view>
        <view class="small-btn primary" @click="saveBanners">保存配置</view>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from "@/common/api";
import { getCurrentUser, logout } from "@/common/auth";

export default {
  data() {
    return {
      user: {},
      activeTab: "users",
      tabs: [
        { value: "users", label: "用户管理" },
        { value: "merchants", label: "商家审核" },
        { value: "products", label: "商品管理" },
        { value: "orders", label: "订单数据" },
        { value: "categories", label: "类目管理" },
        { value: "banners", label: "Banner管理" },
      ],
      dashboard: {},
      users: [],
      userKeyword: "",
      editingUserId: 0,
      userForm: {
        username: "",
        password: "",
        nickname: "",
        phone: "",
        role: "user",
        status: "active",
        merchantName: "",
      },
      roleOptions: [
        { value: "user", label: "普通用户" },
        { value: "merchant", label: "商家" },
        { value: "admin", label: "管理员" },
      ],
      statusOptions: [
        { value: "active", label: "启用" },
        { value: "disabled", label: "禁用" },
      ],
      merchants: [],
      products: [],
      orders: [],
      categories: [],
      categoryForm: {
        name: "",
        status: "active",
      },
      banners: [],
      uploadingBannerIndex: -1,
    };
  },
  async onShow() {
    this.user = getCurrentUser() || {};
    if (this.user.role !== "admin") {
      uni.reLaunch({ url: "/pages/login/index" });
      return;
    }
    await this.loadAll();
  },
  methods: {
    roleText(role) {
      const item = this.roleOptions.find((r) => r.value === role);
      return item ? item.label : role;
    },
    statusText(status) {
      const item = this.statusOptions.find((s) => s.value === status);
      return item ? item.label : status;
    },
    pickRole(event) {
      const current = this.roleOptions[event.detail.value];
      this.userForm.role = current.value;
    },
    pickStatus(event) {
      const current = this.statusOptions[event.detail.value];
      this.userForm.status = current.value;
    },
    async loadAll() {
      try {
        uni.showLoading({ title: "加载中" });
        await Promise.all([
          this.loadDashboard(),
          this.loadUsers(),
          this.loadMerchants(),
          this.loadProducts(),
          this.loadOrders(),
          this.loadCategories(),
          this.loadBanners(),
        ]);
      } catch (error) {
        uni.showToast({ title: error.message || "加载失败", icon: "none" });
      } finally {
        uni.hideLoading();
      }
    },
    async loadDashboard() {
      this.dashboard = await api.getAdminDashboard();
    },
    async loadUsers() {
      const res = await api.getAdminUsers({
        keyword: this.userKeyword || undefined,
        page: 1,
        pageSize: 200,
      });
      this.users = res.items || [];
    },
    editUser(item) {
      this.editingUserId = item.id;
      this.userForm = {
        username: item.username,
        password: "",
        nickname: item.nickname || "",
        phone: item.phone || "",
        role: item.role,
        status: item.status,
        merchantName: item.merchant_name || "",
      };
      this.activeTab = "users";
    },
    resetUserForm() {
      this.editingUserId = 0;
      this.userForm = {
        username: "",
        password: "",
        nickname: "",
        phone: "",
        role: "user",
        status: "active",
        merchantName: "",
      };
    },
    async submitUser() {
      if (!this.userForm.username) {
        uni.showToast({ title: "请输入账号", icon: "none" });
        return;
      }
      if (!this.editingUserId && !this.userForm.password) {
        uni.showToast({ title: "新增用户需要密码", icon: "none" });
        return;
      }
      const payload = {
        username: this.userForm.username,
        password: this.userForm.password,
        nickname: this.userForm.nickname,
        phone: this.userForm.phone,
        role: this.userForm.role,
        status: this.userForm.status,
        merchantName: this.userForm.merchantName,
      };
      try {
        if (this.editingUserId) {
          await api.updateAdminUser(this.editingUserId, payload);
          uni.showToast({ title: "用户已更新", icon: "success" });
        } else {
          await api.createAdminUser(payload);
          uni.showToast({ title: "用户已新增", icon: "success" });
        }
        this.resetUserForm();
        await Promise.all([this.loadUsers(), this.loadDashboard()]);
      } catch (error) {
        uni.showToast({ title: error.message || "操作失败", icon: "none" });
      }
    },
    disableUser(item) {
      uni.showModal({
        title: "确认禁用",
        content: `确认禁用用户 ${item.username} 吗？`,
        success: async (res) => {
          if (!res.confirm) {
            return;
          }
          try {
            await api.disableAdminUser(item.id);
            uni.showToast({ title: "已禁用", icon: "none" });
            await Promise.all([this.loadUsers(), this.loadDashboard()]);
          } catch (error) {
            uni.showToast({ title: error.message || "禁用失败", icon: "none" });
          }
        },
      });
    },
    async loadMerchants() {
      this.merchants = await api.getAdminMerchants();
    },
    async auditMerchant(merchantId, auditStatus) {
      try {
        await api.auditMerchant(merchantId, auditStatus);
        uni.showToast({ title: "审核成功", icon: "success" });
        await Promise.all([this.loadMerchants(), this.loadUsers(), this.loadDashboard()]);
      } catch (error) {
        uni.showToast({ title: error.message || "审核失败", icon: "none" });
      }
    },
    async loadProducts() {
      const res = await api.getAdminProducts({ page: 1, pageSize: 200 });
      this.products = res.items || [];
    },
    async toggleProduct(item) {
      const next = item.status === "on_sale" ? "off_sale" : "on_sale";
      try {
        await api.updateAdminProduct(item.id, { status: next });
        uni.showToast({ title: "商品状态已更新", icon: "success" });
        this.loadProducts();
      } catch (error) {
        uni.showToast({ title: error.message || "更新失败", icon: "none" });
      }
    },
    async disableProduct(item) {
      try {
        await api.disableAdminProduct(item.id);
        uni.showToast({ title: "商品已停用", icon: "none" });
        this.loadProducts();
      } catch (error) {
        uni.showToast({ title: error.message || "停用失败", icon: "none" });
      }
    },
    async loadOrders() {
      const res = await api.getAdminOrders({ page: 1, pageSize: 200 });
      this.orders = res.items || [];
    },
    async loadCategories() {
      this.categories = await api.getAdminCategories();
    },
    async saveCategory() {
      if (!this.categoryForm.name) {
        uni.showToast({ title: "请输入类目名称", icon: "none" });
        return;
      }
      try {
        await api.upsertAdminCategory(this.categoryForm);
        uni.showToast({ title: "类目已保存", icon: "success" });
        this.categoryForm = { name: "", status: "active" };
        this.loadCategories();
      } catch (error) {
        uni.showToast({ title: error.message || "保存失败", icon: "none" });
      }
    },
    async changeCategoryStatus(item) {
      try {
        await api.upsertAdminCategory({
          name: item.name,
          status: item.status === "active" ? "inactive" : "active",
        });
        this.loadCategories();
      } catch (error) {
        uni.showToast({ title: error.message || "更新失败", icon: "none" });
      }
    },
    async deleteCategory(item) {
      try {
        await api.deleteAdminCategory(item.id);
        uni.showToast({ title: "已删除", icon: "none" });
        this.loadCategories();
      } catch (error) {
        uni.showToast({ title: error.message || "删除失败", icon: "none" });
      }
    },
    async loadBanners() {
      const rows = await api.getAdminBanners();
      this.banners = (rows || []).map((item) => ({
        title: item.title || "",
        image: item.image || "",
        link: item.link || "/pages/index/index",
        sort: item.sort || 1,
        enabled: !!item.enabled,
      }));
      if (!this.banners.length) {
        this.addBanner();
      }
    },
    addBanner() {
      this.banners.push({
        title: "",
        image: "",
        link: "/pages/index/index",
        sort: this.banners.length + 1,
        enabled: true,
      });
    },
    removeBanner(index) {
      this.banners.splice(index, 1);
      if (!this.banners.length) {
        this.addBanner();
      }
    },
    uploadBannerImage(index) {
      if (this.uploadingBannerIndex !== -1) {
        return;
      }
      uni.chooseImage({
        count: 1,
        sizeType: ["compressed"],
        sourceType: ["album", "camera"],
        success: async (res) => {
          const filePath = (res.tempFilePaths || [])[0];
          if (!filePath) {
            return;
          }
          this.uploadingBannerIndex = index;
          try {
            const uploaded = await api.uploadImage(filePath);
            if (this.banners[index]) {
              this.banners[index].image = uploaded.url || "";
            }
            uni.showToast({ title: "上传成功", icon: "success" });
          } catch (error) {
            uni.showToast({ title: error.message || "上传失败", icon: "none" });
          } finally {
            this.uploadingBannerIndex = -1;
          }
        },
      });
    },
    async saveBanners() {
      const payload = this.banners.map((item, index) => ({
        ...item,
        sort: index + 1,
      }));
      const invalidIndex = payload.findIndex((item) => !String(item.image || "").trim());
      if (invalidIndex >= 0) {
        uni.showToast({
          title: `第 ${invalidIndex + 1} 条 Banner 缺少图片`,
          icon: "none",
        });
        return;
      }
      try {
        await api.configAdminBanners({ banners: payload });
        uni.showToast({ title: "Banner 已保存", icon: "success" });
        this.loadBanners();
      } catch (error) {
        uni.showToast({ title: error.message || "保存失败", icon: "none" });
      }
    },
    handleLogout() {
      logout();
      uni.reLaunch({ url: "/pages/login/index" });
    },
  },
};
</script>

<style>
.page {
  min-height: 100vh;
  background: linear-gradient(180deg, #edf3fb 0%, #e8eff9 100%);
  padding: 20rpx;
}

.hero {
  background: linear-gradient(130deg, #162f56 0%, #244f8d 100%);
  border-radius: 18rpx;
  padding: 24rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.hero-title {
  display: block;
  color: #ffffff;
  font-size: 34rpx;
  font-weight: 700;
}

.hero-sub {
  margin-top: 10rpx;
  display: block;
  color: rgba(255, 255, 255, 0.88);
  font-size: 22rpx;
}

.logout-btn {
  min-width: 130rpx;
  height: 60rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.15);
  border: 1rpx solid rgba(255, 255, 255, 0.35);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 23rpx;
}

.metrics {
  margin-top: 16rpx;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12rpx;
}

.metric-card {
  background: #ffffff;
  border-radius: 14rpx;
  padding: 16rpx;
}

.metric-num {
  display: block;
  color: #1a4d89;
  font-size: 32rpx;
  font-weight: 700;
}

.metric-label {
  margin-top: 6rpx;
  display: block;
  color: #6f84a1;
  font-size: 22rpx;
}

.tab-scroll {
  margin-top: 16rpx;
  white-space: nowrap;
}

.tab-row {
  display: inline-flex;
  gap: 10rpx;
}

.tab-item {
  padding: 10rpx 20rpx;
  border-radius: 999rpx;
  background: #dfe9f8;
  color: #3f5f88;
  font-size: 23rpx;
}

.tab-item.active {
  color: #ffffff;
  background: linear-gradient(130deg, #1b74f7 0%, #2f95ff 100%);
}

.panel {
  margin-top: 14rpx;
  background: #ffffff;
  border-radius: 16rpx;
  padding: 18rpx;
}

.panel-title {
  display: block;
  color: #1b3455;
  font-size: 28rpx;
  font-weight: 700;
}

.search-row {
  margin-top: 12rpx;
  display: flex;
  gap: 10rpx;
  align-items: center;
}

.search-input {
  flex: 1;
  height: 68rpx;
  border-radius: 12rpx;
  background: #f1f5fb;
  padding: 0 14rpx;
  font-size: 24rpx;
}

.small-btn {
  min-width: 110rpx;
  height: 60rpx;
  border-radius: 10rpx;
  background: #e8f0fb;
  color: #3b5e8d;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22rpx;
}

.small-btn.primary {
  color: #ffffff;
  background: linear-gradient(130deg, #1b74f7 0%, #2f95ff 100%);
}

.small-btn.warning {
  background: #fff2df;
  color: #cb7c26;
}

.small-btn.danger {
  background: #ffecef;
  color: #cc425b;
}

.form-grid {
  margin-top: 12rpx;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10rpx;
}

.field {
  height: 66rpx;
  border-radius: 10rpx;
  background: #f3f7fc;
  padding: 0 12rpx;
  font-size: 23rpx;
  color: #29486e;
  display: flex;
  align-items: center;
}

.picker {
  justify-content: flex-start;
}

.action-row {
  margin-top: 12rpx;
  display: flex;
  gap: 10rpx;
  flex-wrap: wrap;
}

.list-item {
  margin-top: 12rpx;
  border-radius: 12rpx;
  background: #f6f9fd;
  padding: 12rpx;
}

.item-title {
  display: block;
  font-size: 25rpx;
  color: #1f385c;
  font-weight: 600;
}

.item-sub {
  display: block;
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #69809e;
}

.item-actions {
  margin-top: 10rpx;
  display: flex;
  gap: 8rpx;
  flex-wrap: wrap;
}

.banner-form {
  margin-top: 12rpx;
  border-radius: 12rpx;
  padding: 12rpx;
  background: #f6f9fd;
}

.banner-preview {
  width: 100%;
  height: 180rpx;
  margin-top: 10rpx;
  border-radius: 10rpx;
}
</style>
