<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { ElMessage, ElNotification } from "element-plus";
import { marketplaceApi } from "@/api/marketplace";
import { bookingApi, type Appointment } from "@/api/booking";
import { petsApi, type Pet } from "@/api/pets";
import { uploadMedia, mediaSrc } from "@/api/media";
import { useUserStore } from "@/stores/user";
import type { Trainer } from "@/types";

const MAX_PROOF = 8;

const user = useUserStore();
const list = ref<Trainer[]>([]);
const mine = ref<Trainer | null>(null);
const loading = ref(false);
const saving = ref(false);
const avatarInput = ref<HTMLInputElement | null>(null);
const proofInput = ref<HTMLInputElement | null>(null);
const form = ref({
  display_name: "",
  city: "上海",
  specialties: "",
  years: 1,
  price_from: 300 as number | null,
  service_mode: "both",
  bio: "",
  avatar_url: null as string | null,
  experience: "",
  cert_note: "",
  proof_images: [] as string[],
});

const pets = ref<Pet[]>([]);
const showBook = ref(false);
const booking = ref(false);
const bookTarget = ref<Trainer | null>(null);
const bookForm = ref({
  pet_id: null as number | null,
  appt_time: "",
  notes: "",
});

const showProfile = ref(false);
const profileTarget = ref<Trainer | null>(null);

const inbox = ref<Appointment[]>([]);
const inboxFilter = ref("pending");
const inboxLoading = ref(false);
const knownPending = ref<Set<number> | null>(null);
let pollTimer: ReturnType<typeof setInterval> | null = null;

const pendingCount = computed(() => inbox.value.filter((a) => a.status === "pending").length);
const trustReady = computed(
  () => !!(form.value.experience.trim() || form.value.cert_note.trim() || form.value.proof_images.length),
);

function fillForm(t: Trainer) {
  form.value = {
    display_name: t.display_name,
    city: t.city || "",
    specialties: t.specialties,
    years: t.years,
    price_from: t.price_from,
    service_mode: t.service_mode,
    bio: t.bio,
    avatar_url: t.avatar_url || null,
    experience: t.experience || "",
    cert_note: t.cert_note || "",
    proof_images: [...(t.proof_images || [])],
  };
}

async function load() {
  loading.value = true;
  try {
    list.value = await marketplaceApi.trainers({ verified_only: !user.isTrainer });
    if (user.isTrainer) {
      mine.value = await marketplaceApi.myTrainer();
      if (mine.value) fillForm(mine.value);
      await fetchInbox();
    } else if (user.isEndUser || user.userInfo?.role === "user") {
      pets.value = await petsApi.list();
    }
  } finally {
    loading.value = false;
  }
}

async function save() {
  if (!form.value.display_name.trim()) {
    ElMessage.warning("请填写展示名");
    return;
  }
  if (!form.value.experience.trim() && !form.value.proof_images.length) {
    ElMessage.warning("请至少填写从业经历，或上传证书/案例证明图，方便用户信任你");
    return;
  }
  saving.value = true;
  try {
    mine.value = await marketplaceApi.saveTrainer({ ...form.value });
    ElMessage.success(mine.value.verified ? "主页已更新" : "已保存，等待平台审核后对外展示");
    await load();
  } finally {
    saving.value = false;
  }
}

async function onAvatarChange(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  uploadingAvatar.value = true;
  try {
    const res = await uploadMedia(file, "trainer");
    form.value.avatar_url = res.url;
    ElMessage.success("头像已上传");
  } finally {
    uploadingAvatar.value = false;
    input.value = "";
  }
}

async function onProofChange(e: Event) {
  const input = e.target as HTMLInputElement;
  const files = Array.from(input.files || []);
  if (!files.length) return;
  const room = MAX_PROOF - form.value.proof_images.length;
  if (room <= 0) {
    ElMessage.warning(`证明图最多 ${MAX_PROOF} 张`);
    input.value = "";
    return;
  }
  uploadingProof.value = true;
  try {
    for (const file of files.slice(0, room)) {
      const res = await uploadMedia(file, "trainer");
      form.value.proof_images.push(res.url);
    }
    ElMessage.success("证明图已上传");
  } finally {
    uploadingProof.value = false;
    input.value = "";
  }
}

