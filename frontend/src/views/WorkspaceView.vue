<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from "vue";
import { ElMessage, ElMessageBox, ElNotification } from "element-plus";
import { workspaceApi, staffApi, type StoreOverview, type Customer, type StaffMember } from "@/api/workspace";
import { ordersApi } from "@/api/orders";
import { marketplaceApi } from "@/api/marketplace";
import type { VaccineRecall, PetListing, Order } from "@/types";
import { docApi } from "@/api/document";
import type { DocumentItem } from "@/types";
import { storeApi, type Product } from "@/api/store";
import type { Appointment, Boarding } from "@/types";
import { useUserStore } from "@/stores/user";
import { uploadMedia, mediaSrc } from "@/api/media";

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

const STORE_TYPES: Record<string, string> = {
  shop: "宠物店",
  hospital: "宠物医院",
  boarding: "寄养中心",
};

const APPT_TYPES: Record<string, string> = {
  exam: "就诊",
  grooming: "美容",
  boarding: "寄养",
  consult: "咨询",
};

const STATUS: Record<string, { label: string; type: "primary" | "success" | "warning" | "info" | "danger" }> = {
  pending: { label: "待处理", type: "warning" },
  confirmed: { label: "已确认", type: "primary" },
  completed: { label: "已完成", type: "success" },
  cancelled: { label: "已取消", type: "info" },
};

const statusLabel = (s: string) => STATUS[s]?.label ?? s;
const statusType = (s: string) => STATUS[s]?.type ?? "info";

async function fetchOverview() {
  overview.value = await workspaceApi.overview();
}

// ---- 预约处理台 ----
const appointments = ref<Appointment[]>([]);
const apptFilter = ref("");
const apptLoading = ref(false);

async function fetchAppointments() {
  apptLoading.value = true;
  try {
    appointments.value = await workspaceApi.appointments(apptFilter.value || undefined);
  } finally {
    apptLoading.value = false;
  }
}

async function setApptStatus(a: Appointment, status: string) {
  await workspaceApi.setAppointmentStatus(a.id, status);
  ElMessage.success("已更新");
  await fetchAppointments();
  fetchOverview();
}

// ---- 寄养排期管理 ----
const boardings = ref<Boarding[]>([]);
const boardingFilter = ref("");
const boardingLoading = ref(false);

async function fetchBoardings() {
  boardingLoading.value = true;
  try {
    boardings.value = await workspaceApi.boardings(boardingFilter.value || undefined);
  } finally {
    boardingLoading.value = false;
  }
}

async function setBoardingStatus(b: Boarding, status: string) {
  await workspaceApi.setBoardingStatus(b.id, status);
  ElMessage.success("已更新");
  await fetchBoardings();
  fetchOverview();
}

// ---- 本店商品管理 ----
const products = ref<Product[]>([]);
const productLoading = ref(false);

async function fetchProducts() {
  productLoading.value = true;
  try {
    products.value = await workspaceApi.products();
  } finally {
    productLoading.value = false;
  }
}

const CATEGORIES = [
  { value: "cage", label: "笼子" },
  { value: "toy", label: "玩具" },
  { value: "supply", label: "用品" },
  { value: "food", label: "食品" },
  { value: "health", label: "医疗保健" },
];
const catLabel = (v: string) => CATEGORIES.find((c) => c.value === v)?.label ?? v;
const speciesLabel = (v: string) =>
  ({ dog: "犬", cat: "猫", both: "通用" } as Record<string, string>)[v] ?? v;

const showProductDialog = ref(false);
const savingProduct = ref(false);
const editingPid = ref<number | null>(null);
const pform = ref({
  name: "",
  category: "supply",
  price: null as number | null,
  species: "both",
  min_weight_kg: null as number | null,
  max_weight_kg: null as number | null,
  spec: "",
  image_url: "",
  description: "",
  is_active: true,
  brand: "",
  package_spec: "",
});

function openAddProduct() {
  editingPid.value = null;
  pform.value = {
    name: "",
    category: "supply",
    price: null,
    species: "both",
    min_weight_kg: null,
    max_weight_kg: null,
    spec: "",
    image_url: "",
    description: "",
    is_active: true,
    brand: "",
    package_spec: "",
  };
  showProductDialog.value = true;
}

function openEditProduct(p: Product) {
  editingPid.value = p.id;
  pform.value = {
    name: p.name,
    category: p.category,
    price: p.price,
    species: p.species,
    min_weight_kg: p.min_weight_kg,
    max_weight_kg: p.max_weight_kg,
    spec: p.spec ?? "",
    image_url: p.image_url ?? "",
    description: p.description,
    is_active: p.is_active,
    brand: p.brand ?? "",
    package_spec: p.package_spec ?? "",
  };
  showProductDialog.value = true;
}

