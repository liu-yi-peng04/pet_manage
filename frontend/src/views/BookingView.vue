<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { bookingApi, type Appointment, type Boarding } from "@/api/booking";
import { storeApi, type Store } from "@/api/store";
import { petsApi, type Pet } from "@/api/pets";

const route = useRoute();
const router = useRouter();
const activeTab = ref("appointments");
const appointments = ref<Appointment[]>([]);
const boardings = ref<Boarding[]>([]);
const pets = ref<Pet[]>([]);
const stores = ref<Store[]>([]);
const loading = ref(false);

const APPT_TYPES = [
  { value: "exam", label: "就诊" },
  { value: "grooming", label: "美容" },
  { value: "boarding", label: "寄养" },
  { value: "consult", label: "咨询" },
  { value: "train", label: "训练" },
];
const STATUS = [
  { value: "pending", label: "待确认", type: "warning" as const },
  { value: "confirmed", label: "已确认", type: "success" as const },
  { value: "completed", label: "已完成", type: "info" as const },
  { value: "cancelled", label: "已取消", type: "danger" as const },
];
const statusInfo = (s: string) => STATUS.find((x) => x.value === s) ?? { label: s, type: "info" as const };
const apptTypeLabel = (v: string) => APPT_TYPES.find((x) => x.value === v)?.label ?? v;
const petName = (id: number | null) => pets.value.find((p) => p.id === id)?.name ?? "—";
const storeName = (id: number | null, fallback?: string | null) =>
  fallback || stores.value.find((s) => s.id === id)?.name || "未选门店";
const partyLabel = (row: Appointment) => {
  if (row.appt_type === "train") return row.trainer_name || "训犬师";
  return row.store_name || storeName(row.store_id);
};
const lastTicket = ref<{ id: number; store: string; status: string; kind: string } | null>(null);

const hospitalStores = computed(() => stores.value.filter((s) => s.store_type === "hospital"));
const shopStores = computed(() => stores.value.filter((s) => s.store_type === "shop"));
const boardingStores = computed(() => stores.value.filter((s) => s.store_type === "boarding" || s.store_type === "shop"));
const apptStoreOptions = computed(() => {
  if (aform.value.appt_type === "exam") return hospitalStores.value;
  if (aform.value.appt_type === "grooming") return shopStores.value;
  if (aform.value.appt_type === "boarding") return boardingStores.value;
  return stores.value;
});

async function fetchData() {
  loading.value = true;
  try {
    [appointments.value, boardings.value, pets.value, stores.value] = await Promise.all([
      bookingApi.appointments(),
      bookingApi.boardings(),
      petsApi.list(),
      storeApi.stores(),
    ]);
  } finally {
    loading.value = false;
  }
}

// ---- 预约 ----
const showApptDialog = ref(false);
const saving = ref(false);
const aform = ref({
  pet_id: null as number | null,
  store_id: null as number | null,
  appt_type: "exam",
  appt_time: "",
  notes: "",
});

function openAddAppt(prefill?: Partial<typeof aform.value>) {
  aform.value = {
    pet_id: pets.value[0]?.id ?? null,
    store_id: null,
    appt_type: "exam",
    appt_time: "",
    notes: "",
    ...prefill,
  };
  showApptDialog.value = true;
}

/** 从选宠市场 / 首页带参跳转：自动打开预约并预填门店 */
function applyQueryPrefill() {
  const q = route.query;
  if (q.tab === "boardings") {
    activeTab.value = "boardings";
  }
  const storeId = q.store_id ? Number(q.store_id) : null;
  const apptType = typeof q.appt_type === "string" ? q.appt_type : "";
  const notes = typeof q.notes === "string" ? q.notes : "";
  const listing = typeof q.listing === "string" ? q.listing : "";
  if (storeId || apptType || notes || listing) {
    activeTab.value = "appointments";
    openAddAppt({
      store_id: storeId && !Number.isNaN(storeId) ? storeId : null,
      appt_type: apptType || "consult",
      notes: notes || (listing ? `想看宠：${listing}` : ""),
      pet_id: pets.value[0]?.id ?? null,
    });
    // 清掉 query，避免刷新重复弹窗
    router.replace({ path: "/booking" });
  }
}

