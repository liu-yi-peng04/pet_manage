<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from "vue";
import { ElMessageBox, ElNotification } from "element-plus";
import { workspaceApi, type StoreOverview } from "@/api/workspace";
import { ordersApi } from "@/api/orders";
import type { Order } from "@/types";
import { useUserStore } from "@/stores/user";
import { APPT_TYPES, STORE_TYPES, fmtDate } from "./workspace/shared";
import OverviewPanel from "./workspace/OverviewPanel.vue";
import AppointmentsPanel from "./workspace/AppointmentsPanel.vue";
import BoardingsPanel from "./workspace/BoardingsPanel.vue";
import ProductsPanel from "./workspace/ProductsPanel.vue";
import RecallsPanel from "./workspace/RecallsPanel.vue";
import ListingsPanel from "./workspace/ListingsPanel.vue";
import StoreOrdersPanel from "./workspace/StoreOrdersPanel.vue";
import CustomersPanel from "./workspace/CustomersPanel.vue";
import StaffPanel from "./workspace/StaffPanel.vue";
import ContentPanel from "./workspace/ContentPanel.vue";

const userStore = useUserStore();

const activeTab = ref("overview");
const loading = ref(false);
const overview = ref<StoreOverview | null>(null);

const storeName = computed(() => overview.value?.store.name ?? "我的门店");
const storeType = computed(() => overview.value?.store.store_type ?? "shop");
const isHospital = computed(() => storeType.value === "hospital");
const isShop = computed(() => storeType.value === "shop" || !storeType.value);
// 仅宠物店设店员；医院端一人一账号，不管理职工
const canManageStaff = computed(
  () => isShop.value && (userStore.isStoreManager || userStore.isAdmin)
);

const workspaceSubtitle = computed(() => {
  if (isHospital.value) return "医院端 · 接收用户预约 · 一人管本店即可";
  return "商家工作台 · 售宠上架 / 接收预约与寄养 / 用品订单 · 无「我的宠物」";
});

const apptRef = ref<InstanceType<typeof AppointmentsPanel> | null>(null);
const boardRef = ref<InstanceType<typeof BoardingsPanel> | null>(null);
const productRef = ref<InstanceType<typeof ProductsPanel> | null>(null);
const recallRef = ref<InstanceType<typeof RecallsPanel> | null>(null);
const listingRef = ref<InstanceType<typeof ListingsPanel> | null>(null);
const orderRef = ref<InstanceType<typeof StoreOrdersPanel> | null>(null);
const customerRef = ref<InstanceType<typeof CustomersPanel> | null>(null);
const staffRef = ref<InstanceType<typeof StaffPanel> | null>(null);
const contentRef = ref<InstanceType<typeof ContentPanel> | null>(null);

async function fetchOverview() {
  overview.value = await workspaceApi.overview();
}

function onTabChange(name: string | number) {
  if (name === "overview") void fetchOverview();
  if (name === "appointments") void apptRef.value?.reload();
  if (name === "boardings") void boardRef.value?.reload();
  if (name === "products") void productRef.value?.reload();
  if (name === "customers") void customerRef.value?.reload();
  if (name === "recalls") void recallRef.value?.reload();
  if (name === "listings") void listingRef.value?.reload();
  if (name === "orders") void orderRef.value?.reload();
  if (name === "staff") void staffRef.value?.reload();
  if (name === "content") void contentRef.value?.reload();
}

function openPendingAppointments() {
  void apptRef.value?.setFilter("pending");
  activeTab.value = "appointments";
}

function openTab(name: string) {
  activeTab.value = name;
  onTabChange(name);
}

// ---- 新订单语音 / 医院预约弹窗 ----
const knownOrderIds = ref<Set<number> | null>(null);
const knownPendingApptIds = ref<Set<number> | null>(null);
const hospitalPopupOpen = ref(false);
let notifyTimer: ReturnType<typeof setInterval> | null = null;

