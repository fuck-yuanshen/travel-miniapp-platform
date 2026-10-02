<template>
  <view class="page">
    <swiper class="banner-swiper" autoplay circular indicator-dots>
      <swiper-item v-for="banner in banners" :key="banner.id + '-' + banner.image">
        <image :src="banner.image" class="banner-img" mode="aspectFill"></image>
      </swiper-item>
    </swiper>

    <view class="search-wrap card-shadow">
      <input v-model="keyword" class="search-input" placeholder="搜索目的地/标签" />
      <view class="search-btn" @click="loadProducts">搜索</view>
    </view>

    <scroll-view class="category-scroll" scroll-x>
      <view class="category-inner">
        <view
          v-for="item in categories"
          :key="item.id"
          class="category-item"
          :class="{ active: selectedCategoryId === item.id }"
          @click="handleCategory(item.id)"
        >
          {{ item.name }}
        </view>
        <view class="category-item" :class="{ active: selectedCategoryId === 0 }" @click="handleCategory(0)">
          全部
        </view>
      </view>
    </scroll-view>

    <view class="product-list">
      <view class="product-card card-shadow" v-for="item in products" :key="item.id" @click="goDetail(item.id)">
        <image :src="item.cover" class="cover" mode="aspectFill"></image>
        <view class="product-main">
          <text class="product-title text-ellipsis">{{ item.title }}</text>
          <text class="product-meta">{{ item.category_name || "未分类" }} · {{ item.depart_city || "-" }}</text>
          <view class="tag-wrap">
            <text class="tag" v-for="tag in item.tags.slice(0, 3)" :key="tag">{{ tag }}</text>
          </view>
          <view class="price-row">
            <text class="price">¥{{ item.min_price }}</text>
            <text class="stock">库存 {{ item.total_stock }}</text>
          </view>
        </view>
      </view>
      <view class="empty-state" v-if="products.length === 0">
        暂无匹配商品，请调整筛选条件
      </view>
    </view>
  </view>
</template>

<script>
import { getCurrentUser, hasLogin } from "@/common/auth";
import { api } from "@/common/api";

export default {
  data() {
    return {
      user: {},
      keyword: "",
      products: [],
      banners: [],
      categories: [],
      selectedCategoryId: 0,
    };
  },
  onShow() {
    if (!hasLogin()) {
      uni.reLaunch({ url: "/pages/login/index" });
      return;
    }
    this.user = getCurrentUser() || {};
    if (this.user.role === "admin") {
      uni.reLaunch({ url: "/pages/admin/index" });
      return;
    }
    if (this.user.role === "merchant") {
      uni.reLaunch({ url: "/pages/merchant/dashboard" });
      return;
    }
    this.loadBanners();
    this.loadCategories();
    this.loadProducts();
  },
  methods: {
    async loadBanners() {
      try {
        const list = await api.getBanners();
        this.banners = (list || []).map((item) => ({
          ...item,
          image: this.withCacheBust(item.image, item.updated_at),
        }));
      } catch (error) {
        this.banners = [];
      }
    },
    withCacheBust(url, stamp) {
      if (!url) {
        return "";
      }
      const t = encodeURIComponent(stamp || Date.now());
      return url.includes("?") ? `${url}&_t=${t}` : `${url}?_t=${t}`;
    },
    async loadCategories() {
      try {
        this.categories = await api.getCategories();
      } catch (error) {
        this.categories = [];
      }
    },
    async loadProducts() {
      try {
        uni.showLoading({ title: "加载中" });
        const params = {
          keyword: this.keyword,
          page: 1,
          pageSize: 20,
        };
        if (this.selectedCategoryId) {
          params.categoryId = this.selectedCategoryId;
        }
        const res = await api.getProducts(params);
        this.products = res.items || [];
      } catch (error) {
        uni.showToast({
          title: error.message || "加载失败",
          icon: "none",
        });
      } finally {
        uni.hideLoading();
      }
    },
    handleCategory(categoryId) {
      this.selectedCategoryId = categoryId;
      this.loadProducts();
    },
    goDetail(productId) {
      uni.navigateTo({
        url: `/pages/product/detail?id=${productId}`,
      });
    },
  },
};
</script>

<style>
.page {
  min-height: 100vh;
  background: linear-gradient(180deg, #f1f6fd 0%, #edf3fb 60%, #f4f8fd 100%);
  padding: 24rpx;
}

.banner-swiper {
  margin-top: 0;
  height: 280rpx;
  border-radius: 18rpx;
  overflow: hidden;
}

.banner-img {
  width: 100%;
  height: 100%;
}

.search-wrap {
  margin-top: 22rpx;
  display: flex;
  gap: 12rpx;
  background: #ffffff;
  border-radius: 16rpx;
  padding: 10rpx;
}

.search-input {
  flex: 1;
  height: 68rpx;
  border-radius: 12rpx;
  background: #f4f7fb;
  padding: 0 22rpx;
}

.search-btn {
  width: 132rpx;
  height: 68rpx;
  border-radius: 12rpx;
  color: #ffffff;
  background: linear-gradient(130deg, #1b75f8 0%, #2f95ff 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  font-weight: 600;
}

.category-scroll {
  margin-top: 16rpx;
  white-space: nowrap;
}

.category-inner {
  display: inline-flex;
  gap: 12rpx;
}

.category-item {
  padding: 12rpx 22rpx;
  border-radius: 999rpx;
  font-size: 24rpx;
  background: #eaf2ff;
  color: #3f5d84;
}

.category-item.active {
  background: #2b7fff;
  color: #ffffff;
}

.product-list {
  margin-top: 18rpx;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.product-card {
  background: #ffffff;
  border-radius: 18rpx;
  overflow: hidden;
  border: 1rpx solid #e9eff8;
}

.cover {
  width: 100%;
  height: 260rpx;
}

.product-main {
  padding: 18rpx;
}

.product-title {
  display: block;
  font-size: 30rpx;
  color: #172a43;
  font-weight: 600;
  max-width: 100%;
}

.product-meta {
  margin-top: 8rpx;
  display: block;
  color: #6b7f99;
  font-size: 22rpx;
}

.tag-wrap {
  margin-top: 10rpx;
  display: flex;
  gap: 10rpx;
}

.tag {
  padding: 4rpx 10rpx;
  border-radius: 10rpx;
  background: #eef5ff;
  color: #4b6e98;
  font-size: 20rpx;
}

.price-row {
  margin-top: 14rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.price {
  color: #eb5a2f;
  font-size: 34rpx;
  font-weight: 700;
}

.stock {
  color: #7b8fa8;
  font-size: 22rpx;
}

.empty-state {
  margin-top: 40rpx;
  text-align: center;
  color: #8093ac;
  font-size: 24rpx;
}
</style>
