import config from "./config";

export function request(options) {
  const {
    url,
    method = "GET",
    data = {},
    auth = true,
    headers = {},
  } = options;

  return new Promise((resolve, reject) => {
    const token = uni.getStorageSync("token");
    const finalHeaders = {
      "Content-Type": "application/json; charset=utf-8",
      "Accept-Charset": "utf-8",
      ...headers,
    };
    if (auth && token) {
      finalHeaders.Authorization = `Bearer ${token}`;
    }

    uni.request({
      url: `${config.BASE_URL}${url}`,
      method,
      data,
      header: finalHeaders,
      success: (res) => {
        const body = res.data || {};
        if (res.statusCode >= 200 && res.statusCode < 300 && body.code === 0) {
          resolve(body.data);
          return;
        }
        const message = body.message || `请求失败(${res.statusCode})`;
        reject(new Error(message));
      },
      fail: (err) => reject(err),
    });
  });
}