async function saveProduct() {
  if (!pform.value.name.trim()) {
    ElMessage.warning("请输入商品名称");
    return;
  }
  savingProduct.value = true;
  try {
    if (editingPid.value) {
      await storeApi.updateProduct(editingPid.value, { ...pform.value });
      ElMessage.success("已更新");
    } else {
      await storeApi.createProduct({ ...pform.value });
      ElMessage.success("商品已上架");
    }
    showProductDialog.value = false;
    await fetchProducts();
    fetchOverview();
  } finally {
    savingProduct.value = false;
  }
}

async function removeProduct(p: Product) {
  await ElMessageBox.confirm(`确定删除商品「${p.name}」？`, "删除确认", {
    type: "warning",
    confirmButtonText: "删除",
    cancelButtonText: "取消",
    confirmButtonClass: "el-button--danger",
  });
  await storeApi.removeProduct(p.id);
  ElMessage.success("已删除");
  await fetchProducts();
  fetchOverview();
}

// ---- 客户档案 ----
const customers = ref<Customer[]>([]);
const customerLoading = ref(false);

async function fetchCustomers() {
  customerLoading.value = true;
  try {
    customers.value = await workspaceApi.customers();
  } finally {
    customerLoading.value = false;
  }
}

const recalls = ref<VaccineRecall[]>([]);
const recallLoading = ref(false);
const hospitals = ref<{ id: number; name: string; city?: string | null }[]>([]);
const showInviteDialog = ref(false);
const inviting = ref(false);
const inviteTarget = ref<VaccineRecall | null>(null);
const inviteHospitalId = ref<number | null>(null);
const inviteTime = ref("");

async function fetchRecalls() {
  recallLoading.value = true;
  try {
    recalls.value = await workspaceApi.vaccineRecalls();
    if (!hospitals.value.length) {
      const stores = await storeApi.stores({ store_type: "hospital" });
      hospitals.value = stores.map((s) => ({ id: s.id, name: s.name, city: s.city }));
      if (!inviteHospitalId.value && hospitals.value[0]) inviteHospitalId.value = hospitals.value[0].id;
    }
  } finally {
    recallLoading.value = false;
  }
}

function openInvite(r: VaccineRecall) {
  inviteTarget.value = r;
  inviteTime.value = "";
  if (!inviteHospitalId.value && hospitals.value[0]) inviteHospitalId.value = hospitals.value[0].id;
  showInviteDialog.value = true;
}

async function confirmInvite() {
  if (!inviteTarget.value) return;
  if (!inviteHospitalId.value) {
    ElMessage.warning("请选择代约的接种医院");
    return;
  }
  inviting.value = true;
  try {
    const appt = await workspaceApi.inviteVaccine({
      pet_id: inviteTarget.value.pet_id,
      vaccine_id: inviteTarget.value.vaccine_id,
      hospital_id: inviteHospitalId.value,
      appt_time: inviteTime.value || undefined,
      notes: "宠物店中转代约",
    });
    const hName = hospitals.value.find((h) => h.id === inviteHospitalId.value)?.name || "医院";
    ElMessage.success(`已代约「${hName}」接种，预约单 #${appt.id} 已推送到医院端`);
    showInviteDialog.value = false;
  } finally {
    inviting.value = false;
  }
}

const listingPhotoInput = ref<HTMLInputElement | null>(null);
const listingUploading = ref(false);

async function onListingPhoto(ev: Event) {
  const input = ev.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  listingUploading.value = true;
  try {
    const res = await uploadMedia(file, "listing");
    listingForm.value.image_url = res.url;
    ElMessage.success("照片已写入数据库");
  } finally {
    listingUploading.value = false;
    input.value = "";
  }
}
const listingForm = ref({
  name: "",
  species: "dog",
  breed: "",
  age_months: 3,
  price: 0,
  appearance: "standard",
  color: "",
  weight_kg: null as number | null,
  image_url: "",
  vaccine_note: "",
  health_note: "",
  description: "",
});
async function fetchListings() {
  listingLoading.value = true;
  try {
    listings.value = await marketplaceApi.storeListings();
  } finally {
    listingLoading.value = false;
  }
}
async function addListing() {
  if (!listingForm.value.name) return;
  await marketplaceApi.createListing(listingForm.value);
  ElMessage.success("已上架");
  await fetchListings();
}

const storeOrders = ref<Order[]>([]);
async function fetchStoreOrders() {
  storeOrders.value = await ordersApi.storeOrders();
}
async function pushOrder(o: Order, status: string) {
  await ordersApi.setStatus(o.id, status);
  ElMessage.success("已更新");
  await fetchStoreOrders();
}

const fmtDate = (v: string | null) =>
  v ? new Date(v).toLocaleString("zh-CN", { hour12: false }).slice(0, 16) : "—";

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
      storeOrders.value = rows;
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
          fetchStoreOrders();
        },
      });
    }
    knownOrderIds.value = new Set(pending.map((o) => o.id));
    if (activeTab.value === "orders") storeOrders.value = rows;
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
          apptFilter.value = "pending";
          fetchAppointments();
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
              apptFilter.value = "pending";
              fetchAppointments();
              fetchOverview();
            },
          }
        );
      }
    }
    knownPendingApptIds.value = new Set(rows.map((a) => a.id));
    if (activeTab.value === "appointments" && apptFilter.value === "pending") {
      appointments.value = rows;
    }
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

