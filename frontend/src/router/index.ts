import { createRouter, createWebHistory } from "vue-router";
import { useUserStore } from "@/stores/user";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "login",
      component: () => import("@/views/LoginView.vue"),
      meta: { public: true, title: "登录" },
    },
    {
      path: "/",
      component: () => import("@/layout/AppLayout.vue"),
      redirect: "/home",
      children: [
        {
          path: "home",
          name: "home",
          component: () => import("@/views/HomeView.vue"),
          meta: { title: "首页", requireUser: true },
        },
        {
          path: "dashboard",
          name: "dashboard",
          component: () => import("@/views/DashboardView.vue"),
          meta: { title: "工作台", requireAdmin: true },
        },
        {
          path: "kb",
          name: "kb",
          component: () => import("@/views/KBListView.vue"),
          meta: { title: "知识库", requireAdmin: true },
        },
        {
          path: "kb/:id/documents",
          name: "kb-documents",
          component: () => import("@/views/DocumentView.vue"),
          meta: { title: "文档管理", requireAdmin: true },
        },
        {
          path: "chat",
          name: "chat",
          component: () => import("@/views/ChatView.vue"),
          meta: { title: "AI 顾问" },
        },
        {
          path: "pets",
          name: "pets",
          component: () => import("@/views/PetListView.vue"),
          meta: { title: "我的宠物" },
        },
        {
          path: "pets/:id",
          name: "pet-detail",
          component: () => import("@/views/PetDetailView.vue"),
          meta: { title: "宠物详情" },
        },
        {
          path: "listings",
          name: "listings",
          component: () => import("@/views/MarketplaceView.vue"),
          meta: { title: "选宠市场" },
        },
        {
          path: "trainers",
          name: "trainers",
          component: () => import("@/views/TrainersView.vue"),
          meta: { title: "训犬师" },
        },
        {
          path: "orders",
          name: "orders",
          component: () => import("@/views/OrdersView.vue"),
          meta: { title: "我的订单" },
        },
        {
          path: "operator",
          name: "operator",
          component: () => import("@/views/OperatorView.vue"),
          meta: { title: "运营台", requireOperator: true },
        },
        {
          path: "store",
          name: "store",
          component: () => import("@/views/StoreView.vue"),
          meta: { title: "宠物商城" },
        },
        {
          path: "booking",
          name: "booking",
          component: () => import("@/views/BookingView.vue"),
          meta: { title: "预约寄养" },
        },
        {
          path: "workspace",
          name: "workspace",
          component: () => import("@/views/WorkspaceView.vue"),
          meta: { title: "宠物店工作台" },
        },
        {
          path: "profile",
          name: "profile",
          component: () => import("@/views/ProfileView.vue"),
          meta: { title: "个人中心" },
        },
      ],
    },
    { path: "/:pathMatch(.*)*", redirect: "/chat" },
  ],
});

// 全局守卫：先验证本地 token 是否真实有效，再决定放行/踢回登录，避免「过期 token 卡登录页死循环」
router.beforeEach(async (to) => {
  const token = localStorage.getItem("token");

  // 登录/注册等公开页：有 token 就验证一下，有效则进主站，无效则清掉 token 停在登录页
  if (to.meta.public) {
    if (!token) return true;
    const userStore = useUserStore();
    if (!userStore.userInfo) {
      try {
        await userStore.fetchMe();
      } catch {
        // token 已失效：清除本地残留，停在本页（登录页）而不是被弹来弹去
        localStorage.removeItem("token");
        localStorage.removeItem("username");
        return true;
      }
    }
    return { path: userStore.homePath() };
  }

  // 受保护页：无 token → 登录
  if (!token) {
    return { path: "/login" };
  }
  const userStore = useUserStore();
  if (!userStore.userInfo) {
    try {
      await userStore.fetchMe();
    } catch {
      userStore.logout();
      return { path: "/login" };
    }
  }
  // 工作台 / 知识库管理仅超管可访问，其余角色回到默认页
  if (to.meta.requireAdmin && userStore.userInfo?.role !== "admin") {
    return { path: userStore.homePath() };
  }
  if (to.meta.requireUser && userStore.userInfo?.role !== "user") {
    return { path: userStore.homePath() };
  }
  if (to.meta.requireOperator && userStore.userInfo?.role !== "operator" && userStore.userInfo?.role !== "admin") {
    return { path: userStore.homePath() };
  }
  if (to.path === "/workspace" && userStore.userInfo?.role !== "staff" && userStore.userInfo?.role !== "admin") {
    return { path: userStore.homePath() };
  }
  // 养宠用户专属：我的宠物 / 预约到店（商家只接收预约，不发起）
  const userOnly = ["/pets", "/booking", "/orders"];
  if (userOnly.some((p) => to.path === p || to.path.startsWith(p + "/"))) {
    const role = userStore.userInfo?.role;
    if (role && role !== "user") {
      return { path: userStore.homePath() };
    }
  }
  // 选宠市场仅用户逛；商家在工作台管理待售
  if (to.path === "/listings" && userStore.userInfo?.role === "staff") {
    return { path: "/workspace" };
  }
  document.title = `${(to.meta.title as string) || ""} · 宠智联`;
  return true;
});

export default router;