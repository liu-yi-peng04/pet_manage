<script setup lang="ts">
import { ref } from "vue";
import { ElMessage } from "element-plus";
import { marketplaceApi } from "@/api/marketplace";
import { uploadMedia, mediaSrc } from "@/api/media";
import type { PetListing } from "@/types";

// 拆分前模板已使用这两个状态，但脚本未声明；补上后待售列表才能编译并展示。
const listings = ref<PetListing[]>([]);
const listingLoading = ref(false);
const listingPhotoInput = ref<HTMLInputElement | null>(null);
const listingUploading = ref(false);
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

async function reload() {
  listingLoading.value = true;
  try {
    listings.value = await marketplaceApi.storeListings();
  } finally {
    listingLoading.value = false;
  }
}

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

async function addListing() {
  if (!listingForm.value.name) return;
  await marketplaceApi.createListing(listingForm.value);
  ElMessage.success("已上架");
  await reload();
}

defineExpose({ reload });
</script>

<template>
  <div>
  <el-alert
    type="info"
    :closable="false"
    show-icon
    style="margin-bottom: 12px"
    title="本店代售/待售宠（上架管理）。用户端「选宠市场」是浏览与咨询入口，展示卡片与本表字段侧重点不同。"
  />
  <div class="panel-form">
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
    <el-button type="primary" round @click="addListing">上架</el-button>
  </div>
  <div class="sheet" v-loading="listingLoading">
  <el-table v-if="listings.length" :data="listings">
    <el-table-column label="照片" width="76">
      <template #default="{ row }">
        <img v-if="row.image_url" :src="mediaSrc(row.image_url)" alt="" style="width: 44px; height: 44px; object-fit: cover; border-radius: 10px" />
        <span v-else class="text-muted">—</span>
      </template>
    </el-table-column>
    <el-table-column prop="name" label="名字" />
    <el-table-column prop="breed" label="品种">
      <template #default="{ row }"><span class="meta-cell">{{ row.breed || "—" }}</span></template>
    </el-table-column>
    <el-table-column prop="age_months" label="月龄" width="80">
      <template #default="{ row }"><span class="meta-cell">{{ row.age_months }}</span></template>
    </el-table-column>
    <el-table-column prop="appearance" label="品相" width="80" />
    <el-table-column prop="price" label="价格">
      <template #default="{ row }"><span class="money-cell">{{ row.price != null ? `¥${row.price}` : "面议" }}</span></template>
    </el-table-column>
    <el-table-column prop="vaccine_note" label="疫苗">
      <template #default="{ row }"><span class="meta-cell">{{ row.vaccine_note || "—" }}</span></template>
    </el-table-column>
  </el-table>
  <el-empty v-else-if="!listingLoading" class="soft-empty" :image-size="84">
    <template #description>
      <p class="empty-title">还没有待售宠物</p>
      <p class="empty-desc">填写上方信息并上架后，会出现在选宠市场。</p>
    </template>
  </el-empty>
  </div>
  </div>
</template>
