<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { petsApi, type Pet } from "@/api/pets";
import { uploadMedia, mediaSrc } from "@/api/media";

const router = useRouter();
const pets = ref<Pet[]>([]);
const loading = ref(false);
const showDialog = ref(false);
const saving = ref(false);
const uploading = ref(false);
const editingId = ref<number | null>(null);
const petPhotoInput = ref<HTMLInputElement | null>(null);

const form = ref({
  name: "",
  species: "dog",
  breed: "",
  gender: "unknown",
  birth_date: "",
  weight_kg: null as number | null,
  chip_no: "",
  is_neutered: false,
  nickname: "",
  color: "",
  activity_level: "medium",
  diet: "",
  allergies: "",
  chronic_conditions: "",
  temperament: "",
  living_env: "indoor",
  city: "",
  notes: "",
  image_url: "" as string | null,
});

const speciesOptions = [
  { label: "狗", value: "dog" },
  { label: "猫", value: "cat" },
  { label: "其他", value: "other" },
];
const genderOptions = [
  { label: "未知", value: "unknown" },
  { label: "公", value: "male" },
  { label: "母", value: "female" },
];

const livingOptions = [
  { label: "室内", value: "indoor" },
  { label: "室外", value: "outdoor" },
  { label: "室内外", value: "mixed" },
  { label: "公寓", value: "apartment" },
];
const activityOptions = [
  { label: "低", value: "low" },
  { label: "中", value: "medium" },
  { label: "高", value: "high" },
];
const speciesLabel = (v: string) => speciesOptions.find((o) => o.value === v)?.label ?? v;
const genderLabel = (v: string) => genderOptions.find((o) => o.value === v)?.label ?? v;

function emptyForm() {
  return {
    name: "",
    species: "dog",
    breed: "",
    gender: "unknown",
    birth_date: "",
    weight_kg: null as number | null,
    chip_no: "",
    is_neutered: false,
    nickname: "",
    color: "",
    activity_level: "medium",
    diet: "",
    allergies: "",
    chronic_conditions: "",
    temperament: "",
    living_env: "indoor",
    city: "",
    notes: "",
    image_url: null as string | null,
  };
}

