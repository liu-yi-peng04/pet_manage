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
  <div class="page-container" v-loading="loading">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <div>
        <h2 style="margin: 0 0 4px">
          {{ storeName }}
          <el-tag size="small" style="margin-left: 8px; vertical-align: middle">
            {{ STORE_TYPES[storeType] ?? storeType }}
          </el-tag>
        </h2>
        <p class="text-muted" style="margin: 0; font-size: 13px">{{ workspaceSubtitle }}</p>
      </div>
    </div>

    <el-tabs v-model="activeTab" @tab-change="onTabChange">
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
</template>