function speakOrderAlert(order: Order) {
  const text = `您有新的商品订单，编号${order.id}，金额${Math.round(Number(order.total) || 0)}元，请及时处理`;
  try {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "zh-CN";
    u.rate = 1;
    u.volume = 1;
    window.speechSynthesis.speak(u);
  } catch {
    /* 浏览器不支持语音时忽略 */
  }
}

async function pollShopOrders() {
  if (!isShop.value) return;
  try {
    const rows = await ordersApi.storeOrders();
    const pending = rows.filter((o) => o.status === "pending");
    if (knownOrderIds.value === null) {
      knownOrderIds.value = new Set(pending.map((o) => o.id));
      orderRef.value?.setRows(rows);
      return;
    }
    const fresh = pending.filter((o) => !knownOrderIds.value!.has(o.id));
    for (const o of fresh) {
      knownOrderIds.value.add(o.id);
      speakOrderAlert(o);
      ElNotification({
        title: "新订单",
        message: `#${o.id} · ¥${o.total} · ${o.address || "无地址"}`,
        type: "warning",
        duration: 8000,
        onClick: () => {
          activeTab.value = "orders";
          void orderRef.value?.reload();
        },
      });
    }
    knownOrderIds.value = new Set(pending.map((o) => o.id));
    if (activeTab.value === "orders") orderRef.value?.setRows(rows);
  } catch {
    /* 轮询失败不打扰 */
  }
}

async function pollHospitalAppointments() {
  if (!isHospital.value) return;
  try {
    const rows = await workspaceApi.appointments("pending");
    if (knownPendingApptIds.value === null) {
      knownPendingApptIds.value = new Set(rows.map((a) => a.id));
      return;
    }
    const fresh = rows.filter((a) => !knownPendingApptIds.value!.has(a.id));
    for (const a of fresh) {
      knownPendingApptIds.value.add(a.id);
      const typeLabel = APPT_TYPES[a.appt_type] ?? a.appt_type;
      const pet = a.pet_name || (a.pet_id ? `宠物#${a.pet_id}` : "未指定宠物");
      const when = fmtDate(a.appt_time);
      ElNotification({
        title: "新预约",
        message: `${typeLabel} · ${pet} · ${when}`,
        type: "warning",
        duration: 0,
        onClick: () => {
          activeTab.value = "appointments";
          void apptRef.value?.setFilter("pending");
        },
      });
      if (!hospitalPopupOpen.value) {
        hospitalPopupOpen.value = true;
        ElMessageBox.alert(
          `类型：${typeLabel}\n宠物：${pet}\n时间：${when}\n备注：${a.notes || "无"}`,
          "医院端 · 收到新预约",
          {
            confirmButtonText: "去处理",
            type: "warning",
            callback: () => {
              hospitalPopupOpen.value = false;
              activeTab.value = "appointments";
              void apptRef.value?.setFilter("pending");
              void fetchOverview();
            },
          }
        );
      }
    }
    knownPendingApptIds.value = new Set(rows.map((a) => a.id));
    if (activeTab.value === "appointments") apptRef.value?.setRowsIfPending(rows);
    fetchOverview().catch(() => undefined);
  } catch {
    /* ignore */
  }
}

async function pollNotify() {
  if (!overview.value) return;
  if (isShop.value) await pollShopOrders();
  if (isHospital.value) await pollHospitalAppointments();
}

function startNotifyPoll() {
  if (notifyTimer) return;
  void pollNotify();
  notifyTimer = setInterval(() => void pollNotify(), 8000);
}

function stopNotifyPoll() {
  if (notifyTimer) {
    clearInterval(notifyTimer);
    notifyTimer = null;
  }
  try {
    window.speechSynthesis?.cancel();
  } catch {
    /* ignore */
  }
}

