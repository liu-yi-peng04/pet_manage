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
  { label: "选宠看猫狗", hint: "浏览在售", path: "/listings", color: "linear-gradient(135deg,#ff6a00,#ff9a4d)", icon: "Present" },
  { label: "用品商城", hint: "粮与用品", path: "/store", color: "linear-gradient(135deg,#ffd100,#ffb800)", icon: "ShoppingBag", dark: true },
  { label: "预约医院", hint: "体检就诊", path: "/booking?appt_type=exam", color: "linear-gradient(135deg,#00b578,#34d399)", icon: "Calendar" },
  { label: "预约美容", hint: "洗护造型", path: "/booking?appt_type=grooming", color: "linear-gradient(135deg,#3b82f6,#60a5fa)", icon: "Brush" },
  { label: "训犬师", hint: "上门训练", path: "/trainers", color: "linear-gradient(135deg,#f59e0b,#fbbf24)", icon: "Trophy", dark: true },
  { label: "寄养托管", hint: "出行无忧", path: "/booking?tab=boardings", color: "linear-gradient(135deg,#8b5cf6,#a78bfa)", icon: "House" },
  { label: "AI 顾问", hint: "随时提问", path: "/chat", color: "linear-gradient(135deg,#f43f5e,#fb7185)", icon: "ChatDotRound" },
  { label: "我的宠物", hint: "档案疫苗", path: "/pets", color: "linear-gradient(135deg,#0ea5e9,#38bdf8)", icon: "BellFilled" },
  { label: "我的订单", hint: "配送进度", path: "/orders", color: "linear-gradient(135deg,#64748b,#94a3b8)", icon: "List" },
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
  <div class="page-container home-page">
    <section class="home-hero fade-up">
      <div class="home-hero-copy">
        <span class="brand-chip">宠智联</span>
        <h2>嗨，{{ user.username || "养宠人" }}<br />今天想做什么？</h2>
        <p>选宠、买粮、预约医院或找训犬师，从这里一次安排好。</p>
        <div class="home-cta">
          <el-button type="primary" size="large" round @click="go('/listings')">
            <el-icon><Present /></el-icon>
            去选宠
          </el-button>
          <button type="button" class="cta-ghost" @click="go('/booking')">预约到店</button>
        </div>
      </div>
      <aside class="home-hero-side">
        <button type="button" class="hero-metric" @click="go('/listings')">
          <span class="hm-label">热门待售</span>
          <span class="hm-value">{{ loading ? "—" : hotListings.length }}</span>
          <span class="hm-link">查看全部</span>
        </button>
        <button type="button" class="hero-metric" @click="go('/store')">
          <span class="hm-label">热卖用品</span>
          <span class="hm-value">{{ loading ? "—" : hotProducts.length }}</span>
          <span class="hm-link">去商城</span>
        </button>
        <button type="button" class="hero-metric hero-metric-ask" @click="go('/chat')">
          <span class="hm-label">拿不定主意</span>
          <span class="hm-ask">问问 AI 顾问</span>
        </button>
      </aside>
    </section>

    <section class="section-card fade-up fade-up-delay-1">
      <div class="section-head">
        <h3>常用服务</h3>
        <span class="text-muted">点一下就能开始</span>
      </div>
      <div class="svc-grid">
        <button v-for="q in quicks" :key="q.path" type="button" class="svc-item" @click="go(q.path)">
          <span class="svc-icon" :style="{ background: q.color, color: q.dark ? '#1a1a1a' : '#fff' }">
            <el-icon :size="20"><component :is="q.icon" /></el-icon>
          </span>
          <span class="svc-copy">
            <span class="svc-label">{{ q.label }}</span>
            <span class="svc-hint">{{ q.hint }}</span>
          </span>
        </button>
      </div>
    </section>

    <section class="section-card fade-up fade-up-delay-2">
      <div class="section-head">
        <h3>热门待售</h3>
        <span class="more" @click="go('/listings')">全部选宠 ›</span>
      </div>
      <div v-if="loading && !hotListings.length" class="goods-grid">
        <div v-for="n in 4" :key="n" class="skel-card" />
      </div>
      <div v-else-if="hotListings.length" class="goods-grid">
        <article v-for="p in hotListings" :key="p.id" class="goods-card home-pet" @click="go('/listings')">
          <div class="pet-cover">
            <img :src="cover(p)" :alt="p.name" loading="lazy" />
            <span class="pet-species">{{ p.species === "cat" ? "猫" : "犬" }}</span>
          </div>
          <div class="pet-body">
            <div class="pet-name">{{ p.name }}</div>
            <div class="text-muted pet-meta">{{ p.breed || "品种待补充" }}</div>
            <div class="pet-row">
              <div class="price-tag"><small>¥</small>{{ p.price != null ? p.price : "面议" }}</div>
              <el-button type="primary" size="small" round @click.stop="bookListing(p)">预约看宠</el-button>
            </div>
          </div>
        </article>
      </div>
      <el-empty v-else class="soft-empty" :image-size="88">
        <template #description>
          <p class="empty-title">暂时没有待售宠物</p>
          <p class="empty-desc">选宠市场更新后，热门卡片会出现在这里。</p>
        </template>
        <el-button type="primary" round @click="go('/listings')">去选宠市场看看</el-button>
      </el-empty>
    </section>

    <section class="section-card fade-up fade-up-delay-3">
      <div class="section-head">
        <h3>本周热卖用品</h3>
        <span class="more" @click="go('/store')">去商城 ›</span>
      </div>
      <div v-if="loading && !hotProducts.length" class="goods-grid">
        <div v-for="n in 4" :key="n" class="skel-card skel-short" />
      </div>
      <div v-else-if="hotProducts.length" class="goods-grid">
        <article v-for="p in hotProducts" :key="p.id" class="goods-card home-product" @click="go('/store')">
          <div class="product-cover">
            <el-icon :size="34" color="#ff6a00"><ShoppingBag /></el-icon>
          </div>
          <div class="pet-body">
            <div class="pet-name">{{ p.name }}</div>
            <div class="text-muted pet-meta">{{ p.store_name || "合作门店" }}</div>
            <div class="price-tag"><small>¥</small>{{ p.price ?? "—" }}</div>
          </div>
        </article>
      </div>
      <el-empty v-else class="soft-empty" :image-size="88">
        <template #description>
          <p class="empty-title">本周还没有热卖</p>
          <p class="empty-desc">商城里的粮、玩具和日用，下单后也能在订单里跟踪进度。</p>
        </template>
        <el-button type="primary" round @click="go('/store')">去用品商城</el-button>
      </el-empty>
    </section>
  </div>
