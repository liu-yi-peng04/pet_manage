<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { petsApi, type Pet, type Vaccine } from "@/api/pets";
import type { MedicalExam, Medication } from "@/api/pets";
import { uploadMedia, mediaSrc } from "@/api/media";

const route = useRoute();
const router = useRouter();
const petId = Number(route.params.id);

const pet = ref<Pet | null>(null);
const vaccines = ref<Vaccine[]>([]);
const exams = ref<MedicalExam[]>([]);
const medications = ref<Medication[]>([]);
const loading = ref(false);
const activeTab = ref("vaccines");
const uploading = ref(false);
const detailPhotoInput = ref<HTMLInputElement | null>(null);

const showVaccineDialog = ref(false);
const saving = ref(false);
const editingVid = ref<number | null>(null);
const vform = ref({
  vaccine_name: "",
  dose_no: 1,
  vaccinated_at: "",
  next_due_date: "",
  notes: "",
});

const showExamDialog = ref(false);
const eform = ref({
  exam_date: "",
  hospital: "",
  items: "",
  result: "",
  vet_name: "",
});

const showMedDialog = ref(false);
const mform = ref({
  drug_name: "",
  start_date: "",
  end_date: "",
  dosage: "",
  reason: "",
  notes: "",
});

const speciesLabel = (v: string) =>
  ({ dog: "狗", cat: "猫", other: "其他" } as Record<string, string>)[v] ?? v;
const genderLabel = (v: string) =>
  ({ unknown: "未知", male: "公", female: "母" } as Record<string, string>)[v] ?? v;

const statusOf = (v: Vaccine) => {
  if (!v.next_due_date) return { label: "待定", type: "info" as const };
  const today = new Date();
  const due = new Date(v.next_due_date);
  const days = Math.ceil((due.getTime() - today.getTime()) / 86400000);
  if (days < 0) return { label: `已过期 ${-days} 天`, type: "danger" as const };
  if (days <= 30) return { label: `${days} 天后到期`, type: "warning" as const };
  return { label: "正常", type: "success" as const };
};

const upcoming = computed(() => vaccines.value.filter((v) => statusOf(v).type !== "success"));

async function fetchData() {
  loading.value = true;
  try {
    [pet.value, vaccines.value, exams.value, medications.value] = await Promise.all([
      petsApi.get(petId),
      petsApi.vaccines(petId),
      petsApi.exams(petId),
      petsApi.medications(petId),
    ]);
  } finally {
    loading.value = false;
  }
}

async function onUploadPhoto(ev: Event) {
  const input = ev.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file || !pet.value) return;
  uploading.value = true;
  try {
    const res = await uploadMedia(file, "pet");
    pet.value = await petsApi.update(petId, {
      name: pet.value.name,
      species: pet.value.species,
      breed: pet.value.breed,
      gender: pet.value.gender,
      birth_date: pet.value.birth_date,
      weight_kg: pet.value.weight_kg,
      chip_no: pet.value.chip_no,
      is_neutered: pet.value.is_neutered,
      nickname: pet.value.nickname,
      color: pet.value.color,
      activity_level: pet.value.activity_level,
      diet: pet.value.diet,
      allergies: pet.value.allergies,
      chronic_conditions: pet.value.chronic_conditions,
      temperament: pet.value.temperament,
      living_env: pet.value.living_env,
      city: pet.value.city,
      notes: pet.value.notes,
      image_url: res.url,
    });
    ElMessage.success("照片已保存到数据库");
  } finally {
    uploading.value = false;
    input.value = "";
  }
}

// ---- 疫苗 ----
function openAddVaccine() {
  editingVid.value = null;
  vform.value = { vaccine_name: "", dose_no: 1, vaccinated_at: "", next_due_date: "", notes: "" };
  showVaccineDialog.value = true;
}

function openEditVaccine(v: Vaccine) {
  editingVid.value = v.id;
  vform.value = {
    vaccine_name: v.vaccine_name,
    dose_no: v.dose_no,
    vaccinated_at: v.vaccinated_at,
    next_due_date: v.next_due_date ?? "",
    notes: v.notes,
  };
  showVaccineDialog.value = true;
}

async function saveVaccine() {
  if (!vform.value.vaccine_name.trim()) {
    ElMessage.warning("请输入疫苗名称");
    return;
  }
  if (!vform.value.vaccinated_at) {
    ElMessage.warning("请选择接种日期");
    return;
  }
  const payload = {
    vaccine_name: vform.value.vaccine_name.trim(),
    dose_no: vform.value.dose_no,
    vaccinated_at: vform.value.vaccinated_at,
    next_due_date: vform.value.next_due_date || null,
    notes: vform.value.notes,
  };
  saving.value = true;
  try {
    if (editingVid.value) {
      await petsApi.updateVaccine(editingVid.value, payload);
      ElMessage.success("已更新");
    } else {
      await petsApi.addVaccine(petId, payload);
      ElMessage.success("疫苗记录已添加");
    }
    showVaccineDialog.value = false;
    await fetchData();
  } finally {
    saving.value = false;
  }
}