onMounted(async () => {
  loading.value = true;
  try {
    await fetchOverview();
    // 等门店类型决定 Tab 显隐后，再按原逻辑预取各面板数据
    await nextTick();
    const tasks: Promise<unknown>[] = [
      apptRef.value?.reload() ?? Promise.resolve(),
      customerRef.value?.reload() ?? Promise.resolve(),
      contentRef.value?.reload() ?? Promise.resolve(),
    ];
    if (isShop.value) {
      tasks.push(
        boardRef.value?.reload() ?? Promise.resolve(),
        productRef.value?.reload() ?? Promise.resolve(),
        orderRef.value?.reload() ?? Promise.resolve(),
        listingRef.value?.reload() ?? Promise.resolve(),
      );
      if (canManageStaff.value) tasks.push(staffRef.value?.reload() ?? Promise.resolve());
    } else if (isHospital.value) {
      // 医院端聚焦预约；商品可选
      tasks.push(productRef.value?.reload() ?? Promise.resolve());
    } else {
      tasks.push(
        boardRef.value?.reload() ?? Promise.resolve(),
        productRef.value?.reload() ?? Promise.resolve(),
      );
    }
    await Promise.allSettled(tasks);
    startNotifyPoll();
  } finally {
    loading.value = false;
  }
});

onUnmounted(() => {
  stopNotifyPoll();
});
</script>

<template>
  <div class="page-container ws-page" v-loading="loading">
    <header class="ws-mast">
      <div class="ws-badge" aria-hidden="true">{{ isHospital ? "医" : "店" }}</div>
      <div class="ws-mast-copy">
        <p class="page-kicker">{{ isHospital ? "医院工作台" : "门店工作台" }}</p>
        <h2 class="page-title">
          {{ storeName }}
          <el-tag size="small" effect="plain" round class="ws-type">
            {{ STORE_TYPES[storeType] ?? storeType }}
          </el-tag>
        </h2>
        <p class="page-sub">{{ workspaceSubtitle }}</p>
      </div>
    </header>

    <div class="ws-board">
    <el-tabs v-model="activeTab" class="ws-tabs" @tab-change="onTabChange">
      <el-tab-pane label="门店概览" name="overview">
        <OverviewPanel
          :overview="overview"
          :is-hospital="isHospital"
          :is-shop="isShop"
          @open-appointments="openPendingAppointments"
          @open-boardings="openTab('boardings')"
          @open-customers="openTab('customers')"
          @open-orders="openTab('orders')"
          @open-recalls="openTab('recalls')"
        />
      </el-tab-pane>

      <el-tab-pane label="预约处理台" name="appointments">
        <AppointmentsPanel ref="apptRef" @changed="fetchOverview" />
      </el-tab-pane>

      <el-tab-pane v-if="!isHospital" label="客户寄养" name="boardings">
        <BoardingsPanel ref="boardRef" @changed="fetchOverview" />
      </el-tab-pane>

      <el-tab-pane label="商品管理" name="products">
        <ProductsPanel ref="productRef" @changed="fetchOverview" />
      </el-tab-pane>

      <el-tab-pane v-if="isShop" label="疫苗代约" name="recalls">
        <RecallsPanel ref="recallRef" />
      </el-tab-pane>

      <el-tab-pane v-if="isShop" label="待售宠物" name="listings">
        <ListingsPanel ref="listingRef" />
      </el-tab-pane>

      <el-tab-pane v-if="isShop" label="商品订单" name="orders">
        <StoreOrdersPanel ref="orderRef" />
      </el-tab-pane>

      <el-tab-pane label="客户档案" name="customers">
        <CustomersPanel ref="customerRef" />
      </el-tab-pane>

      <el-tab-pane v-if="canManageStaff" label="店员管理" name="staff">
        <StaffPanel ref="staffRef" :store-id="overview?.store.id ?? null" @changed="fetchOverview" />
      </el-tab-pane>

      <el-tab-pane label="本店内容库" name="content">
        <ContentPanel ref="contentRef" />
      </el-tab-pane>
    </el-tabs>
    </div>
  </div>
</template>

