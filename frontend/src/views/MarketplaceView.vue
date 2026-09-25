<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { marketplaceApi } from "@/api/marketplace";
import type { PetListing } from "@/types";
import { mediaSrc } from "@/api/media";

const router = useRouter();
const list = ref<PetListing[]>([]);
const loading = ref(false);
const species = ref("");
const keyword = ref("");
const detail = ref<PetListing | null>(null);

const APPEAR: Record<string, string> = {
  premium: "精品",
  standard: "标准",
  fair: "合格",
  sale: "特价",
};
const genderLabel = (g: string) => ({ male: "公", female: "母", unknown: "未填" }[g] ?? g);
const ageText = (m: number | null | undefined) => {
  if (m == null) return "月龄未知";
  if (m < 12) return `${m} 月龄`;
  const y = Math.floor(m / 12);
  const rest = m % 12;
  return rest ? `${y} 岁 ${rest} 个月` : `${y} 岁`;
};
const cover = (p: PetListing) =>
  mediaSrc(
    p.image_url,
    p.species === "cat"
      ? "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=800&q=80"
      : "https://images.unsplash.com/photo-1552053831-71594a27632d?w=800&q=80"
  );

function onCoverError(ev: Event, species?: string) {
  const img = ev.target as HTMLImageElement;
  if (img.dataset.fallback) return;
  img.dataset.fallback = "1";
  img.src =
    species === "cat"
      ? "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=800&q=80"
      : "https://images.unsplash.com/photo-1552053831-71594a27632d?w=800&q=80";
}

function bookSee(p: PetListing) {
  const q = new URLSearchParams({
    appt_type: "consult",
    store_id: String(p.store_id ?? ""),
    listing: p.name,
    notes: `想看宠：${p.name}（${p.breed || ""}）`,
  });
  router.push(`/booking?${q.toString()}`);
}

async function load() {
  loading.value = true;
  try {
    list.value = await marketplaceApi.listings({
      species: species.value || undefined,
      keyword: keyword.value || undefined,
    });
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="page-container">
    <div class="hero-banner" style="margin-bottom: 16px; padding: 18px 20px">
      <h2 style="font-size: 20px">选宠市场</h2>
      <p>看图、比价、看品相，心动了就预约到店看宠。</p>
    </div>

    <div style="display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap">
      <el-radio-group v-model="species" @change="load">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="dog">犬</el-radio-button>
        <el-radio-button value="cat">猫</el-radio-button>
      </el-radio-group>
      <el-input v-model="keyword" placeholder="搜品种 / 名字" clearable style="width: 240px" @keyup.enter="load" @clear="load">
        <template #append><el-button type="primary" @click="load">搜索</el-button></template>
      </el-input>
    </div>

    <div v-loading="loading" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px">
      <div v-for="p in list" :key="p.id" class="goods-card" @click="detail = p">
        <div style="height: 168px; background: #f3f4f6; overflow: hidden; position: relative">
          <img
            :src="cover(p)"
            :alt="p.name"
            style="width: 100%; height: 100%; object-fit: cover; display: block"
            loading="lazy"
            @error="(e) => onCoverError(e, p.species)"
          />
          <span class="brand-chip" style="position: absolute; left: 10px; top: 10px">
            {{ APPEAR[p.appearance || "standard"] || "在售" }}
          </span>
        </div>
        <div style="padding: 12px 14px 14px">
          <div style="font-weight: 700; margin-bottom: 4px">{{ p.name }}</div>
          <div class="text-muted" style="font-size: 12px; margin-bottom: 8px">
            {{ p.breed || "品种未填" }} · {{ ageText(p.age_months) }}
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px">
            <div class="price-tag"><small>¥</small>{{ p.price != null ? p.price : "面议" }}</div>
            <span class="text-muted" style="font-size: 12px">{{ p.store_name }}</span>
          </div>
          <el-button type="primary" style="width: 100%" @click.stop="bookSee(p)">预约看宠</el-button>
        </div>
      </div>
    </div>
    <el-empty v-if="!loading && !list.length" description="暂无在售宠物" />

    <el-drawer :model-value="!!detail" :title="detail?.name" size="420px" @close="detail = null">
      <div v-if="detail">
        <img
          :src="cover(detail)"
          :alt="detail.name"
          style="width: 100%; height: 220px; object-fit: cover; border-radius: 12px; margin-bottom: 14px"
          @error="(e) => onCoverError(e, detail.species)"
        />
        <div class="price-tag" style="margin-bottom: 12px"><small>¥</small>{{ detail.price != null ? detail.price : "面议" }}</div>
        <p>
          <el-tag size="small">{{ detail.species === "cat" ? "猫" : "犬" }}</el-tag>
          <el-tag size="small" type="warning" effect="dark" style="margin-left: 6px">{{ APPEAR[detail.appearance || "standard"] }}</el-tag>
        </p>
        <p>品种 {{ detail.breed || "未填" }} · {{ genderLabel(detail.gender) }}</p>
        <p>年龄 {{ ageText(detail.age_months) }}<template v-if="detail.weight_kg"> · 体重 {{ detail.weight_kg }} kg</template></p>
        <p v-if="detail.color">毛色 {{ detail.color }}</p>
        <p>疫苗：{{ detail.vaccine_note || "未填" }}</p>
        <p>健康：{{ detail.health_note || "未填" }}</p>
        <p style="line-height: 1.7">{{ detail.description || "暂无介绍" }}</p>
        <el-divider />
        <p style="font-weight: 700">{{ detail.store_name }}</p>
        <p class="text-muted" style="font-size: 13px">
          {{ detail.store_city }} {{ detail.store_address }}<br />
          {{ detail.store_phone || "暂无电话" }} · 评分 {{ detail.store_rating ?? "—" }}
        </p>
        <el-button type="primary" size="large" style="width: 100%; margin-top: 12px" @click="bookSee(detail)">
          预约到该店看宠
        </el-button>
      </div>
    </el-drawer>
  </div>
</template>