// ---- 店员管理（仅宠物店） ----
const staffList = ref<StaffMember[]>([]);
const staffLoading = ref(false);
const showStaffDialog = ref(false);
const staffKeyword = ref("");
const candidates = ref<{ id: number; username: string; email: string | null }[]>([]);
const selectedUid = ref<number | null>(null);
const staffRole = ref("assistant");
const assigning = ref(false);

async function fetchStaff() {
  if (!overview.value) return;
  staffLoading.value = true;
  try {
    staffList.value = await staffApi.list(overview.value.store.id);
  } finally {
    staffLoading.value = false;
  }
}

async function searchCandidates() {
  if (!overview.value || !staffKeyword.value.trim()) return;
  candidates.value = await staffApi.search(overview.value.store.id, staffKeyword.value.trim());
  selectedUid.value = candidates.value[0]?.id ?? null;
}

async function assignStaff() {
  if (!overview.value || !selectedUid.value) {
    ElMessage.warning("请先搜索并选择用户");
    return;
  }
  assigning.value = true;
  try {
    await staffApi.assign(overview.value.store.id, {
      user_id: selectedUid.value,
      staff_role: staffRole.value,
    });
    ElMessage.success("已添加店员");
    showStaffDialog.value = false;
    await fetchStaff();
    fetchOverview();
  } finally {
    assigning.value = false;
  }
}

async function removeStaff(m: StaffMember) {
  if (!overview.value) return;
  await ElMessageBox.confirm(`确定解除「${m.username}」的店员身份？`, "解除确认", {
    type: "warning",
    confirmButtonText: "解除",
    cancelButtonText: "取消",
    confirmButtonClass: "el-button--danger",
  });
  await staffApi.remove(overview.value.store.id, m.id);
  ElMessage.success("已解除");
  await fetchStaff();
  fetchOverview();
}

// ---- tab 切换 ----
function onTabChange(name: string | number) {
  if (name === "overview") fetchOverview();
  if (name === "appointments") fetchAppointments();
  if (name === "boardings") fetchBoardings();
  if (name === "products") fetchProducts();
  if (name === "customers") fetchCustomers();
  if (name === "recalls") fetchRecalls();
  if (name === "listings") fetchListings();
  if (name === "orders") fetchStoreOrders();
  if (name === "staff") fetchStaff();
  if (name === "content") fetchStoreKb();
}

// ---- 本店内容库 ----
const storeKb = ref<{ id: number; name: string; description: string } | null>(null);
const kbDocs = ref<DocumentItem[]>([]);
const kbLoading = ref(false);
const uploading = ref(false);
const kbFileInput = ref<HTMLInputElement | null>(null);

async function fetchStoreKb() {
  storeKb.value = await workspaceApi.storeKb();
  await fetchKbDocs();
}

async function fetchKbDocs() {
  kbLoading.value = true;
  try {
    kbDocs.value = await workspaceApi.storeKbDocuments();
  } finally {
    kbLoading.value = false;
  }
}

function pickKbFile() {
  kbFileInput.value?.click();
}

async function onKbFile(ev: Event) {
  const input = ev.target as HTMLInputElement;
  const f = input.files?.[0];
  if (!f) return;
  if (!storeKb.value) await fetchStoreKb();
  uploading.value = true;
  try {
    await docApi.upload(storeKb.value!.id, f);
    ElMessage.success("已上传并入库");
    await fetchKbDocs();
  } finally {
    uploading.value = false;
    input.value = "";
  }
}

async function removeKbDoc(d: DocumentItem) {
  await ElMessageBox.confirm(`确定删除「${d.filename}」？`, "删除确认", {
    type: "warning",
    confirmButtonText: "删除",
    cancelButtonText: "取消",
    confirmButtonClass: "el-button--danger",
  });
  await docApi.remove(d.id);
  ElMessage.success("已删除");
  await fetchKbDocs();
}

// ---- 店端 AI 问答（绑定本店内容库） ----
interface KbMsg {
  role: "user" | "assistant";
  text: string;
  tools: string[];
}
const kbConsult = ref<"policy" | "pet">("policy");
const kbMsgs = ref<KbMsg[]>([]);
const kbQ = ref("");
const kbAsking = ref(false);
const kbWaitingHint = ref(false);
const kbScrolling = ref<HTMLElement | null>(null);
let kbConvId: number | null = null;
let kbWaitTimer: ReturnType<typeof setTimeout> | null = null;

function resetKbChat() {
  kbMsgs.value = [];
  kbConvId = null;
  kbWaitingHint.value = false;
  if (kbWaitTimer) {
    clearTimeout(kbWaitTimer);
    kbWaitTimer = null;
  }
}