<style scoped>
.ws-mast {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 14px;
  padding: 18px 20px;
  background:
    linear-gradient(90deg, color-mix(in srgb, var(--app-brand) 28%, var(--app-surface)), var(--app-surface) 42%);
  border: 1px solid var(--app-border);
  border-radius: 18px;
  box-shadow: var(--app-shadow);
}
.ws-badge {
  width: 58px;
  height: 58px;
  border-radius: 18px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 800;
  color: #1a1a1a;
  background: linear-gradient(145deg, #ffe56a, #ff7a1a);
  box-shadow: 0 10px 20px rgba(255, 122, 26, 0.25);
}
.ws-mast .page-title {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.ws-mast .page-sub {
  margin-bottom: 0;
}
.ws-type {
  font-weight: 700;
}
.ws-board {
  background: var(--app-surface);
  border: 1px solid var(--app-border);
  border-radius: 18px;
  box-shadow: var(--app-shadow);
  padding: 4px 16px 18px;
}
.ws-board :deep(.el-tabs__header) {
  margin-bottom: 14px;
}
.ws-board :deep(.el-tabs__item) {
  height: 48px;
  font-weight: 600;
  font-size: 14px;
}
.ws-board :deep(.el-tabs__active-bar) {
  height: 3px;
  border-radius: 3px;
}
.ws-board :deep(.el-alert) {
  border-radius: 12px;
}
.ws-board :deep(.panel-toolbar),
.ws-board :deep(.panel-form) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  background: color-mix(in srgb, var(--app-bg) 70%, var(--app-surface));
}
.ws-board :deep(.panel-form) {
  justify-content: flex-start;
}
.ws-board :deep(.sheet) {
  border: 1px solid var(--app-border);
  border-radius: 14px;
  overflow: hidden;
  background: var(--app-surface);
  min-height: 120px;
}
.ws-board :deep(.el-table) {
  --el-table-border-color: transparent;
  --el-table-header-bg-color: color-mix(in srgb, var(--app-primary) 6%, var(--app-surface));
  --el-table-tr-bg-color: var(--app-surface);
  --el-table-row-hover-bg-color: var(--app-primary-soft);
}
.ws-board :deep(.el-table th.el-table__cell) {
  font-size: 12px;
  font-weight: 700;
  color: var(--app-text-muted);
  background: color-mix(in srgb, var(--app-primary) 7%, var(--app-surface));
}
.ws-board :deep(.el-table td.el-table__cell) {
  padding-top: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid color-mix(in srgb, var(--app-border) 80%, transparent);
  color: var(--app-text);
}
.ws-board :deep(.el-table .cell) {
  line-height: 1.55;
}
.ws-board :deep(.el-table__inner-wrapper::before) {
  display: none;
}
.ws-board :deep(.soft-empty) {
  margin: 8px;
  padding: 20px 8px;
  border-radius: 12px;
  background: color-mix(in srgb, var(--app-bg) 55%, var(--app-surface));
}
.ws-board :deep(.kb-chat) {
  margin-top: 8px;
  padding: 14px;
  border-radius: 14px;
  border: 1px solid var(--app-border);
  background: color-mix(in srgb, var(--app-bg) 45%, var(--app-surface));
}
.ws-board :deep(.kb-bubble) {
  max-width: min(640px, 100%);
  margin-bottom: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: var(--app-surface);
  border: 1px solid var(--app-border);
}
.ws-board :deep(.kb-bubble.user) {
  margin-left: auto;
  background: var(--app-primary-soft);
  border-color: transparent;
}
.ws-board :deep(.kb-who) {
  font-size: 12px;
  color: var(--app-text-muted);
  margin-bottom: 4px;
}
.ws-board :deep(.kb-text) {
  white-space: pre-wrap;
  line-height: 1.6;
}
.ws-board :deep(.meta-cell) {
  color: var(--app-text-secondary);
  font-size: 13px;
}
.ws-board :deep(.money-cell) {
  font-family: "Outfit", sans-serif;
  font-weight: 700;
  color: var(--app-primary);
}
@media (max-width: 720px) {
  .ws-mast {
    align-items: flex-start;
    padding: 16px;
  }
  .ws-board {
    padding: 4px 10px 14px;
  }
  .ws-board :deep(.el-tabs__item) {
    padding: 0 10px;
  }
}
</style>