async function fetchPets() {
  loading.value = true;
  try {
    pets.value = await petsApi.list();
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editingId.value = null;
  form.value = emptyForm();
  showDialog.value = true;
}

function openEdit(pet: Pet) {
  editingId.value = pet.id;
  form.value = {
    name: pet.name,
    species: pet.species,
    breed: pet.breed ?? "",
    gender: pet.gender,
    birth_date: pet.birth_date ?? "",
    weight_kg: pet.weight_kg,
    chip_no: pet.chip_no ?? "",
    is_neutered: pet.is_neutered,
    nickname: pet.nickname ?? "",
    color: pet.color ?? "",
    activity_level: pet.activity_level ?? "medium",
    diet: pet.diet ?? "",
    allergies: pet.allergies ?? "",
    chronic_conditions: pet.chronic_conditions ?? "",
    temperament: pet.temperament ?? "",
    living_env: pet.living_env ?? "indoor",
    city: pet.city ?? "",
    notes: pet.notes,
    image_url: pet.image_url ?? null,
  };
  showDialog.value = true;
}

async function onPickPhoto(ev: Event) {
  const input = ev.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  uploading.value = true;
  try {
    const res = await uploadMedia(file, "pet");
    form.value.image_url = res.url;
    ElMessage.success("照片已上传并写入数据库");
  } finally {
    uploading.value = false;
    input.value = "";
  }
}

async function save() {
  if (!form.value.name.trim()) {
    ElMessage.warning("请输入宠物名");
    return;
  }
  const sameName = pets.value.filter(
    (p) => p.name.trim() === form.value.name.trim() && p.id !== editingId.value
  );
  if (sameName.length && !form.value.nickname.trim()) {
    ElMessage.warning("已有同名宠物，请填写昵称（如大旺财/小旺财）以免顾问给错方案");
    return;
  }
  const payload = {
    name: form.value.name.trim(),
    species: form.value.species,
    breed: form.value.breed.trim() || null,
    gender: form.value.gender,
    birth_date: form.value.birth_date || null,
    weight_kg: form.value.weight_kg,
    chip_no: form.value.chip_no.trim() || null,
    is_neutered: form.value.is_neutered,
    nickname: form.value.nickname.trim(),
    color: form.value.color.trim() || null,
    activity_level: form.value.activity_level,
    diet: form.value.diet.trim(),
    allergies: form.value.allergies.trim(),
    chronic_conditions: form.value.chronic_conditions.trim(),
    temperament: form.value.temperament.trim() || null,
    living_env: form.value.living_env,
    city: form.value.city.trim() || null,
    notes: form.value.notes,
    image_url: form.value.image_url || null,
  };
  saving.value = true;
  try {
    if (editingId.value) {
      await petsApi.update(editingId.value, payload);
      ElMessage.success("已更新");
    } else {
      await petsApi.create(payload);
      ElMessage.success("宠物已添加");
    }
    showDialog.value = false;
    await fetchPets();
  } finally {
    saving.value = false;
  }
}

async function remove(pet: Pet) {
  await ElMessageBox.confirm(
    `确定删除宠物「${pet.name}」？其疫苗记录将一并删除，且不可恢复。`,
    "删除确认",
    { type: "warning", confirmButtonText: "删除", cancelButtonText: "取消", confirmButtonClass: "el-button--danger" }
  );
  await petsApi.remove(pet.id);
  ElMessage.success("已删除");
  await fetchPets();
}

onMounted(fetchPets);
</script>

<template>
  <div class="page-container">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <h2 class="page-title" style="margin: 0">我的宠物</h2>
      <el-button type="primary" @click="openCreate">
        <el-icon style="margin-right: 4px"><Plus /></el-icon>添加宠物
      </el-button>
    </div>

    <div v-loading="loading" style="min-height: 200px">
      <div v-if="pets.length" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px">
        <div v-for="pet in pets" :key="pet.id" class="card" style="display: flex; flex-direction: column; transition: box-shadow .2s"
          @mouseenter="($event.currentTarget as HTMLElement).style.boxShadow = 'var(--app-shadow-lg)'"
          @mouseleave="($event.currentTarget as HTMLElement).style.boxShadow = 'var(--app-shadow)'">
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px">
            <div style="width: 56px; height: 56px; border-radius: 12px; background: #12b88618; color: #0b8a63; display: flex; align-items: center; justify-content: center; overflow: hidden; flex-shrink: 0">
              <img v-if="pet.image_url" :src="mediaSrc(pet.image_url)" :alt="pet.name" style="width: 100%; height: 100%; object-fit: cover" />
              <el-icon v-else :size="24"><component :is="pet.species === 'cat' ? 'Apple' : 'BellFilled'" /></el-icon>
            </div>
            <div style="flex: 1; min-width: 0">
              <div style="font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
                {{ pet.name }}<span v-if="pet.nickname" class="text-muted" style="font-weight: 400">（{{ pet.nickname }}）</span>
              </div>
              <div class="text-muted" style="font-size: 12px">{{ speciesLabel(pet.species) }} · {{ genderLabel(pet.gender) }}<template v-if="pet.breed"> · {{ pet.breed }}</template></div>
            </div>
            <el-tag v-if="pet.weight_kg" size="small" effect="plain">{{ pet.weight_kg }} kg</el-tag>
          </div>
          <p class="text-secondary" style="flex: 1; font-size: 13px; line-height: 1.6; margin: 0 0 14px; min-height: 40px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical">
            {{ pet.notes || `${pet.breed || "未知品种"}${pet.allergies ? " · 过敏 " + pet.allergies : ""}${pet.is_neutered ? " · 已绝育" : ""}` }}
          </p>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <span class="text-muted" style="font-size: 12px">建档 {{ pet.created_at.slice(0, 10) }}</span>
            <div>
              <el-button size="small" type="primary" plain @click="router.push(`/pets/${pet.id}`)">详情</el-button>
              <el-button size="small" link @click="openEdit(pet)">编辑</el-button>
              <el-button size="small" type="danger" link @click="remove(pet)">删除</el-button>
            </div>
          </div>
        </div>
      </div>

      <el-empty v-else-if="!loading" description="还没有宠物，点击右上角添加">
        <el-button type="primary" @click="openCreate">添加宠物</el-button>
      </el-empty>
    </div>

    <el-dialog v-model="showDialog" :title="editingId ? '编辑宠物' : '添加宠物'" width="640px">
      <el-form label-position="top">
        <el-form-item label="宠物照片">
          <div style="display: flex; align-items: center; gap: 12px">
            <div style="width: 88px; height: 88px; border-radius: 12px; background: #f3f4f6; overflow: hidden; display: flex; align-items: center; justify-content: center">
              <img v-if="form.image_url" :src="mediaSrc(form.image_url)" alt="预览" style="width: 100%; height: 100%; object-fit: cover" />
              <span v-else class="text-muted" style="font-size: 12px">暂无照片</span>
            </div>
            <div>
              <el-button :loading="uploading" @click="petPhotoInput?.click()">上传照片</el-button>
              <el-button v-if="form.image_url" link type="danger" @click="form.image_url = null">移除</el-button>
              <div class="text-muted" style="font-size: 12px; margin-top: 6px">jpg/png/webp，最大 5MB，保存到数据库</div>
              <input ref="petPhotoInput" type="file" accept="image/jpeg,image/png,image/webp,image/gif" style="display: none" @change="onPickPhoto" />
            </div>
          </div>
        </el-form-item>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px">
          <el-form-item label="宠物名" required>
            <el-input v-model="form.name" placeholder="如：旺财" maxlength="30" />
          </el-form-item>
          <el-form-item label="昵称（同名必填）">
            <el-input v-model="form.nickname" placeholder="家里有两只同名时填写，如大旺财" maxlength="30" />
          </el-form-item>
          <el-form-item label="物种">
            <el-select v-model="form.species" style="width: 100%">
              <el-option v-for="o in speciesOptions" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="品种">
            <el-input v-model="form.breed" placeholder="如：金毛" maxlength="30" />
          </el-form-item>
          <el-form-item label="性别">
            <el-select v-model="form.gender" style="width: 100%">
              <el-option v-for="o in genderOptions" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="毛色">
            <el-input v-model="form.color" placeholder="如：奶油色" maxlength="30" />
          </el-form-item>
          <el-form-item label="生日">
            <el-date-picker v-model="form.birth_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" placeholder="选择日期" />
          </el-form-item>
          <el-form-item label="体重 (kg)">
            <el-input-number v-model="form.weight_kg" :min="0" :max="200" :precision="1" style="width: 100%" placeholder="可空" />
          </el-form-item>
          <el-form-item label="芯片号">
            <el-input v-model="form.chip_no" placeholder="可空" maxlength="30" />
          </el-form-item>
          <el-form-item label="所在城市">
            <el-input v-model="form.city" placeholder="用于匹配附近医院/门店" maxlength="20" />
          </el-form-item>
          <el-form-item label="居住环境">
            <el-select v-model="form.living_env" style="width: 100%">
              <el-option v-for="o in livingOptions" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="活动量">
            <el-select v-model="form.activity_level" style="width: 100%">
              <el-option v-for="o in activityOptions" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="绝育">
            <el-switch v-model="form.is_neutered" active-text="已绝育" />
          </el-form-item>
        </div>
        <el-form-item label="性格">
          <el-input v-model="form.temperament" placeholder="如：亲人、护食、怕生" maxlength="60" />
        </el-form-item>
        <el-form-item label="日常饮食">
          <el-input v-model="form.diet" type="textarea" :rows="2" placeholder="主粮品牌、日喂次数、零食、是否生骨肉" />
        </el-form-item>
        <el-form-item label="过敏史">
          <el-input v-model="form.allergies" placeholder="食物/药物/环境过敏，没有可空" />
        </el-form-item>
        <el-form-item label="慢性病/既往史">
          <el-input v-model="form.chronic_conditions" placeholder="如：胰腺炎、心脏病、皮肤病" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" placeholder="其他需要顾问知道的情况" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