function kbRoleLabel(r: string) {
  return r === "user" ? "我" : kbConsult.value === "policy" ? "制度助手" : "养宠顾问";
}

async function askKb() {
  const q = kbQ.value.trim();
  if (!q || kbAsking.value) return;
  if (!storeKb.value) await fetchStoreKb();
  const kbId = storeKb.value!.id;
  kbMsgs.value.push({ role: "user", text: q, tools: [] });
  kbQ.value = "";
  const asst = reactive<KbMsg>({ role: "assistant", text: "", tools: [] });
  kbMsgs.value.push(asst);
  kbAsking.value = true;
  kbWaitingHint.value = false;
  if (kbWaitTimer) clearTimeout(kbWaitTimer);
  kbWaitTimer = setTimeout(() => {
    if (kbAsking.value) kbWaitingHint.value = true;
  }, 3500);
  const token = localStorage.getItem("token");
  try {
    const resp = await fetch("/api/chat/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
        body: JSON.stringify({
          kb_id: kbId,
          content: q,
          conversation_id: kbConvId,
          consult_type: "policy",
          pet_id: null,
        }),
    });
    const reader = resp.body!.getReader();
    const dec = new TextDecoder();
    let buf = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let idx: number;
      while ((idx = buf.indexOf("\n\n")) >= 0) {
        const chunk = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        const line = chunk.split("\n").find((l) => l.startsWith("data: "));
        if (!line) continue;
        const payload = line.slice(6);
        try {
          const ev = JSON.parse(payload);
          if (ev.type === "tool" && ev.summary) asst.tools.push(ev.summary);
          else if (ev.type === "conv" && ev.id) kbConvId = ev.id;
          else if (ev.type === "delta" && ev.content) asst.text += ev.content;
          else if (ev.type === "error") asst.text += `\n（出错：${ev.content}）`;
        } catch {
          if (payload.startsWith("[TOOL]")) asst.tools.push(payload.slice(6));
          else if (payload.startsWith("[MSG]")) kbConvId = Number(payload.slice(6));
          else if (payload !== "[DONE]") asst.text += payload;
        }
      }
    }
  } catch (e) {
    asst.text += (asst.text ? "\n" : "") + `（请求失败：${e}）`;
  }
  kbAsking.value = false;
  kbWaitingHint.value = false;
  if (kbWaitTimer) {
    clearTimeout(kbWaitTimer);
    kbWaitTimer = null;
  }
}

