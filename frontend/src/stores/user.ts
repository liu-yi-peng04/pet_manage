import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { authApi } from "@/api/auth";
import { kbApi } from "@/api/knowledge";
import { docApi } from "@/api/document";
import type { UserInfo } from "@/types";
import { useChatStore } from "@/stores/chat";

export const useUserStore = defineStore("user", () => {
  const token = ref<string>(localStorage.getItem("token") ?? "");
  const username = ref<string>(localStorage.getItem("username") ?? "");
  const userInfo = ref<UserInfo | null>(null);

  const isLoggedIn = () => !!token.value;
  const isAdmin = computed(() => userInfo.value?.role === "admin");
  // 宠物店店员（含店主）；需绑定门店
  const isStaff = computed(() => userInfo.value?.role === "staff" && !!userInfo.value?.store_id);
  // 店主
  const isStoreManager = computed(() => isStaff.value && userInfo.value?.staff_role === "manager");
  const isOperator = computed(() => userInfo.value?.role === "operator");
  const isTrainer = computed(() => userInfo.value?.role === "trainer");
  const isEndUser = computed(() => userInfo.value?.role === "user");

  function homePath() {
    const r = userInfo.value?.role;
    if (r === "admin") return "/dashboard";
    if (r === "staff") return "/workspace";
    if (r === "operator") return "/operator";
    if (r === "trainer") return "/trainers";
    return "/home";
  }

  async function login(usernameVal: string, passwordVal: string) {
    const res = await authApi.login({ username: usernameVal, password: passwordVal });
    token.value = res.access_token;
    username.value = usernameVal;
    localStorage.setItem("token", res.access_token);
    localStorage.setItem("username", usernameVal);
    await fetchMe();
  }

  async function register(data: { username: string; email: string; password: string; role?: string }) {
    await authApi.register(data);
    await login(data.username, data.password);
  }

  async function fetchMe() {
    userInfo.value = await authApi.me();
    // 绑定本端 AI 会话通道，避免与其它角色/账号串话
    useChatStore().bindIdentity(userInfo.value?.id ?? null, userInfo.value?.role);
  }

  async function changePassword(oldPwd: string, newPwd: string) {
    await authApi.changePassword(oldPwd, newPwd);
  }

  function logout() {
    useChatStore().resetSession();
    token.value = "";
    username.value = "";
    userInfo.value = null;
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    window.location.href = "/login";
  }

  // 预取侧栏计数等
  const dashStats = ref({ kb: 0, doc: 0 });
  async function refreshCounts() {
    try {
      const kbs = await kbApi.list();
      dashStats.value.kb = kbs.length;
      const docs = await docApi.listAll();
      dashStats.value.doc = docs.length;
    } catch {
      /* ignore */
    }
  }

  return {
    token,
    username,
    userInfo,
    isAdmin,
    isStaff,
    isStoreManager,
    isOperator,
    isTrainer,
    isEndUser,
    homePath,
    isLoggedIn,
    login,
    register,
    fetchMe,
    changePassword,
    logout,
    dashStats,
    refreshCounts,
  };
});