function removeProof(idx: number) {
  form.value.proof_images.splice(idx, 1);
}

function openProfile(t: Trainer) {
  profileTarget.value = t;
  showProfile.value = true;
}

function openBook(t: Trainer) {
  if (!user.isEndUser && user.userInfo?.role !== "user") {
    ElMessage.warning("请使用养宠用户账号预约训犬师");
    return;
  }
  bookTarget.value = t;
  bookForm.value = {
    pet_id: pets.value[0]?.id ?? null,
    appt_time: "",
    notes: "",
  };
  showBook.value = true;
}

function bookFromProfile() {
  if (!profileTarget.value) return;
  showProfile.value = false;
  openBook(profileTarget.value);
}

async function submitBook() {
  if (!bookTarget.value) return;
  if (!bookForm.value.appt_time) {
    ElMessage.warning("请选择上课时间");
    return;
  }
  booking.value = true;
  try {
    const created = await bookingApi.createAppointment({
      appt_type: "train",
      trainer_id: bookTarget.value.id,
      pet_id: bookForm.value.pet_id,
      appt_time: new Date(bookForm.value.appt_time).toISOString(),
      notes: bookForm.value.notes || `预约训练：${bookTarget.value.display_name}`,
    });
    ElMessage.success(`预约已提交（#${created.id}），等待「${bookTarget.value.display_name}」确认`);
    showBook.value = false;
  } finally {
    booking.value = false;
  }
}

async function fetchInbox() {
  if (!user.isTrainer) return;
  inboxLoading.value = true;
  try {
    const status = inboxFilter.value || undefined;
    inbox.value = await bookingApi.trainerAppointments(status);
    const pending = await bookingApi.trainerAppointments("pending");
    if (knownPending.value === null) {
      knownPending.value = new Set(pending.map((a) => a.id));
    } else {
      const fresh = pending.filter((a) => !knownPending.value!.has(a.id));
      for (const a of fresh) {
        knownPending.value.add(a.id);
        ElNotification({
          title: "新训练预约",
          message: `${a.user_name || "用户"} · ${a.pet_name || "未指定宠物"} · ${new Date(a.appt_time).toLocaleString("zh-CN")}`,
          type: "warning",
          duration: 0,
        });
      }
      knownPending.value = new Set(pending.map((a) => a.id));
    }
  } finally {
    inboxLoading.value = false;
  }
}

async function setStatus(a: Appointment, status: string) {
  await bookingApi.trainerSetStatus(a.id, status);
  ElMessage.success("已更新");
  await fetchInbox();
}

function snippet(text: string | undefined, n = 72) {
  const s = (text || "").replace(/\s+/g, " ").trim();
  if (!s) return "";
  return s.length > n ? `${s.slice(0, n)}…` : s;
}

onMounted(async () => {
  await load();
  if (user.isTrainer) {
    pollTimer = setInterval(() => void fetchInbox(), 8000);
  }
});

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer);
});
</script>