onMounted(async () => {
  loading.value = true;
  try {
    await fetchOverview();
    const tasks: Promise<unknown>[] = [fetchAppointments(), fetchCustomers(), fetchStoreKb()];
    if (isShop.value) {
      tasks.push(fetchBoardings(), fetchProducts(), fetchStoreOrders(), fetchListings());
      if (canManageStaff.value) tasks.push(fetchStaff());
    } else if (isHospital.value) {
      // 医院端聚焦预约；商品可选
      tasks.push(fetchProducts());
    } else {
      tasks.push(fetchBoardings(), fetchProducts());
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
      <!-- 概览 -->
      <el-tab-pane label="门店概览" name="overview">
        <div class="loop-strip" style="margin-top: 0">
          <strong>{{ isHospital ? "医院闭环" : "门店闭环" }}</strong>
          <span v-if="isHospital">用户预约就诊 → 你在此确认 → 用户端状态更新</span>
          <span v-else>用户下单/预约看宠/寄养 → 你接单确认 → 用户在订单与预约里看到进度</span>
        </div>
        <div v-if="overview" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px">
          <div
            class="stat-tile"
            @click="activeTab = 'appointments'; apptFilter = 'pending'; fetchAppointments()"
          >
            <div class="label">待处理预约</div>
            <div class="value" style="color: var(--app-primary)">{{ overview.pending_appointments }}</div>
            <div class="hint">点此去确认 ›</div>
          </div>
          <div
            v-if="!isHospital"
            class="stat-tile"
            @click="activeTab = 'boardings'; fetchBoardings()"
          >
            <div class="label">进行中寄养</div>
            <div class="value" style="color: #2563eb">{{ overview.active_boardings }}</div>
            <div class="hint">客户寄养排期 ›</div>
          </div>
          <div class="stat-tile" @click="activeTab = 'customers'; fetchCustomers()">
            <div class="label">客户数</div>
            <div class="value" style="color: #16a34a">{{ overview.customers }}</div>
            <div class="hint">到店客户档案 ›</div>
          </div>
          <div v-if="isShop" class="stat-tile" @click="activeTab = 'orders'; fetchStoreOrders()">
            <div class="label">商品 / 履约</div>
            <div class="value" style="color: #9333ea">{{ overview.products }}</div>
            <div class="hint">去处理订单 ›</div>
          </div>
          <div
            v-if="isShop"
            class="stat-tile"
            @click="activeTab = 'recalls'; fetchRecalls()"
          >
            <div class="label">疫苗临期（代约）</div>
            <div class="value" style="color: #dc2626">{{ overview.due_vaccines }}</div>
            <div class="hint">中转预约医院 ›</div>
          </div>
        </div>
        <el-empty v-else description="暂无门店数据" :image-size="90" />
      </el-tab-pane>

      <!-- 预约处理：只接收用户端预约，商家不能替用户下预约单 -->
      <el-tab-pane label="预约处理台" name="appointments">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
          title="用户在「预约到店」提交后会出现在这里。商家端只确认/完成，不能自己发起预约。"
        />
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px">
          <el-radio-group v-model="apptFilter" @change="fetchAppointments">
            <el-radio-button value="">全部</el-radio-button>
            <el-radio-button value="pending">待处理</el-radio-button>
            <el-radio-button value="confirmed">已确认</el-radio-button>
            <el-radio-button value="completed">已完成</el-radio-button>
            <el-radio-button value="cancelled">已取消</el-radio-button>
          </el-radio-group>
        </div>
        <el-table v-loading="apptLoading" :data="appointments" style="width: 100%">
          <el-table-column prop="appt_time" label="时间" width="160">
            <template #default="{ row }">{{ fmtDate(row.appt_time) }}</template>
          </el-table-column>
          <el-table-column label="类型" width="90">
            <template #default="{ row }">{{ APPT_TYPES[row.appt_type] ?? row.appt_type }}</template>
          </el-table-column>
          <el-table-column prop="user_id" label="客户 ID" width="90" />
          <el-table-column label="宠物" min-width="120">
            <template #default="{ row }">{{ row.pet_name || (row.pet_id ? `#${row.pet_id}` : "—") }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="notes" label="备注" min-width="140">
            <template #default="{ row }">{{ row.notes || "—" }}</template>
          </el-table-column>
          <el-table-column label="操作" width="200" align="right">
            <template #default="{ row }">
              <template v-if="row.status === 'pending'">
                <el-button size="small" type="primary" link @click="setApptStatus(row, 'confirmed')">确认</el-button>
                <el-button size="small" type="danger" link @click="setApptStatus(row, 'cancelled')">取消</el-button>
              </template>
              <el-button
                v-else-if="row.status === 'confirmed'"
                size="small"
                type="success"
                link
                @click="setApptStatus(row, 'completed')"
              >完成</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!apptLoading && !appointments.length" description="暂无预约" :image-size="70" />
      </el-tab-pane>

      <!-- 寄养排期：客户寄养到本店的宠物（非商家自有宠物） -->
      <el-tab-pane v-if="!isHospital" label="客户寄养" name="boardings">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
          title="这里是用户预约寄养到本店的宠物排期。商家没有「我的宠物」，也不在此发起预约——只接收并处理。"
        />
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px">
          <el-radio-group v-model="boardingFilter" @change="fetchBoardings">
            <el-radio-button value="">全部</el-radio-button>
            <el-radio-button value="pending">待确认</el-radio-button>
            <el-radio-button value="confirmed">已确认</el-radio-button>
            <el-radio-button value="completed">已完成</el-radio-button>
            <el-radio-button value="cancelled">已取消</el-radio-button>
          </el-radio-group>
        </div>
        <el-table v-loading="boardingLoading" :data="boardings" style="width: 100%">
          <el-table-column prop="start_date" label="入住" width="110" />
          <el-table-column prop="end_date" label="离店" width="110" />
          <el-table-column prop="user_id" label="客户 ID" width="90" />
          <el-table-column prop="pet_id" label="宠物 ID" width="90" />
          <el-table-column label="日费" width="90">
            <template #default="{ row }">{{ row.daily_fee != null ? `¥${row.daily_fee}/天` : "—" }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="notes" label="备注" min-width="140">
            <template #default="{ row }">{{ row.notes || "—" }}</template>
          </el-table-column>
          <el-table-column label="操作" width="200" align="right">
            <template #default="{ row }">
              <template v-if="row.status === 'pending'">
                <el-button size="small" type="primary" link @click="setBoardingStatus(row, 'confirmed')">确认</el-button>
                <el-button size="small" type="danger" link @click="setBoardingStatus(row, 'cancelled')">取消</el-button>
              </template>
              <el-button
                v-else-if="row.status === 'confirmed'"
                size="small"
                type="success"
                link
                @click="setBoardingStatus(row, 'completed')"
              >完成</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!boardingLoading && !boardings.length" description="暂无寄养订单" :image-size="70" />
      </el-tab-pane>

      <!-- 本店商品 -->
      <el-tab-pane label="商品管理" name="products">
        <div style="display: flex; justify-content: flex-end; margin-bottom: 12px">
          <el-button type="primary" size="small" @click="openAddProduct">
            <el-icon style="margin-right: 4px"><Plus /></el-icon>上架商品
          </el-button>
        </div>
        <el-table v-loading="productLoading" :data="products" style="width: 100%">
          <el-table-column prop="name" label="名称" min-width="160" />
          <el-table-column label="分类" width="100">
            <template #default="{ row }">{{ catLabel(row.category) }}</template>
          </el-table-column>
          <el-table-column label="价格" width="100">
            <template #default="{ row }">{{ row.price != null ? `¥${row.price}` : "面议" }}</template>
          </el-table-column>
          <el-table-column label="适用" width="90">
            <template #default="{ row }">{{ speciesLabel(row.species) }}</template>
          </el-table-column>
          <el-table-column label="规格" min-width="130">
            <template #default="{ row }">{{ row.spec || "—" }}</template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="row.is_active ? 'success' : 'info'" effect="plain">
                {{ row.is_active ? "在售" : "下架" }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" align="right">
            <template #default="{ row }">
              <el-button size="small" link @click="openEditProduct(row)">编辑</el-button>
              <el-button size="small" type="danger" link @click="removeProduct(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!productLoading && !products.length" description="本店暂无商品" :image-size="70" />
      </el-tab-pane>

      <el-tab-pane v-if="isShop" label="疫苗代约" name="recalls">
        <el-alert
          type="warning"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
          title="宠物店不负责接种，只做中转：发现客户疫苗临期后，代约到合作医院；医院在「预约处理台」确认并完成接种。"
        />
        <el-table v-loading="recallLoading" :data="recalls" style="width: 100%">
          <el-table-column prop="owner_name" label="主人" width="110" />
          <el-table-column prop="pet_name" label="宠物" width="110" />
          <el-table-column prop="vaccine_name" label="疫苗" min-width="140" />
          <el-table-column prop="next_due_date" label="到期日" width="120" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">{{ row.status === "overdue" ? "已过期" : "临期" }} {{ row.days_left }}天</template>
          </el-table-column>
          <el-table-column label="操作" width="150" align="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" @click="openInvite(row)">代约医院</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!recallLoading && !recalls.length" description="暂无临期疫苗客户" :image-size="70" />
      </el-tab-pane>

      <el-tab-pane v-if="isShop" label="待售宠物" name="listings">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
          title="本店代售/待售宠（上架管理）。用户端「选宠市场」是浏览与咨询入口，展示卡片与本表字段侧重点不同。"
        />
        <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap">
          <el-input v-model="listingForm.name" placeholder="名字" style="width: 120px" />
          <el-input v-model="listingForm.breed" placeholder="品种" style="width: 120px" />
          <el-input-number v-model="listingForm.age_months" :min="0" placeholder="月龄" />
          <el-select v-model="listingForm.appearance" style="width: 100px">
            <el-option label="精品" value="premium" />
            <el-option label="标准" value="standard" />
            <el-option label="合格" value="fair" />
            <el-option label="特价" value="sale" />
          </el-select>
          <el-input-number v-model="listingForm.price" :min="0" placeholder="价格" />
          <el-button :loading="listingUploading" @click="listingPhotoInput?.click()">上传照片</el-button>
          <input ref="listingPhotoInput" type="file" accept="image/jpeg,image/png,image/webp,image/gif" style="display: none" @change="onListingPhoto" />
          <img v-if="listingForm.image_url" :src="mediaSrc(listingForm.image_url)" alt="预览" style="width: 40px; height: 40px; object-fit: cover; border-radius: 6px" />
          <el-button type="primary" @click="addListing">上架</el-button>
        </div>
        <el-table v-loading="listingLoading" :data="listings">
          <el-table-column label="照片" width="70">
            <template #default="{ row }">
              <img v-if="row.image_url" :src="mediaSrc(row.image_url)" style="width: 40px; height: 40px; object-fit: cover; border-radius: 6px" />
              <span v-else class="text-muted">—</span>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="名字" />
          <el-table-column prop="breed" label="品种" />
          <el-table-column prop="age_months" label="月龄" width="80" />
          <el-table-column prop="appearance" label="品相" width="80" />
          <el-table-column prop="price" label="价格" />
          <el-table-column prop="vaccine_note" label="疫苗" />
        </el-table>
      </el-tab-pane>

      <el-tab-pane v-if="isShop" label="商品订单" name="orders">
        <el-table :data="storeOrders">
          <el-table-column prop="id" label="#" width="70" />
          <el-table-column prop="address" label="地址" min-width="160" />
          <el-table-column prop="total" label="金额" width="90" />
          <el-table-column prop="status" label="状态" width="110" />
          <el-table-column label="履约" width="220">
            <template #default="{ row }">
              <el-button v-if="row.status === 'pending'" size="small" @click="pushOrder(row, 'accepted')">接单</el-button>
              <el-button v-if="row.status === 'accepted'" size="small" @click="pushOrder(row, 'preparing')">备货</el-button>
              <el-button v-if="row.status === 'preparing'" size="small" @click="pushOrder(row, 'delivering')">配送</el-button>
              <el-button v-if="row.status === 'delivering'" size="small" type="primary" @click="pushOrder(row, 'completed')">完成</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 客户档案 -->
      <el-tab-pane label="客户档案" name="customers">
        <el-table v-loading="customerLoading" :data="customers" style="width: 100%">
          <el-table-column prop="username" label="客户" min-width="120" />
          <el-table-column prop="email" label="邮箱" min-width="160">
            <template #default="{ row }">{{ row.email || "—" }}</template>
          </el-table-column>
          <el-table-column label="宠物" min-width="180">
            <template #default="{ row }">
              <template v-if="row.pets.length">
                <el-tag
                  v-for="p in row.pets"
                  :key="p.id"
                  size="small"
                  effect="plain"
                  style="margin: 2px"
                >{{ p.name }}（{{ speciesLabel(p.species) }}）</el-tag>
              </template>
              <span v-else class="text-muted">—</span>
            </template>
          </el-table-column>
          <el-table-column label="最近到店" width="170">
            <template #default="{ row }">{{ fmtDate(row.last_appointment_at) }}</template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!customerLoading && !customers.length" description="暂无客户" :image-size="70" />
      </el-tab-pane>

      <!-- 店员管理（仅宠物店店主；医院端不设职工） -->
      <el-tab-pane v-if="canManageStaff" label="店员管理" name="staff">
        <div style="display: flex; justify-content: flex-end; margin-bottom: 12px">
          <el-button type="primary" size="small" @click="showStaffDialog = true">
            <el-icon style="margin-right: 4px"><Plus /></el-icon>添加店员
          </el-button>
        </div>
        <el-table v-loading="staffLoading" :data="staffList" style="width: 100%">
          <el-table-column prop="username" label="用户名" min-width="140" />
          <el-table-column prop="email" label="邮箱" min-width="160">
            <template #default="{ row }">{{ row.email || "—" }}</template>
          </el-table-column>
          <el-table-column label="身份" width="110">
            <template #default="{ row }">
              <el-tag size="small" :type="row.staff_role === 'manager' ? 'warning' : 'primary'" effect="plain">
                {{ row.staff_role === "manager" ? "店主" : "店员" }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="110" align="right">
            <template #default="{ row }">
              <el-button
                v-if="!(row.id === userStore.userInfo?.id)"
                size="small"
                type="danger"
                link
                @click="removeStaff(row)"
              >解除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!staffLoading && !staffList.length" description="暂无店员" :image-size="70" />
      </el-tab-pane>

      <!-- 本店内容库 -->
      <el-tab-pane label="本店内容库" name="content">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px">
          <div>
            <b>{{ storeKb?.name ?? "本店内容库" }}</b>
            <span class="text-muted" style="margin-left: 8px; font-size: 12px">
              店内制度/条款/商品说明/SOP，供店员问答与培训
            </span>
          </div>
          <el-button type="primary" size="small" :loading="uploading" @click="pickKbFile">上传文档</el-button>
          <input
            ref="kbFileInput"
            type="file"
            style="display: none"
            accept=".pdf,.docx,.txt,.md,.mdx,.csv"
            @change="onKbFile"
          />
        </div>

        <el-table v-loading="kbLoading" :data="kbDocs" style="width: 100%">
          <el-table-column prop="filename" label="文档" min-width="220" />
          <el-table-column prop="file_type" label="类型" width="90" />
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag size="small" :type="row.status === 'indexed' ? 'success' : 'info'" effect="plain">
                {{ row.status === "indexed" ? "已入库" : "处理中" }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="上传时间" width="180">
            <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="90" align="right">
            <template #default="{ row }">
              <el-button size="small" type="danger" link @click="removeKbDoc(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!kbLoading && !kbDocs.length" description="尚未上传文档，上传后店员可据此问答" :image-size="70" />

        <el-divider content-position="left">店内 AI（与用户端隔离）</el-divider>
        <el-alert
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
          title="只答本店制度/SOP（寄养收费、售宠话术等）。用户养宠问答不会出现在这里；商家没有「我的宠物」。"
        />
        <el-alert
          v-if="kbWaitingHint"
          type="warning"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
          title="回答需要一点时间，可先处理预约或订单，稍后再回来查看。"
        />
        <div>
          <div v-for="(m, i) in kbMsgs" :key="i" style="margin-bottom: 10px">
            <div style="font-size: 12px; color: #909399; margin-bottom: 2px">
              {{ kbRoleLabel(m.role) }}
              <el-tag
                v-for="(t, ti) in m.tools"
                :key="ti"
                size="small"
                type="info"
                effect="plain"
                style="margin-left: 6px"
              >{{ t }}</el-tag>
            </div>
            <div style="white-space: pre-wrap">{{ m.text }}</div>
          </div>
          <el-empty v-if="!kbMsgs.length" description="问寄养收费、售宠话术、退换货 SOP，将检索本店内容库" :image-size="60" />
          <div style="display: flex; gap: 8px; margin-top: 12px">
            <el-input
              v-model="kbQ"
              placeholder="例如：顾客要寄养中型犬怎么收费？"
              @keyup.enter="askKb"
              :disabled="kbAsking"
            />
            <el-button type="primary" :loading="kbAsking" @click="askKb">发送</el-button>
          </div>
          <el-button
            v-if="kbMsgs.length"
            size="small"
            link
            type="info"
            style="margin-top: 6px"
            @click="kbMsgs = []; kbConvId = null"
          >清空对话</el-button>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 商品对话框 -->
    <el-dialog v-model="showProductDialog" :title="editingPid ? '编辑商品' : '上架商品'" width="560px">
      <el-form label-position="top">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px">
          <el-form-item label="商品名称" required>
            <el-input v-model="pform.name" maxlength="60" />
          </el-form-item>
          <el-form-item label="分类">
            <el-select v-model="pform.category" style="width: 100%">
              <el-option v-for="c in CATEGORIES" :key="c.value" :label="c.label" :value="c.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="价格 (元)">
            <el-input-number v-model="pform.price" :min="0" :precision="2" style="width: 100%" />
          </el-form-item>
          <el-form-item label="适用物种">
            <el-select v-model="pform.species" style="width: 100%">
              <el-option label="通用" value="both" />
              <el-option label="犬" value="dog" />
              <el-option label="猫" value="cat" />
            </el-select>
          </el-form-item>
          <el-form-item label="适用体重下限 (kg)">
            <el-input-number v-model="pform.min_weight_kg" :min="0" style="width: 100%" />
          </el-form-item>
          <el-form-item label="适用体重上限 (kg)">
            <el-input-number v-model="pform.max_weight_kg" :min="0" style="width: 100%" />
          </el-form-item>
        </div>
        <el-form-item label="规格参数">
          <el-input v-model="pform.spec" placeholder="如：长 90cm × 宽 60cm × 高 65cm" />
        </el-form-item>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px">
          <el-form-item label="品牌">
            <el-input v-model="pform.brand" placeholder="如：皇家" />
          </el-form-item>
          <el-form-item label="包装">
            <el-input v-model="pform.package_spec" placeholder="如：10kg 袋装" />
          </el-form-item>
        </div>
        <el-form-item label="商品描述">
          <el-input v-model="pform.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="上架状态">
          <el-switch v-model="pform.is_active" active-text="上架" inactive-text="下架" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showProductDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingProduct" @click="saveProduct">保存</el-button>
      </template>
    </el-dialog>

    <!-- 添加店员对话框 -->
    <el-dialog v-model="showStaffDialog" title="添加店员" width="480px">
      <el-form label-position="top">
        <el-form-item label="搜索用户（按用户名）">
          <div style="display: flex; gap: 8px; width: 100%">
            <el-input v-model="staffKeyword" placeholder="输入用户名关键字" @keyup.enter="searchCandidates" />
            <el-button @click="searchCandidates"><el-icon><Search /></el-icon></el-button>
          </div>
        </el-form-item>
        <el-form-item label="选择用户">
          <el-select v-model="selectedUid" style="width: 100%" placeholder="先搜索再选择" filterable>
            <el-option
              v-for="c in candidates"
              :key="c.id"
              :label="`${c.username}${c.email ? '（' + c.email + '）' : ''}`"
              :value="c.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="身份">
          <el-radio-group v-model="staffRole">
            <el-radio-button value="assistant">店员</el-radio-button>
            <el-radio-button value="manager">店主</el-radio-button>
          </el-radio-group>
          <div v-if="!userStore.isAdmin" class="text-muted" style="font-size: 12px; margin-top: 6px">
            只有超管可以指定店主
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showStaffDialog = false">取消</el-button>
        <el-button type="primary" :loading="assigning" @click="assignStaff">添加</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showInviteDialog" title="代约医院接种（中转）" width="480px">
      <el-alert
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 14px"
        title="本店不打针：只是帮客户把预约推到医院。医院确认后，用户可在「我的预约」看到进度。"
      />
      <el-form label-position="top" v-if="inviteTarget">
        <el-form-item label="客户 / 宠物">
          <div>{{ inviteTarget.owner_name }} · {{ inviteTarget.pet_name }} · {{ inviteTarget.vaccine_name }}</div>
        </el-form-item>
        <el-form-item label="接种医院" required>
          <el-select v-model="inviteHospitalId" placeholder="选择合作医院" style="width: 100%">
            <el-option v-for="h in hospitals" :key="h.id" :label="h.city ? `${h.name}（${h.city}）` : h.name" :value="h.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="预约时间（可选，默认两天后上午10点）">
          <el-date-picker
            v-model="inviteTime"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="选择时间"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showInviteDialog = false">取消</el-button>
        <el-button type="primary" :loading="inviting" @click="confirmInvite">确认代约</el-button>
      </template>
    </el-dialog>
  </div>
</template>
