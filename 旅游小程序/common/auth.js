import { request } from "./request";

export async function loginByAccount(payload = {}) {
  const profile = await request({
    url: "/auth/login",
    method: "POST",
    auth: false,
    data: payload,
  });
  uni.setStorageSync("token", profile.token);
  uni.setStorageSync("user", profile.user);
  uni.setStorageSync("merchant", profile.merchant || null);
  return profile;
}

export function getCurrentUser() {
  return uni.getStorageSync("user") || null;
}

export function hasLogin() {
  return Boolean(uni.getStorageSync("token"));
}

export function logout() {
  uni.removeStorageSync("token");
  uni.removeStorageSync("user");
  uni.removeStorageSync("merchant");
}
