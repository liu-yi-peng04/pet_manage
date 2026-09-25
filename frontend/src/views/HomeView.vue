<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { marketplaceApi } from "@/api/marketplace";
import { storeApi, type Product } from "@/api/store";
import type { PetListing } from "@/types";
import { mediaSrc } from "@/api/media";
import { useUserStore } from "@/stores/user";

const router = useRouter();
const user = useUserStore();
const hotListings = ref<PetListing[]>([]);
const hotProducts = ref<Product[]>([]);
const loading = ref(false);

const quicks = [
  { label: "选宠看猫狗", path: "/listings", color: "linear-gradient(135deg,#ff6a00,#ff9a4d)", icon: "Present" },
  { label: "用品商城", path: "/store", color: "linear-gradient(135deg,#ffd100,#ffb800)", icon: "ShoppingBag", dark: true },
  { label: "预约医院", path: "/booking?appt_type=exam", color: "linear-gradient(135deg,#00b578,#34d399)", icon: "Calendar" },
  { label: "预约美容", path: "/booking?appt_type=grooming", color: "linear-gradient(135deg,#3b82f6,#60a5fa)", icon: "Brush" },
  { label: "训犬师", path: "/trainers", color: "linear-gradient(135deg,#f59e0b,#fbbf24)", icon: "Trophy", dark: true },
  { label: "寄养托管", path: "/booking?tab=boardings", color: "linear-gradient(135deg,#8b5cf6,#a78bfa)", icon: "House" },
  { label: "AI 顾问", path: "/chat", color: "linear-gradient(135deg,#f43f5e,#fb7185)", icon: "ChatDotRound" },
  { label: "我的宠物", path: "/pets", color: "linear-gradient(135deg,#0ea5e9,#38bdf8)", icon: "BellFilled" },
  { label: "我的订单", path: "/orders", color: "linear-gradient(135deg,#64748b,#94a3b8)", icon: "List" },
];

const cover = (p: PetListing) =>
  mediaSrc(
    p.image_url,
    p.species === "cat"
      ? "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=800&q=80"
      : "https://images.unsplash.com/photo-1552053831-71594a27632d?w=800&q=80"
  );

function go(path: string) {
  router.push(path);
}

function bookListing(p: PetListing) {
  const q = new URLSearchParams({
    appt_type: "consult",
    store_id: String(p.store_id ?? ""),
    listing: p.name,
    notes: `想看宠：${p.name}（${p.breed || p.species}）`,
  });
  router.push(`/booking?${q.toString()}`);
}

onMounted(async () => {
  loading.value = true;
  try {
    const [listings, products] = await Promise.all([
      marketplaceApi.listings({}),
      storeApi.products({}),
    ]);
    hotListings.value = listings.slice(0, 4);
    hotProducts.value = products.slice(0, 4);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="page-container" v-loading="loading">
    <div class="hero-banner fade-up">
      <span class="brand-chip" style="margin-bottom: 10px">宠智联</span>
      <h2>嗨，{{ user.username || "养宠人" }}，今天想做什么？</h2>
      <p>选宠、买粮、预约医院或找训犬师，一站搞定。</p>
    </div>

    <div class="section-head fade-up fade-up-delay-1">
      <h3>常用服务</h3>
    </div>
    <div class="quick-grid fade-up fade-up-delay-2">
      <div v-for="q in quicks" :key="q.path" class="quick-item" @click="go(q.path)">
        <div class="qi-icon" :style="{ background: q.color, color: q.dark ? '#1a1a1a' : '#fff' }">
          <el-icon><component :is="q.icon" /></el-icon>
        </div>
        <div class="qi-label">{{ q.label }}</div>
      </div>
    </div>

    <div class="section-head fade-up fade-up-delay-2">
      <h3>热门待售</h3>
      <span class="more" @click="go('/listings')">全部选宠 ›</span>
    </div>
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px" class="fade-up fade-up-delay-3">
      <div v-for="p in hotListings" :key="p.id" class="goods-card" @click="go('/listings')">
        <div style="height: 120px; background: #f0f0f0">
          <img :src="cover(p)" :alt="p.name" style="width: 100%; height: 100%; object-fit: cover; display: block" loading="lazy" />
        </div>
        <div style="padding: 10px 12px 12px">
          <div style="font-weight: 600; font-size: 13px; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">
            {{ p.name }}
          </div>
          <div class="price-tag" style="font-size: 16px; margin-bottom: 8px">
            <small>¥</small>{{ p.price != null ? p.price : "面议" }}
          </div>
          <el-button type="primary" size="small" style="width: 100%" @click.stop="bookListing(p)">预约看宠</el-button>
        </div>
      </div>
      <el-empty v-if="!hotListings.length" description="暂无待售" :image-size="60" />
    </div>

    <div class="section-head">
      <h3>本周热卖用品</h3>
      <span class="more" @click="go('/store')">去商城 ›</span>
    </div>
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px">
      <div v-for="p in hotProducts" :key="p.id" class="goods-card" @click="go('/store')">
        <div style="height: 110px; background: linear-gradient(160deg, #fff7ed, #ffedd5); display: flex; align-items: center; justify-content: center">
          <el-icon :size="36" color="#ff6a00"><ShoppingBag /></el-icon>
        </div>
        <div style="padding: 10px 12px 12px">
          <div style="font-weight: 600; font-size: 13px; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">
            {{ p.name }}
          </div>
          <div class="text-muted" style="font-size: 11px; margin-bottom: 4px">{{ p.store_name || "合作门店" }}</div>
          <div class="price-tag" style="font-size: 16px"><small>¥</small>{{ p.price ?? "—" }}</div>
        </div>
      </div>
    </div>
  </div>
</template>