async function removeVaccine(v: Vaccine) {
  await ElMessageBox.confirm(
    `确定删除「${v.vaccine_name}」第 ${v.dose_no} 针记录？`,
    "删除确认",
    { type: "warning", confirmButtonText: "删除", cancelButtonText: "取消", confirmButtonClass: "el-button--danger" }
  );
  await petsApi.removeVaccine(v.id);
  ElMessage.success("已删除");
  await fetchData();
}

// ---- 体检 ----
function openAddExam() {
  eform.value = { exam_date: "", hospital: "", items: "", result: "", vet_name: "" };
  showExamDialog.value = true;
}

async function saveExam() {
  if (!eform.value.exam_date) {
    ElMessage.warning("请选择体检日期");
    return;
  }
  saving.value = true;
  try {
    await petsApi.addExam(petId, {
      exam_date: eform.value.exam_date,
      hospital: eform.value.hospital || null,
      items: eform.value.items || null,
      result: eform.value.result,
      vet_name: eform.value.vet_name || null,
    });
    ElMessage.success("体检记录已添加");
    showExamDialog.value = false;
    await fetchData();
  } finally {
    saving.value = false;
  }
}

async function removeExam(e: MedicalExam) {
  await ElMessageBox.confirm(`确定删除 ${e.exam_date} 的体检记录？`, "删除确认", {
    type: "warning",
    confirmButtonText: "删除",
    cancelButtonText: "取消",
    confirmButtonClass: "el-button--danger",
  });
  await petsApi.removeExam(petId, e.id);
  ElMessage.success("已删除");
  await fetchData();
}

// ---- 用药 ----
function openAddMed() {
  mform.value = { drug_name: "", start_date: "", end_date: "", dosage: "", reason: "", notes: "" };
  showMedDialog.value = true;
}

async function saveMed() {
  if (!mform.value.drug_name.trim()) {
    ElMessage.warning("请输入药品名称");
    return;
  }
  saving.value = true;
  try {
    await petsApi.addMedication(petId, {
      drug_name: mform.value.drug_name.trim(),
      start_date: mform.value.start_date || null,
      end_date: mform.value.end_date || null,
      dosage: mform.value.dosage || null,
      reason: mform.value.reason || null,
      notes: mform.value.notes,
    });
    ElMessage.success("用药记录已添加");
    showMedDialog.value = false;
    await fetchData();
  } finally {
    saving.value = false;
  }
}

async function removeMed(m: Medication) {
  await ElMessageBox.confirm(`确定删除「${m.drug_name}」用药记录？`, "删除确认", {
    type: "warning",
    confirmButtonText: "删除",
    cancelButtonText: "取消",
    confirmButtonClass: "el-button--danger",
  });
  await petsApi.removeMedication(petId, m.id);
  ElMessage.success("已删除");
  await fetchData();
}

onMounted(fetchData);
</script>