async function saveAppt() {
  if (!aform.value.store_id) {
    ElMessage.warning("请选择医院或门店，预约才会提交给商家");
    return;
  }
  if (!aform.value.appt_time) {
    ElMessage.warning("请选择预约时间");
    return;
  }
  saving.value = true;
  try {
    const created = await bookingApi.createAppointment({
      pet_id: aform.value.pet_id,
      store_id: aform.value.store_id,
      appt_type: aform.value.appt_type,
      appt_time: new Date(aform.value.appt_time).toISOString(),
      notes: aform.value.notes,
    });
    lastTicket.value = {
      id: created.id,
      store: created.store_name || storeName(created.store_id),
      status: created.status,
      kind: apptTypeLabel(created.appt_type),
    };
    ElMessage.success({
      message: `预约已提交（#${created.id}），请留意「我的预约」状态`,
      duration: 3500,
    });
    showApptDialog.value = false;
    await fetchData();
  } finally {
    saving.value = false;
  }
}

async function cancelAppt(a: Appointment) {
  await ElMessageBox.confirm("确定取消该预约？", "取消确认", { type: "warning" });
  await bookingApi.cancelAppointment(a.id);
  ElMessage.success("已取消");
  await fetchData();
}

// ---- 寄养 ----
const showBoardingDialog = ref(false);
const bform = ref({
  pet_id: null as number | null,
  store_id: null as number | null,
  start_date: "",
  end_date: "",
  daily_fee: null as number | null,
  notes: "",
});

function openAddBoarding() {
  bform.value = { pet_id: null, store_id: null, start_date: "", end_date: "", daily_fee: null, notes: "" };
  showBoardingDialog.value = true;
}

async function saveBoarding() {
  if (!bform.value.pet_id) {
    ElMessage.warning("请选择宠物");
    return;
  }
  if (!bform.value.store_id) {
    ElMessage.warning("请选择寄养门店");
    return;
  }
  if (!bform.value.start_date || !bform.value.end_date) {
    ElMessage.warning("请选择寄养起止日期");
    return;
  }
  saving.value = true;
  try {
    const created = await bookingApi.createBoarding({
      pet_id: bform.value.pet_id,
      store_id: bform.value.store_id,
      start_date: bform.value.start_date,
      end_date: bform.value.end_date,
      daily_fee: bform.value.daily_fee,
      notes: bform.value.notes,
    });
    lastTicket.value = {
      id: created.id,
      store: created.store_name || storeName(created.store_id),
      status: created.status,
      kind: "寄养",
    };
    ElMessage.success(`寄养已提交（#${created.id}），可在下方查看状态`);
    showBoardingDialog.value = false;
    await fetchData();
  } finally {
    saving.value = false;
  }
}

async function cancelBoarding(b: Boarding) {
  await ElMessageBox.confirm("确定取消该寄养预订？", "取消确认", { type: "warning" });
  await bookingApi.cancelBoarding(b.id);
  ElMessage.success("已取消");
  await fetchData();
}

const daysOf = (b: Boarding) => {
  const s = new Date(b.start_date).getTime();
  const e = new Date(b.end_date).getTime();
  return Math.max(1, Math.round((e - s) / 86400000) + 1);
};

onMounted(async () => {
  await fetchData();
  applyQueryPrefill();
});

watch(
  () => route.query,
  () => applyQueryPrefill()
);
</script>