</template>

<style scoped>
.home-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(220px, 0.7fr);
  gap: 22px;
  align-items: stretch;
  padding: 28px 28px 26px;
  border-radius: 22px;
  background:
    radial-gradient(circle at 88% -10%, rgba(255, 255, 255, 0.55), transparent 32%),
    radial-gradient(circle at 8% 120%, rgba(255, 106, 0, 0.28), transparent 36%),
    linear-gradient(128deg, #ffe56a 0%, #ffc400 36%, #ff7a1a 100%);
  color: #1a1a1a;
  box-shadow: 0 18px 40px rgba(255, 122, 26, 0.22);
  overflow: hidden;
  position: relative;
}
.home-hero-copy h2 {
  margin: 12px 0 10px;
  font-family: "Outfit", "Noto Sans SC", sans-serif;
  font-size: 32px;
  line-height: 1.2;
  letter-spacing: -0.03em;
}
.home-hero-copy p {
  margin: 0;
  max-width: 420px;
  color: rgba(26, 26, 26, 0.78);
  font-size: 14px;
  line-height: 1.65;
}
.home-cta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 18px;
  align-items: center;
}
.home-cta :deep(.el-button) {
  font-weight: 700;
  padding: 12px 22px;
  box-shadow: 0 8px 18px rgba(224, 92, 0, 0.28);
}
.cta-ghost {
  border: 0;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.62);
  color: #1a1a1a;
  font-weight: 700;
  font-size: 14px;
  border-radius: 999px;
  padding: 12px 20px;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.8);
}
.cta-ghost:hover {
  background: #fff;
}
.home-hero-side {
  display: grid;
  gap: 10px;
  align-content: stretch;
}
.hero-metric {
  text-align: left;
  border: 0;
  cursor: pointer;
  border-radius: 16px;
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 8px 20px rgba(120, 53, 15, 0.08);
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.hero-metric:hover {
  background: #fff;
}
.hm-label {
  font-size: 12px;
  color: #8a5a32;
  font-weight: 600;
}
.hm-value {
  font-family: "Outfit", sans-serif;
  font-size: 26px;
  font-weight: 700;
  line-height: 1.1;
}
.hm-link,
.hm-ask {
  font-size: 12px;
  font-weight: 700;
  color: var(--app-primary);
}
.hero-metric-ask {
  background: #1a1a1a;
}
.hero-metric-ask .hm-label {
  color: rgba(255, 255, 255, 0.62);
}
.hero-metric-ask .hm-ask {
  color: var(--app-brand);
  font-size: 16px;
  margin-top: 4px;
}
.svc-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.svc-item {
  display: flex;
  align-items: center;
  gap: 12px;
  text-align: left;
  border: 1px solid var(--app-border);
  background: color-mix(in srgb, var(--app-bg) 65%, var(--app-surface));
  border-radius: 14px;
  padding: 12px;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s;
}
.svc-item:hover {
  transform: translateY(-2px);
  border-color: transparent;
  box-shadow: var(--app-shadow-hover);
  background: var(--app-surface);
}
.svc-icon {
  width: 42px;
  height: 42px;
  border-radius: 13px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.svc-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.svc-label {
  font-size: 14px;
  font-weight: 700;
  color: var(--app-text);
}
.svc-hint {
  margin-top: 2px;
  font-size: 12px;
  color: var(--app-text-muted);
}
.goods-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 14px;
}
.home-pet,
.home-product {
  display: flex;
  flex-direction: column;
}
.pet-cover {
  position: relative;
  height: 148px;
  background: #f3f1ee;
}
.pet-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.pet-species {
  position: absolute;
  left: 10px;
  top: 10px;
  background: rgba(26, 26, 26, 0.72);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  border-radius: 999px;
  padding: 2px 8px;
}
.pet-body {
  padding: 12px 14px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}
.pet-name {
  font-weight: 700;
  font-size: 15px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pet-meta {
  font-size: 12px;
}
.pet-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 8px;
}
.pet-row .price-tag {
  font-size: 18px;
}
.product-cover {
  height: 92px;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(circle at 80% 20%, rgba(255, 209, 0, 0.45), transparent 42%),
    linear-gradient(160deg, #fff7ed, #ffedd5);
}
.skel-card {
  height: 230px;
  border-radius: var(--app-radius);
  background: linear-gradient(90deg, #f3f1ee 25%, #faf8f5 37%, #f3f1ee 63%);
  background-size: 400% 100%;
  animation: sheen 1.2s ease infinite;
}
.skel-short {
  height: 176px;
}
@keyframes sheen {
  0% { background-position: 100% 0; }
  100% { background-position: 0 0; }
}
@media (max-width: 860px) {
  .home-hero {
    grid-template-columns: 1fr;
    padding: 22px 18px;
  }
  .home-hero-copy h2 {
    font-size: 26px;
  }
  .home-hero-side {
    grid-template-columns: 1fr 1fr;
  }
  .hero-metric-ask {
    grid-column: 1 / -1;
  }
  .svc-grid {
    grid-template-columns: 1fr 1fr;
  }
}
@media (max-width: 520px) {
  .svc-grid,
  .home-hero-side {
    grid-template-columns: 1fr;
  }
}
</style>