<template>
  <div class="page-container">
    <el-page-header style="margin-bottom: 16px" @back="router.push('/pets')">
      <template #content>
        <span style="font-weight: 600">{{ pet?.name ?? "宠物详情" }}</span>
      </template>
    </el-page-header>

    <div v-loading="loading" style="min-height: 200px">
      <!-- 档案卡 -->
      <div v-if="pet" class="card" style="margin-bottom: 16px">
        <div style="display: flex; gap: 16px; flex-wrap: wrap; align-items: center; margin-bottom: 12px">
          <div style="position: relative; width: 96px; height: 96px; border-radius: 16px; background: #12b88618; color: #0b8a63; display: flex; align-items: center; justify-content: center; overflow: hidden; flex-shrink: 0">
            <img v-if="pet.image_url" :src="mediaSrc(pet.image_url)" :alt="pet.name" style="width: 100%; height: 100%; object-fit: cover" />
            <el-icon v-else :size="36"><component :is="pet.species === 'cat' ? 'Apple' : 'BellFilled'" /></el-icon>
          </div>
          <div style="display: flex; flex-direction: column; gap: 6px">
            <el-button size="small" :loading="uploading" @click="detailPhotoInput?.click()">上传/更换照片</el-button>
            <input ref="detailPhotoInput" type="file" accept="image/jpeg,image/png,image/webp,image/gif" style="display: none" @change="onUploadPhoto" />
          </div>
          <div style="flex: 1; min-width: 200px">
            <div style="display: flex; align-items: center; gap: 8px">
              <span style="font-size: 18px; font-weight: 700">{{ pet.name }}</span>
              <el-tag size="small" effect="plain">{{ speciesLabel(pet.species) }} · {{ genderLabel(pet.gender) }}</el-tag>
              <el-tag v-if="pet.is_neutered" size="small" type="success" effect="plain">已绝育</el-tag>
            </div>
            <div class="text-muted" style="font-size: 13px; margin-top: 4px">
              {{ pet.breed || "未知品种" }}
              <template v-if="pet.nickname"> · 昵称 {{ pet.nickname }}</template>
              <template v-if="pet.color"> · {{ pet.color }}</template>
              <template v-if="pet.birth_date"> · {{ pet.birth_date }}</template>
              <template v-if="pet.city"> · {{ pet.city }}</template>
              <template v-if="pet.chip_no"> · 芯片 {{ pet.chip_no }}</template>
            </div>
            <div class="text-muted" style="font-size: 12px; margin-top: 4px">
              活动量 {{ pet.activity_level || "medium" }}
              <template v-if="pet.living_env"> · 环境 {{ pet.living_env }}</template>
              <template v-if="pet.temperament"> · {{ pet.temperament }}</template>
            </div>
          </div>
          <div style="text-align: center; padding: 0 12px">
            <div style="font-size: 22px; font-weight: 700; color: #0b8a63">{{ pet.weight_kg ?? "-" }}</div>
            <div class="text-muted" style="font-size: 12px">体重 (kg)</div>
          </div>
        </div>
        <p v-if="pet.diet" class="text-secondary" style="font-size: 13px; margin: 8px 0 0">饮食：{{ pet.diet }}</p>
        <p v-if="pet.allergies" class="text-secondary" style="font-size: 13px; margin: 4px 0 0">过敏：{{ pet.allergies }}</p>
        <p v-if="pet.chronic_conditions" class="text-secondary" style="font-size: 13px; margin: 4px 0 0">慢性病：{{ pet.chronic_conditions }}</p>
        <p v-if="pet.notes" class="text-secondary" style="font-size: 13px; margin: 4px 0 0">{{ pet.notes }}</p>
      </div>

      <!-- 页签：疫苗 / 体检 / 用药 -->
      <div class="card">
        <el-tabs v-model="activeTab">
          <!-- 疫苗 -->
          <el-tab-pane label="疫苗记录" name="vaccines">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px">
              <el-alert v-if="upcoming.length" :closable="false" type="warning" show-icon style="flex: 1; margin-right: 12px">
                有 {{ upcoming.length }} 条疫苗即将到期或已过期，请及时安排接种。
              </el-alert>
              <el-button size="small" type="primary" @click="openAddVaccine">
                <el-icon style="margin-right: 4px"><Plus /></el-icon>添加疫苗
              </el-button>
            </div>
            <el-table v-if="vaccines.length" :data="vaccines" style="width: 100%">
              <el-table-column prop="vaccine_name" label="疫苗" min-width="120" />
              <el-table-column prop="dose_no" label="针次" width="70">
                <template #default="{ row }">第 {{ row.dose_no }} 针</template>
              </el-table-column>
              <el-table-column prop="vaccinated_at" label="接种日期" width="120" />
              <el-table-column prop="next_due_date" label="下次到期" width="120">
                <template #default="{ row }">{{ row.next_due_date || "—" }}</template>
              </el-table-column>
              <el-table-column label="状态" width="130">
                <template #default="{ row }">
                  <el-tag :type="statusOf(row).type" size="small" effect="light">{{ statusOf(row).label }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="140" align="right">
                <template #default="{ row }">
                  <el-button size="small" link @click="openEditVaccine(row)">编辑</el-button>
                  <el-button size="small" type="danger" link @click="removeVaccine(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-else description="暂无疫苗记录，点击右上角添加" :image-size="80" />
          </el-tab-pane>

          <!-- 体检 -->
          <el-tab-pane label="体检记录" name="exams">
            <div style="display: flex; justify-content: flex-end; margin-bottom: 12px">
              <el-button size="small" type="primary" @click="openAddExam">
                <el-icon style="margin-right: 4px"><Plus /></el-icon>添加体检
              </el-button>
            </div>
            <el-table v-if="exams.length" :data="exams" style="width: 100%">
              <el-table-column prop="exam_date" label="体检日期" width="120" />
              <el-table-column prop="hospital" label="医院" min-width="130">
                <template #default="{ row }">{{ row.hospital || "—" }}</template>
              </el-table-column>
              <el-table-column prop="items" label="项目" min-width="150">
                <template #default="{ row }">{{ row.items || "—" }}</template>
              </el-table-column>
              <el-table-column prop="result" label="结果" min-width="160">
                <template #default="{ row }">{{ row.result || "—" }}</template>
              </el-table-column>
              <el-table-column prop="vet_name" label="医生" width="100">
                <template #default="{ row }">{{ row.vet_name || "—" }}</template>
              </el-table-column>
              <el-table-column label="操作" width="80" align="right">
                <template #default="{ row }">
                  <el-button size="small" type="danger" link @click="removeExam(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-else description="未做体检" :image-size="80" />
          </el-tab-pane>

          <!-- 用药 -->
          <el-tab-pane label="用药记录" name="medications">
            <div style="display: flex; justify-content: flex-end; margin-bottom: 12px">
              <el-button size="small" type="primary" @click="openAddMed">
                <el-icon style="margin-right: 4px"><Plus /></el-icon>添加用药
              </el-button>
            </div>
            <el-table v-if="medications.length" :data="medications" style="width: 100%">
              <el-table-column prop="drug_name" label="药品" min-width="120" />
              <el-table-column prop="start_date" label="开始" width="110">
                <template #default="{ row }">{{ row.start_date || "—" }}</template>
              </el-table-column>
              <el-table-column prop="end_date" label="结束" width="110">
                <template #default="{ row }">{{ row.end_date || "—" }}</template>
              </el-table-column>
              <el-table-column prop="dosage" label="剂量" width="110">
                <template #default="{ row }">{{ row.dosage || "—" }}</template>
              </el-table-column>
              <el-table-column prop="reason" label="原因" min-width="130">
                <template #default="{ row }">{{ row.reason || "—" }}</template>
              </el-table-column>
              <el-table-column label="操作" width="80" align="right">
                <template #default="{ row }">
                  <el-button size="small" type="danger" link @click="removeMed(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-else description="未使用药物" :image-size="80" />
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>

    <!-- 疫苗对话框 -->
    <el-dialog v-model="showVaccineDialog" :title="editingVid ? '编辑疫苗记录' : '添加疫苗记录'" width="480px">
      <el-form label-position="top">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px">
          <el-form-item label="疫苗名称" required>
            <el-input v-model="vform.vaccine_name" placeholder="如：狂犬疫苗" maxlength="30" />
          </el-form-item>
          <el-form-item label="针次">
            <el-input-number v-model="vform.dose_no" :min="1" :max="20" style="width: 100%" />
          </el-form-item>
          <el-form-item label="接种日期" required>
            <el-date-picker v-model="vform.vaccinated_at" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item label="下次到期日">
            <el-date-picker v-model="vform.next_due_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" placeholder="用于到期提醒" />
          </el-form-item>
        </div>
        <el-form-item label="备注">
          <el-input v-model="vform.notes" type="textarea" :rows="2" placeholder="疫苗批号、接种医院等（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showVaccineDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveVaccine">保存</el-button>
      </template>
    </el-dialog>

    <!-- 体检对话框 -->
    <el-dialog v-model="showExamDialog" title="添加体检记录" width="520px">
      <el-form label-position="top">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px">
          <el-form-item label="体检日期" required>
            <el-date-picker v-model="eform.exam_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item label="医院">
            <el-input v-model="eform.hospital" placeholder="医院名称（可选）" />
          </el-form-item>
          <el-form-item label="体检项目">
            <el-input v-model="eform.items" placeholder="如：血常规、生化、B超" />
          </el-form-item>
          <el-form-item label="医生">
            <el-input v-model="eform.vet_name" placeholder="医生姓名（可选）" />
          </el-form-item>
        </div>
        <el-form-item label="结果摘要">
          <el-input v-model="eform.result" type="textarea" :rows="3" placeholder="体检结果、医嘱等" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showExamDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveExam">保存</el-button>
      </template>
    </el-dialog>

    <!-- 用药对话框 -->
    <el-dialog v-model="showMedDialog" title="添加用药记录" width="520px">
      <el-form label-position="top">
        <el-form-item label="药品名称" required>
          <el-input v-model="mform.drug_name" placeholder="如：阿莫西林" maxlength="50" />
        </el-form-item>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px">
          <el-form-item label="开始日期">
            <el-date-picker v-model="mform.start_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item label="结束日期">
            <el-date-picker v-model="mform.end_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item label="剂量">
            <el-input v-model="mform.dosage" placeholder="如：每次半片" />
          </el-form-item>
          <el-form-item label="用药原因">
            <el-input v-model="mform.reason" placeholder="如：皮肤感染" />
          </el-form-item>
        </div>
        <el-form-item label="备注">
          <el-input v-model="mform.notes" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showMedDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveMed">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
