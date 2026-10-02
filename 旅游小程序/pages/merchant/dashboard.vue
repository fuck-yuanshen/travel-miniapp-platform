<template>
  <view class="page">
    <view class="hero card-shadow">
      <text class="hero-title">商家运营中心</text>
      <text class="hero-sub">管理商品信息和上下架，评论请切换到底部“评论”页</text>
    </view>

    <view class="card card-shadow">
      <text class="title">经营看板</text>
      <view class="stats">
        <view class="stat">
          <text class="num">{{ dashboard.totalOrders || 0 }}</text>
          <text class="label">订单总数</text>
        </view>
        <view class="stat">
          <text class="num">¥{{ dashboard.gmv || 0 }}</text>
          <text class="label">GMV</text>
        </view>
        <view class="stat">
          <text class="num">{{ dashboard.refundRate || 0 }}</text>
          <text class="label">退款率</text>
        </view>
      </view>
    </view>

    <view class="card card-shadow">
      <view class="title-row">
        <text class="title">{{ editingProductId ? "编辑商品" : "发布商品" }}</text>
        <text class="edit-tip" v-if="editingProductId">当前编辑：#{{ editingProductId }}</text>
      </view>

      <view class="type-switch">
        <view class="type-pill" :class="{ active: form.publishType === 'travel' }" @click="setPublishType('travel')">旅游商品</view>
        <view class="type-pill" :class="{ active: form.publishType === 'normal' }" @click="setPublishType('normal')">普通商品</view>
      </view>

      <view class="cover-box" @click="chooseCover">
        <image v-if="form.cover" :src="form.cover" class="cover-preview" mode="aspectFill"></image>
        <view class="cover-placeholder" v-else>
          <text class="cover-main">点击上传封面图</text>
          <text class="cover-sub">支持 jpg / jpeg / png / webp</text>
        </view>
      </view>
      <button class="upload-btn" :loading="uploading" @click="chooseCover">{{ uploading ? "上传中..." : "上传/更换封面" }}</button>

      <picker v-if="form.publishType === 'travel'" class="picker-wrap" :range="categories" range-key="name" @change="onCategoryChange">
        <view class="picker">{{ selectedCategoryName || "请选择商品分类" }}</view>
      </picker>

      <input v-model.trim="form.title" :placeholder="form.publishType === 'normal' ? '商品标题（选填）' : '商品标题（必填）'" class="input" />
      <input v-model="form.basePrice" placeholder="基础价格（必填）" type="number" class="input" />
      <input v-if="form.publishType === 'travel'" v-model.trim="form.departCity" placeholder="出发地（如：上海）" class="input" />
      <input v-if="form.publishType === 'travel'" v-model.trim="form.tagText" placeholder="标签，多个用逗号分隔" class="input" />
      <textarea
        v-model.trim="form.detail"
        class="textarea"
        :placeholder="form.publishType === 'normal' ? '商品信息（必填）' : '商品详情说明（可选）'"
      ></textarea>

      <view class="form-actions">
        <button class="submit-btn" @click="submitProduct">{{ editingProductId ? "保存修改" : "发布商品" }}</button>
        <button class="cancel-btn" v-if="editingProductId" @click="cancelEdit">取消编辑</button>
      </view>
    </view>

    <view class="card card-shadow">
      <text class="title">我的商品</text>
      <view class="product-item" v-for="item in products" :key="item.id">
        <image class="product-cover" :src="item.cover || defaultCover" mode="aspectFill"></image>
        <view class="product-main">
          <text class="name text-ellipsis">{{ item.title }}</text>
          <text class="meta">¥{{ item.base_price }} · {{ item.status === "on_sale" ? "在售" : "已下架" }}</text>
          <text class="meta">分类：{{ displayCategory(item) }} · 出发地：{{ item.depart_city || "-" }}</text>
        </view>
        <view class="product-actions">
          <button size="mini" class="mini-btn" @click="startEdit(item)">编辑</button>
          <button size="mini" class="mini-btn" @click="toggleStatus(item)">
            {{ item.status === "on_sale" ? "下架" : "上架" }}
          </button>
          <button size="mini" class="mini-btn danger" @click="deleteProduct(item)">删除</button>
        </view>
      </view>
      <view class="empty" v-if="products.length === 0">暂无商品，请先发布一个商品</view>
    </view>

    <view class="merchant-tabbar">
      <view class="merchant-tab active">
        <text class="tab-label">首页</text>
      </view>
      <view class="merchant-tab" @click="goReviewPage">
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
      dashboard: {},
      products: [],
      categories: [],
      editingProductId: 0,
      uploading: false,
      defaultCover: "https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=900&q=80",
      form: {
        publishType: "travel",
        title: "",
        basePrice: "",
        departCity: "",
        tagText: "",
        detail: "",
        categoryId: "",
        cover: "",
      },
    };
  },
  computed: {
    selectedCategoryName() {
      const found = this.categories.find((item) => item.id === this.form.categoryId);
      return found ? found.name : "";
    },
  },
  onShow() {
    this.user = getCurrentUser() || {};
    if (this.user.role !== "merchant") {
      uni.showToast({ title: "无权限访问商家页", icon: "none" });
      return;
    }
    this.loadAll();
  },
  methods: {
    async loadAll() {
      try {
        uni.showLoading({ title: "加载中" });
        const [dashboard, products, categories] = await Promise.all([
          api.getMerchantDashboard(),
          api.getMerchantProducts(),
          api.getCategories(),
        ]);
        this.dashboard = dashboard || {};
        this.products = products || [];
        this.categories = categories || [];
      } catch (error) {
        uni.showToast({
          title: error.message || "加载失败",
          icon: "none",
        });
      } finally {
        uni.hideLoading();
      }
    },
    setPublishType(type) {
      this.form.publishType = type;
      if (type === "normal") {
        this.form.categoryId = "";
        this.form.departCity = "";
      }
    },
    resetForm() {
      this.form = {
        publishType: "travel",
        title: "",
        basePrice: "",
        departCity: "",
        tagText: "",
        detail: "",
        categoryId: "",
        cover: "",
      };
      this.editingProductId = 0;
    },
    displayCategory(item) {
      if (item.category_name) {
        return item.category_name;
      }
      const tags = item.tags || [];
      if (tags.includes("普通商品")) {
        return "普通商品";
      }
      return "未分类";
    },
    onCategoryChange(event) {
      const index = Number(event.detail.value || 0);
      const item = this.categories[index];
      this.form.categoryId = item ? item.id : "";
    },
    chooseCover() {
      if (this.uploading) {
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
          this.uploading = true;
          try {
            const uploaded = await api.uploadImage(filePath);
            this.form.cover = uploaded.url;
            uni.showToast({ title: "上传成功", icon: "success" });
          } catch (error) {
            uni.showToast({
              title: error.message || "上传失败",
              icon: "none",
            });
          } finally {
            this.uploading = false;
          }
        },
      });
    },
    startEdit(item) {
      const tags = item.tags || [];
      const isNormal = !item.category_id && tags.includes("普通商品");
      this.editingProductId = item.id;
      this.form = {
        publishType: isNormal ? "normal" : "travel",
        title: item.title || "",
        basePrice: String(item.base_price || ""),
        departCity: item.depart_city || "",
        tagText: (isNormal ? tags.filter((t) => t !== "普通商品") : tags).join(","),
        detail: item.detail || "",
        categoryId: item.category_id || "",
        cover: item.cover || "",
      };
      uni.pageScrollTo({ scrollTop: 0, duration: 200 });
    },
    cancelEdit() {
      this.resetForm();
    },
    async submitProduct() {
      const isNormal = this.form.publishType === "normal";
      if (!this.form.basePrice) {
        uni.showToast({ title: "请填写价格", icon: "none" });
        return;
      }
      if (!this.form.cover) {
        uni.showToast({ title: "请先上传封面图", icon: "none" });
        return;
      }
      if (!isNormal && !this.form.title) {
        uni.showToast({ title: "请填写商品标题", icon: "none" });
        return;
      }
      if (isNormal && !this.form.detail) {
        uni.showToast({ title: "请填写商品信息", icon: "none" });
        return;
      }
      if (!isNormal && !this.form.categoryId) {
        uni.showToast({ title: "请选择商品分类", icon: "none" });
        return;
      }

      const tags = this.form.tagText
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);

      if (isNormal && !tags.includes("普通商品")) {
        tags.unshift("普通商品");
      }

      const payload = {
        title: this.form.title || `普通商品-${Date.now().toString().slice(-6)}`,
        basePrice: Number(this.form.basePrice),
        categoryId: isNormal ? null : this.form.categoryId,
        cover: this.form.cover,
        detail: this.form.detail,
        departCity: isNormal ? "" : this.form.departCity,
        tags,
      };

      try {
        if (this.editingProductId) {
          await api.updateMerchantProduct(this.editingProductId, payload);
          uni.showToast({ title: "修改成功", icon: "success" });
        } else {
          await api.createMerchantProduct({
            ...payload,
            calendar: [],
          });
          uni.showToast({ title: "发布成功", icon: "success" });
        }
        this.resetForm();
        await this.loadAll();
      } catch (error) {
        uni.showToast({
          title: error.message || (this.editingProductId ? "修改失败" : "发布失败"),
          icon: "none",
        });
      }
    },
    async toggleStatus(item) {
      const target = item.status === "on_sale" ? "off_sale" : "on_sale";
      try {
        await api.updateMerchantProduct(item.id, {
          status: target,
        });
        uni.showToast({ title: "已更新", icon: "success" });
        await this.loadAll();
      } catch (error) {
        uni.showToast({ title: error.message || "更新失败", icon: "none" });
      }
    },
    deleteProduct(item) {
      uni.showModal({
        title: "删除商品",
        content: `确认删除商品【${item.title}】吗？删除后不可恢复。`,
        success: async (res) => {
          if (!res.confirm) {
            return;
          }
          try {
            await api.deleteMerchantProduct(item.id);
            uni.showToast({ title: "删除成功", icon: "success" });
            if (this.editingProductId === item.id) {
              this.resetForm();
            }
            await this.loadAll();
          } catch (error) {
            uni.showToast({
              title: error.message || "删除失败",
              icon: "none",
            });
          }
        },
      });
    },
    goReviewPage() {
      uni.redirectTo({ url: "/pages/merchant/reviews" });
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

.title {
  display: block;
  font-size: 28rpx;
  font-weight: 700;
  color: #182f4e;
}

.title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.edit-tip {
  color: #56769d;
  font-size: 22rpx;
}

.type-switch {
  margin-top: 12rpx;
  display: flex;
  gap: 10rpx;
}

.type-pill {
  flex: 1;
  text-align: center;
  background: #edf3fd;
  color: #466080;
  border-radius: 999rpx;
  padding: 12rpx 0;
  font-size: 24rpx;
}

.type-pill.active {
  background: #1d74f7;
  color: #ffffff;
  font-weight: 700;
}

.stats {
  margin-top: 12rpx;
  display: flex;
  gap: 16rpx;
}

.stat {
  flex: 1;
  background: linear-gradient(180deg, #edf4ff 0%, #f5f8ff 100%);
  border-radius: 12rpx;
  padding: 14rpx;
}

.num {
  display: block;
  font-size: 28rpx;
  color: #1459c2;
  font-weight: 700;
}

.label {
  margin-top: 6rpx;
  display: block;
  font-size: 22rpx;
  color: #5f7494;
}

.cover-box {
  margin-top: 12rpx;
  height: 260rpx;
  border-radius: 14rpx;
  overflow: hidden;
  background: #f4f7fb;
}

.cover-preview {
  width: 100%;
  height: 100%;
}

.cover-placeholder {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.cover-main {
  font-size: 28rpx;
  color: #30506f;
  font-weight: 600;
}

.cover-sub {
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #7790ad;
}

.upload-btn {
  margin-top: 12rpx;
  border-radius: 12rpx;
  background: #edf4ff;
  color: #205cbe;
  border: 1rpx solid #d7e6fb;
  font-size: 25rpx;
}

.picker-wrap {
  margin-top: 12rpx;
}

.picker {
  height: 72rpx;
  background: #f4f7fb;
  border-radius: 12rpx;
  padding: 0 14rpx;
  display: flex;
  align-items: center;
  color: #2f4b6c;
  font-size: 25rpx;
}

.input {
  margin-top: 12rpx;
  height: 72rpx;
  background: #f4f7fb;
  border-radius: 12rpx;
  padding: 0 14rpx;
}

.textarea {
  margin-top: 12rpx;
  background: #f4f7fb;
  border-radius: 12rpx;
  padding: 14rpx;
  min-height: 160rpx;
  width: 100%;
  box-sizing: border-box;
}

.form-actions {
  margin-top: 14rpx;
  display: flex;
  gap: 12rpx;
}

.submit-btn,
.cancel-btn {
  flex: 1;
  border-radius: 12rpx;
  font-size: 27rpx;
}

.submit-btn {
  border: 0;
  background: linear-gradient(130deg, #1b75f8 0%, #2f95ff 100%);
  color: #ffffff;
  font-weight: 600;
}

.cancel-btn {
  background: #f0f4fa;
  color: #4e6888;
  border: 1rpx solid #dde6f3;
}

.product-item {
  margin-top: 12rpx;
  padding: 12rpx;
  border-radius: 12rpx;
  background: #f7f9fd;
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.product-cover {
  width: 120rpx;
  height: 120rpx;
  border-radius: 10rpx;
  flex-shrink: 0;
}

.product-main {
  flex: 1;
}

.name {
  display: block;
  font-size: 26rpx;
  color: #213855;
  max-width: 340rpx;
}

.meta {
  margin-top: 6rpx;
  display: block;
  font-size: 22rpx;
  color: #6f85a2;
}

.product-actions {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.mini-btn {
  background: #e8f1ff;
  color: #1d68cc;
  border: 1rpx solid #ccdefa;
}

.mini-btn.danger {
  background: #ffecee;
  color: #d64056;
  border: 1rpx solid #ffd2d8;
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