<template>
  <div class="page-container">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <div>
        <h2 class="page-title" style="margin: 0 0 4px">预约到店</h2>
        <p class="page-sub" style="margin: 0">预约就诊、美容、寄养或咨询，进度可在下方查看。</p>
      </div>
    </div>

    <el-alert
      v-if="lastTicket"
      type="success"
      :closable="false"
      show-icon
      style="margin-bottom: 12px"
      :title="`已预约「${lastTicket.store}」的${lastTicket.kind}（#${lastTicket.id}），当前待确认`"
    />
    <div class="card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="我的预约" name="appointments">
          <div style="display: flex; justify-content: flex-end; margin-bottom: 12px">
            <el-button size="small" type="primary" @click="openAddAppt">
              <el-icon style="margin-right: 4px"><Plus /></el-icon>新建预约
            </el-button>
          </div>
          <el-table v-if="appointments.length" :data="appointments" style="width: 100%">
            <el-table-column prop="appt_time" label="预约时间" min-width="160" />
            <el-table-column label="类型" width="90">
              <template #default="{ row }">{{ apptTypeLabel(row.appt_type) }}</template>
            </el-table-column>
            <el-table-column label="宠物" width="100">
              <template #default="{ row }">{{ row.pet_name || petName(row.pet_id) }}</template>
            </el-table-column>
            <el-table-column label="对象" min-width="130">
              <template #default="{ row }">{{ partyLabel(row) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusInfo(row.status).type" size="small" effect="light">{{ statusInfo(row.status).label }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="90" align="right">
              <template #default="{ row }">
                <el-button v-if="row.status !== 'cancelled' && row.status !== 'completed'" size="small" type="danger" link @click="cancelAppt(row)">取消</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="暂无预约，点击右上角新建" :image-size="80" />
        </el-tab-pane>

        <el-tab-pane label="寄养预订" name="boardings">
          <div style="display: flex; justify-content: flex-end; margin-bottom: 12px">
            <el-button size="small" type="primary" @click="openAddBoarding">
              <el-icon style="margin-right: 4px"><Plus /></el-icon>预订寄养
            </el-button>
          </div>
          <el-table v-if="boardings.length" :data="boardings" style="width: 100%">
            <el-table-column label="宠物" width="100">
              <template #default="{ row }">{{ row.pet_name || petName(row.pet_id) }}</template>
            </el-table-column>
            <el-table-column prop="start_date" label="开始" width="110" />
            <el-table-column prop="end_date" label="结束" width="110" />
            <el-table-column label="天数" width="70">
              <template #default="{ row }">{{ daysOf(row) }} 天</template>
            </el-table-column>
            <el-table-column label="门店" min-width="130">
              <template #default="{ row }">{{ row.store_name || storeName(row.store_id) }}</template>
            </el-table-column>
            <el-table-column label="费用" width="110">
              <template #default="{ row }">{{ row.daily_fee != null ? `¥${row.daily_fee}/天` : "面议" }}</template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusInfo(row.status).type" size="small" effect="light">{{ statusInfo(row.status).label }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="90" align="right">
              <template #default="{ row }">
                <el-button v-if="row.status !== 'cancelled' && row.status !== 'completed'" size="small" type="danger" link @click="cancelBoarding(row)">取消</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="暂无寄养预订，点击右上角预订" :image-size="80" />
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 预约对话框 -->
    <el-dialog v-model="showApptDialog" title="新建预约" width="500px">
      <el-form label-position="top">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px">
          <el-form-item label="宠物">
            <el-select v-model="aform.pet_id" clearable style="width: 100%" placeholder="选择宠物（可选）">
              <el-option v-for="p in pets" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="预约类型">
            <el-select v-model="aform.appt_type" style="width: 100%">
              <el-option v-for="t in APPT_TYPES" :key="t.value" :label="t.label" :value="t.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="门店" required>
            <el-select v-model="aform.store_id" style="width: 100%" placeholder="就诊请选医院，美容请选宠物店">
              <el-option v-for="s in apptStoreOptions" :key="s.id" :label="`${s.name}（${s.store_type}）`" :value="s.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="预约时间" required>
            <el-date-picker v-model="aform.appt_time" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
          </el-form-item>
        </div>
        <el-form-item label="备注">
          <el-input v-model="aform.notes" type="textarea" :rows="2" placeholder="症状描述、需求等（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showApptDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveAppt">提交预约</el-button>
      </template>
    </el-dialog>

    <!-- 寄养对话框 -->
    <el-dialog v-model="showBoardingDialog" title="预订寄养" width="500px">
      <el-form label-position="top">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px">
          <el-form-item label="宠物" required>
            <el-select v-model="bform.pet_id" style="width: 100%" placeholder="选择宠物">
              <el-option v-for="p in pets" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="门店" required>
            <el-select v-model="bform.store_id" style="width: 100%" placeholder="选择寄养中心或宠物店">
              <el-option v-for="s in boardingStores" :key="s.id" :label="s.name" :value="s.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="开始日期" required>
            <el-date-picker v-model="bform.start_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item label="结束日期" required>
            <el-date-picker v-model="bform.end_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item label="每日费用 (元)">
            <el-input-number v-model="bform.daily_fee" :min="0" :precision="2" style="width: 100%" />
          </el-form-item>
        </div>
        <el-form-item label="备注">
          <el-input v-model="bform.notes" type="textarea" :rows="2" placeholder="喂养习惯、注意事项等" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showBoardingDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveBoarding">提交预订</el-button>
      </template>
    </el-dialog>
  </div>
</template>
