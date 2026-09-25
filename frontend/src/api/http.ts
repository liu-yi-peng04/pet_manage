import axios, { type AxiosInstance } from "axios";
import { ElMessage } from "element-plus";
import router from "@/router";

const instance: AxiosInstance = axios.create({
  baseURL: "/api",
  timeout: 120000,
});

// 请求拦截：注入 JWT
instance.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截：统一错误处理 + 401 跳登录
instance.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const status = err?.response?.status;
    const detail = err?.response?.data?.detail;
    if (status === 401) {
      localStorage.removeItem("token");
      localStorage.removeItem("username");
      ElMessage.error("登录状态已过期，请重新登录");
      router.push("/login");
    } else {
      const msg = typeof detail === "string" ? detail : (err?.message ?? "请求失败");
      ElMessage.error(msg);
    }
    return Promise.reject(err);
  }
);

export default instance;