<template>
  <div class="page-container" v-loading="loading">
    <div class="hero-banner" style="margin-bottom: 16px; padding: 18px 20px">
      <h2 style="font-size: 20px">{{ user.isTrainer ? "训犬师工作台" : "训犬师市场" }}</h2>
      <p v-if="user.isTrainer">
        接收预约之外，还要完善<strong>经历与证明</strong>——用户靠这些决定是否信任并预约你。
      </p>
      <p v-else>浏览教练经历与案例，满意后预约训练。</p>
    </div>

    <template v-if="user.isTrainer">
      <div class="loop-strip" style="margin-top: 0">
        <strong>待办</strong>
        <span>确认新预约</span>
        <span>→</span>
        <span>完成课时</span>
        <el-tag v-if="pendingCount" type="danger" effect="dark" size="small" style="margin-left: 8px">
          待确认 {{ pendingCount }}
        </el-tag>
      </div>

      <div class="card" style="padding: 16px; margin-bottom: 16px">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px">
          <div style="font-weight: 700">预约接收台</div>
          <el-radio-group v-model="inboxFilter" size="small" @change="fetchInbox">
            <el-radio-button value="pending">待确认</el-radio-button>
            <el-radio-button value="confirmed">已确认</el-radio-button>
            <el-radio-button value="">全部</el-radio-button>
          </el-radio-group>
        </div>
        <el-table v-loading="inboxLoading" :data="inbox" style="width: 100%">
          <el-table-column label="时间" min-width="150">
            <template #default="{ row }">{{ new Date(row.appt_time).toLocaleString("zh-CN", { hour12: false }).slice(0, 16) }}</template>
          </el-table-column>
          <el-table-column prop="user_name" label="客户" width="100" />
          <el-table-column prop="pet_name" label="宠物" width="100">
            <template #default="{ row }">{{ row.pet_name || "—" }}</template>
          </el-table-column>
          <el-table-column prop="notes" label="备注" min-width="140">
            <template #default="{ row }">{{ row.notes || "—" }}</template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="90" />
          <el-table-column label="操作" width="180" align="right">
            <template #default="{ row }">
              <template v-if="row.status === 'pending'">
                <el-button size="small" type="primary" link @click="setStatus(row, 'confirmed')">接单</el-button>
                <el-button size="small" type="danger" link @click="setStatus(row, 'cancelled')">婉拒</el-button>
              </template>
              <el-button
                v-else-if="row.status === 'confirmed'"
                size="small"
                type="success"
                link
                @click="setStatus(row, 'completed')"
              >完成课时</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!inboxLoading && !inbox.length" description="暂无训练预约" :image-size="70" />
      </div>

      <div class="card" style="padding: 16px; margin-bottom: 16px">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px">
          <div style="font-weight: 600">
            我的主页 {{ mine?.verified ? "· 已审核（用户可约）" : "· 待审核（暂不可约）" }}
          </div>
          <el-tag :type="trustReady ? 'success' : 'warning'" size="small" effect="plain">
            {{ trustReady ? "信任材料已填写" : "建议补充经历/证明图" }}
          </el-tag>
        </div>
        <el-form label-position="top">
          <el-form-item label="头像">
            <div style="display: flex; align-items: center; gap: 12px">
              <div
                style="
                  width: 72px;
                  height: 72px;
                  border-radius: 50%;
                  overflow: hidden;
                  background: #f3f4f6;
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  flex-shrink: 0;
                "
              >
                <img
                  v-if="form.avatar_url"
                  :src="mediaSrc(form.avatar_url)"
                  alt="头像"
                  style="width: 100%; height: 100%; object-fit: cover"
                />
                <span v-else style="font-size: 12px; color: #9ca3af">未上传</span>
              </div>
              <div>
                <input ref="avatarInput" type="file" accept="image/*" hidden @change="onAvatarChange" />
                <el-button :loading="uploadingAvatar" @click="avatarInput?.click()">上传头像</el-button>
                <el-button v-if="form.avatar_url" link type="danger" @click="form.avatar_url = null">清除</el-button>
              </div>
            </div>
          </el-form-item>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px">
            <el-form-item label="展示名"><el-input v-model="form.display_name" /></el-form-item>
            <el-form-item label="城市"><el-input v-model="form.city" /></el-form-item>
            <el-form-item label="擅长"><el-input v-model="form.specialties" placeholder="拆家,服从,金毛" /></el-form-item>
            <el-form-item label="起步价">
              <el-input-number v-model="form.price_from" :min="0" style="width: 100%" />
            </el-form-item>
            <el-form-item label="从业年限">
              <el-input-number v-model="form.years" :min="0" :max="50" style="width: 100%" />
            </el-form-item>
            <el-form-item label="服务方式">
              <el-select v-model="form.service_mode" style="width: 100%">
                <el-option label="上门" value="home" />
                <el-option label="场地" value="studio" />
                <el-option label="上门/场地" value="both" />
              </el-select>
            </el-form-item>
          </div>
          <el-form-item label="一句话简介"><el-input v-model="form.bio" type="textarea" :rows="2" /></el-form-item>
          <el-form-item label="从业经历（必填其一）" required>
            <el-input
              v-model="form.experience"
              type="textarea"
              :rows="5"
              placeholder="按时间线写：在哪工作、带过什么课、大概个案量、擅长问题……用户会据此判断是否靠谱"
            />
          </el-form-item>
          <el-form-item label="证书 / 资质说明">
            <el-input
              v-model="form.cert_note"
              type="textarea"
              :rows="2"
              placeholder="如：CPDT 认证、协会会员、比赛名次等"
            />
          </el-form-item>
          <el-form-item :label="`证书与案例证明图（最多 ${MAX_PROOF} 张）`">
            <div style="display: flex; flex-wrap: wrap; gap: 10px; align-items: center">
              <div
                v-for="(url, idx) in form.proof_images"
                :key="url + idx"
                style="position: relative; width: 88px; height: 88px; border-radius: 8px; overflow: hidden; background: #f3f4f6"
              >
                <img :src="mediaSrc(url)" alt="证明" style="width: 100%; height: 100%; object-fit: cover" />
                <el-button
                  size="small"
                  type="danger"
                  circle
                  style="position: absolute; top: 4px; right: 4px; padding: 4px"
                  @click="removeProof(idx)"
                >×</el-button>
              </div>
              <label v-if="form.proof_images.length < MAX_PROOF" style="cursor: pointer">
                <input ref="proofInput" type="file" accept="image/*" multiple hidden @change="onProofChange" />
                <div
                  style="
                    width: 88px;
                    height: 88px;
                    border: 1px dashed #d1d5db;
                    border-radius: 8px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: #6b7280;
                    font-size: 12px;
                    text-align: center;
                    padding: 8px;
                  "
                  @click="proofInput?.click()"
                >
                  {{ uploadingProof ? "上传中…" : "点击上传" }}
                </div>
              </label>
            </div>
            <div class="text-muted" style="font-size: 12px; margin-top: 6px">
              建议上传：证书照片、训练前后对比、场地实拍
            </div>
          </el-form-item>
          <el-button type="primary" :loading="saving" @click="save">保存主页与经历</el-button>
        </el-form>
      </div>
    </template>

    <div v-if="!user.isTrainer" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px">
      <div v-for="t in list" :key="t.id" class="goods-card" style="padding: 16px; cursor: default">
        <div style="display: flex; gap: 12px; align-items: flex-start">
          <div
            style="
              width: 56px;
              height: 56px;
              border-radius: 50%;
              overflow: hidden;
              background: #f3f4f6;
              flex-shrink: 0;
              display: flex;
              align-items: center;
              justify-content: center;
            "
          >
            <img
              v-if="t.avatar_url"
              :src="mediaSrc(t.avatar_url)"
              alt=""
              style="width: 100%; height: 100%; object-fit: cover"
            />
            <span v-else style="font-size: 18px; font-weight: 700; color: #f59e0b">{{ t.display_name.slice(0, 1) }}</span>
          </div>
          <div style="flex: 1; min-width: 0">
            <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px">
              <strong>{{ t.display_name }}</strong>
              <el-tag v-if="t.verified" size="small" type="success">已认证</el-tag>
            </div>
            <div class="text-muted" style="font-size: 12px; margin: 4px 0">
              {{ t.city }} · {{ t.years }} 年 ·
              {{ t.service_mode === "home" ? "上门" : t.service_mode === "studio" ? "场地" : "上门/场地" }}
            </div>
          </div>
        </div>
        <div style="font-size: 13px; margin: 10px 0 6px">{{ t.specialties }}</div>
        <p v-if="t.experience" style="font-size: 13px; color: var(--app-text-secondary); margin: 0 0 8px; line-height: 1.5">
          {{ snippet(t.experience) }}
        </p>
        <p v-else style="font-size: 13px; color: var(--app-text-secondary); margin: 0 0 8px">{{ t.bio }}</p>
        <div v-if="t.proof_images?.length" style="display: flex; gap: 6px; margin-bottom: 10px; overflow: hidden">
          <img
            v-for="(url, i) in t.proof_images.slice(0, 3)"
            :key="i"
            :src="mediaSrc(url)"
            alt=""
            style="width: 56px; height: 56px; object-fit: cover; border-radius: 6px"
          />
          <span v-if="t.proof_images.length > 3" class="text-muted" style="font-size: 12px; align-self: center">+{{ t.proof_images.length - 3 }}</span>
        </div>
        <div v-else-if="t.cert_note" class="text-muted" style="font-size: 12px; margin-bottom: 10px">资质：{{ snippet(t.cert_note, 40) }}</div>
        <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap">
          <div class="price-tag" style="font-size: 18px">
            {{ t.price_from != null ? `¥${t.price_from} 起` : "面议" }}
          </div>
          <div style="display: flex; gap: 8px">
            <el-button @click="openProfile(t)">查看经历</el-button>
            <el-button type="primary" @click="openBook(t)">预约训练</el-button>
          </div>
        </div>
      </div>
      <el-empty v-if="!list.length" description="暂无已审核训犬师" />
    </div>

    <el-dialog v-model="showProfile" :title="profileTarget?.display_name || '教练经历'" width="560px">
      <template v-if="profileTarget">
        <div style="display: flex; gap: 14px; margin-bottom: 14px">
          <div
            style="
              width: 72px;
              height: 72px;
              border-radius: 50%;
              overflow: hidden;
              background: #f3f4f6;
              flex-shrink: 0;
              display: flex;
              align-items: center;
              justify-content: center;
            "
          >
            <img
              v-if="profileTarget.avatar_url"
              :src="mediaSrc(profileTarget.avatar_url)"
              alt=""
              style="width: 100%; height: 100%; object-fit: cover"
            />
            <span v-else style="font-weight: 700; color: #f59e0b">{{ profileTarget.display_name.slice(0, 1) }}</span>
          </div>
          <div>
            <div style="font-weight: 700; margin-bottom: 4px">
              {{ profileTarget.display_name }}
              <el-tag v-if="profileTarget.verified" size="small" type="success" style="margin-left: 6px">已认证</el-tag>
            </div>
            <div class="text-muted" style="font-size: 13px">
              {{ profileTarget.city }} · {{ profileTarget.years }} 年经验 · {{ profileTarget.specialties }}
            </div>
            <p v-if="profileTarget.bio" style="margin: 8px 0 0; font-size: 13px">{{ profileTarget.bio }}</p>
          </div>
        </div>
        <div style="margin-bottom: 14px">
          <div style="font-weight: 600; margin-bottom: 6px">从业经历</div>
          <pre
            v-if="profileTarget.experience"
            style="white-space: pre-wrap; font-family: inherit; margin: 0; font-size: 13px; line-height: 1.6; color: var(--app-text-secondary)"
          >{{ profileTarget.experience }}</pre>
          <div v-else class="text-muted" style="font-size: 13px">教练尚未填写详细经历</div>
        </div>
        <div v-if="profileTarget.cert_note" style="margin-bottom: 14px">
          <div style="font-weight: 600; margin-bottom: 6px">证书 / 资质</div>
          <p style="margin: 0; font-size: 13px; line-height: 1.6">{{ profileTarget.cert_note }}</p>
        </div>
        <div v-if="profileTarget.proof_images?.length">
          <div style="font-weight: 600; margin-bottom: 8px">证明图</div>
          <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 8px">
            <a
              v-for="(url, i) in profileTarget.proof_images"
              :key="i"
              :href="mediaSrc(url)"
              target="_blank"
              rel="noopener"
            >
              <img :src="mediaSrc(url)" alt="证明" style="width: 100%; height: 100px; object-fit: cover; border-radius: 8px" />
            </a>
          </div>
        </div>
      </template>
      <template #footer>
        <el-button @click="showProfile = false">关闭</el-button>
        <el-button type="primary" @click="bookFromProfile">预约这位教练</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showBook" :title="`预约 · ${bookTarget?.display_name || ''}`" width="460px">
      <el-form label-position="top">
        <el-form-item label="宠物（可选）">
          <el-select v-model="bookForm.pet_id" clearable style="width: 100%" placeholder="选择宠物">
            <el-option v-for="p in pets" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="上课时间" required>
          <el-date-picker
            v-model="bookForm.appt_time"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%"
            placeholder="选择时间"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="bookForm.notes" type="textarea" :rows="2" placeholder="行为问题、上门地址等" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showBook = false">取消</el-button>
        <el-button type="primary" :loading="booking" @click="submitBook">提交给教练</el-button>
      </template>
    </el-dialog>
  </div>
</template>
