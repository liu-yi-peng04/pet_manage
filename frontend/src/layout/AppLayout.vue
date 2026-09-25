<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useAppStore } from "@/stores/app";
import { useUserStore } from "@/stores/user";

const appStore = useAppStore();
const userStore = useUserStore();
const router = useRouter();

const activeRoute = computed(() => router.currentRoute.value.path);

// 养宠用户菜单
const userMenu = [
  { path: "/home", label: "首页", icon: "HomeFilled" },
  { path: "/chat", label: "AI 顾问", icon: "ChatDotRound" },
  { path: "/listings", label: "选宠市场", icon: "Present" },
  { path: "/store", label: "用品商城", icon: "ShoppingBag" },
  { path: "/booking", label: "预约到店", icon: "Calendar" },
  { path: "/pets", label: "我的宠物", icon: "BellFilled" },
  { path: "/orders", label: "我的订单", icon: "List" },
  { path: "/trainers", label: "训犬师", icon: "Trophy" },
  { path: "/profile", label: "个人中心", icon: "User" },
];

const adminMenu = [
  { path: "/dashboard", label: "平台工作台", icon: "DataBoard" },
  { path: "/kb", label: "知识库", icon: "FolderOpened" },
  { path: "/operator", label: "运营台", icon: "Connection" },
  { path: "/chat", label: "平台 AI", icon: "ChatDotRound" },
  { path: "/profile", label: "个人中心", icon: "User" },
];

const staffWorkbench = computed(() => {
  const hospital = userStore.userInfo?.store_type === "hospital";
  return [
    {
      path: "/workspace",
      label: hospital ? "医院工作台" : "门店工作台",
      icon: hospital ? "OfficeBuilding" : "Shop",
    },
    { path: "/chat", label: hospital ? "医院 AI" : "店内 AI", icon: "ChatDotRound" },
    { path: "/profile", label: "个人中心", icon: "User" },
  ];
});
const operatorMenu = [
  { path: "/operator", label: "运营台", icon: "Connection" },
  { path: "/chat", label: "运营 AI", icon: "ChatDotRound" },
  { path: "/profile", label: "个人中心", icon: "User" },
];

const displayMenu = computed(() => {
  if (userStore.isAdmin) return adminMenu;
  if (userStore.isStaff) return staffWorkbench.value;
  if (userStore.isOperator) return operatorMenu;
  if (userStore.isTrainer)
    return [
      { path: "/trainers", label: "预约接收台", icon: "Trophy" },
      { path: "/profile", label: "个人中心", icon: "User" },
    ];
  return userMenu;
});

function goRoute(path: string) {
  router.push(path);
}

const layout = { display: "flex", height: "100vh", overflow: "hidden" };
const sidebar = {
  width: "220px",
  background: "var(--app-sidebar-bg)",
  color: "var(--app-sidebar-text)",
  display: "flex",
  flexDirection: "column" as const,
  transition: "width .2s",
  flexShrink: 0,
};
const logoBar = {
  height: "var(--app-header-h)",
  display: "flex",
  alignItems: "center",
  gap: "10px",
  padding: "0 20px",
  fontWeight: 600,
  color: "#fff",
};
const logoText = { fontSize: "16px" };
const menuItem = (active: boolean) => ({
  display: "flex",
  alignItems: "center",
  gap: "10px",
  padding: "10px 20px",
  margin: "2px 8px",
  borderRadius: "8px",
  cursor: "pointer",
  background: active ? "var(--app-sidebar-active)" : "transparent",
  color: active ? "#fff" : "inherit",
  transition: "all .15s",
});
const sidebarFooter = {
  padding: "12px 20px",
  borderTop: "1px solid rgba(255,255,255,.06)",
  display: "flex",
  alignItems: "center",
  gap: "10px",
  cursor: "pointer",
  color: "var(--app-sidebar-text)",
};
const header = {
  height: "var(--app-header-h)",
  background: "var(--app-surface)",
  borderBottom: "1px solid var(--app-border)",
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  padding: "0 20px",
};
const userBar = {
  display: "flex",
  alignItems: "center",
  gap: "8px",
  cursor: "pointer",
  outline: "none",
};
</script>

<template>
  <div :style="layout">
    <aside :style="sidebar">
      <div :style="logoBar">
        <span
          style="
            width: 28px;
            height: 28px;
            border-radius: 8px;
            background: var(--app-brand);
            color: #1a1a1a;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 14px;
          "
          >宠</span
        >
        <span v-if="!appStore.sidebarCollapsed" :style="{ ...logoText, fontFamily: 'Outfit, Noto Sans SC, sans-serif' }"
          >宠智联</span
        >
      </div>

      <nav style="flex: 1; overflow-y: auto; padding: 8px 0">
        <div
          v-for="item in displayMenu"
          :key="item.path"
          :style="menuItem(item.path === activeRoute)"
          @click="goRoute(item.path)"
        >
          <el-icon :size="18"><component :is="item.icon" /></el-icon>
          <span v-if="!appStore.sidebarCollapsed">{{ item.label }}</span>
        </div>
      </nav>

      <div :style="sidebarFooter" @click="appStore.toggleSidebar()">
        <el-icon :size="16" style="color: var(--app-sidebar-text)"><component :is="appStore.sidebarCollapsed ? 'Expand' : 'Fold'" /></el-icon>
        <span v-if="!appStore.sidebarCollapsed">收起菜单</span>
      </div>
    </aside>

    <div style="flex: 1; min-width: 0; display: flex; flex-direction: column">
      <header :style="header">
        <div style="display: flex; align-items: center; gap: 12px">
          <el-tooltip :content="appStore.isDark ? '切换浅色' : '切换深色'">
            <el-icon :size="18" style="cursor: pointer" @click="appStore.toggleTheme()">
              <Sunny v-if="!appStore.isDark" />
              <Moon v-else />
            </el-icon>
          </el-tooltip>
        </div>

        <el-dropdown trigger="click">
          <span :style="userBar">
            <el-avatar :size="28" style="background: #2563eb">
              {{ userStore.username.slice(0, 1).toUpperCase() }}
            </el-avatar>
            <span>{{ userStore.username }}</span>
            <el-tag v-if="userStore.isAdmin" size="small" type="danger" effect="dark" style="line-height: 18px; height: 18px">超管</el-tag>
            <el-tag v-else-if="userStore.isOperator" size="small" type="success" effect="dark" style="line-height: 18px; height: 18px">运营者</el-tag>
            <el-tag v-else-if="userStore.isTrainer" size="small" type="success" effect="plain" style="line-height: 18px; height: 18px">训犬师</el-tag>
            <el-tag
              v-else-if="userStore.isStaff && userStore.userInfo?.store_type === 'hospital'"
              size="small"
              type="danger"
              effect="plain"
              style="line-height: 18px; height: 18px"
            >医院端</el-tag>
            <el-tag v-else-if="userStore.isStoreManager" size="small" type="warning" effect="dark" style="line-height: 18px; height: 18px">店主</el-tag>
            <el-tag v-else-if="userStore.isStaff" size="small" type="warning" effect="plain" style="line-height: 18px; height: 18px">店员</el-tag>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="goRoute('/profile')">个人中心</el-dropdown-item>
              <el-dropdown-item divided @click="userStore.logout()">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </header>

      <main style="flex: 1; overflow: auto; background: var(--app-bg)">
        <router-view />
      </main>
    </div>
  </div>
</template>