<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { ordersApi } from "@/api/orders";
import type { Order } from "@/types";

const router = useRouter();
const list = ref<Order[]>([]);
const loading = ref(false);

const LABEL: Record<string, string> = {
  pending: "待接单",
  accepted: "已接单",
  preparing: "备货中",
  delivering: "配送中",
  completed: "已完成",
  cancelled: "已取消",
};

/**
 * 订单接口只返回当前 status 和 created_at，没有逐状态历史。
 * 时间线按应用里已有的履约枚举推导，不新增接口：
 * pending 待接单 → accepted 已接单 → preparing 备货中 → delivering 配送中 → completed 已完成。
 * cancelled 已取消离开主路径：保留「已下单」，当前节点改为「已取消」。
 * 下单时间只标在第一步；其余节点没有独立时间戳。
 */
const FLOW = ["pending", "accepted", "preparing", "delivering", "completed"] as const;

type StepType = "primary" | "success" | "warning" | "info" | "danger";

interface TimelineStep {
  key: string;
  title: string;
  type: StepType;
  hollow: boolean;
  timestamp: string;
  desc: string;
}

function tagType(status: string): StepType {
  if (status === "completed") return "success";
  if (status === "cancelled") return "info";
  if (status === "pending") return "warning";
  if (status === "delivering" || status === "preparing") return "primary";
  return "primary";
}

function createdLabel(order: Order) {
  return order.created_at
    ? new Date(order.created_at).toLocaleString("zh-CN", { hour12: false }).slice(0, 16)
    : "";
}

function timelineOf(order: Order): TimelineStep[] {
  const created = createdLabel(order);
  if (order.status === "cancelled") {
    return [
      { key: "created", title: "已下单", type: "success", hollow: false, timestamp: created, desc: "订单已创建" },
      { key: "cancelled", title: "已取消", type: "info", hollow: false, timestamp: "当前", desc: "订单已取消，后续不再履约" },
    ];
  }
  const current = FLOW.indexOf(order.status as (typeof FLOW)[number]);
  const steps: TimelineStep[] = FLOW.map((key, i) => {
    const reached = current >= 0 && i < current;
    const active = current === i;
    const done = key === "completed" && active;
    return {
      key,
      title: LABEL[key],
      type: (done || reached ? "success" : active ? "primary" : "info") as StepType,
      hollow: current < 0 || i > current,
      timestamp: i === 0 ? created : active ? "当前" : "",
      desc: done || reached ? "已完成" : active ? "当前进度" : "待进行",
    };
  });
  if (current < 0) {
    steps.push({
      key: "unknown",
      title: LABEL[order.status] || order.status,
      type: "warning",
      hollow: false,
      timestamp: "当前",
      desc: "未识别的状态，主路径仅供参考",
    });
  }
  return steps;
}

async function load() {
  loading.value = true;
  try {
    list.value = await ordersApi.mine();
  } finally {
    loading.value = false;
  }
}

async function cancel(o: Order) {
  await ordersApi.cancel(o.id);
  ElMessage.success("已取消");
  await load();
}

onMounted(load);
</script>

<template>
  <div class="page-container orders-page" v-loading="loading">
    <header class="page-mast">
      <div>
        <p class="page-kicker">消费记录</p>
        <h2 class="page-title">我的订单</h2>
        <p class="page-sub">查看商品订单的接单、备货与配送进度。待接单或已接单时可以取消。</p>
      </div>
      <div v-if="!loading" class="mast-count">
        <strong>{{ list.length }}</strong>
        <span>笔订单</span>
      </div>
    </header>

    <div v-if="list.length" class="order-list">
      <article v-for="o in list" :key="o.id" class="card order-card" :data-status="o.status">
        <div class="order-main">
          <div class="order-head">
            <div>
              <div class="order-kicker">商品订单</div>
              <div class="order-id">#{{ o.id }}</div>
            </div>
            <div class="order-head-side">
              <div class="price-tag order-price"><small>¥</small>{{ o.total }}</div>
              <el-tag size="small" round effect="dark" :type="tagType(o.status)">{{ LABEL[o.status] || o.status }}</el-tag>
            </div>
          </div>
          <div class="order-items">
            <span v-for="(item, idx) in o.items" :key="item.id || idx" class="item-chip">
              {{ item.name }} × {{ item.qty }}
            </span>
            <span v-if="!o.items.length" class="text-muted">无商品明细</span>
          </div>
          <div class="order-meta">
            <div><span class="text-muted">门店</span>{{ o.store_name || o.store_id }}</div>
            <div><span class="text-muted">配送</span>{{ o.shipping_mode === "express" ? "快递" : "即时" }}</div>
            <div class="meta-wide"><span class="text-muted">地址</span>{{ o.address || "—" }}</div>
          </div>
          <div class="order-actions">
            <el-button
              v-if="o.status === 'pending' || o.status === 'accepted'"
              size="small"
              plain
              type="danger"
              @click="cancel(o)"
            >取消订单</el-button>
          </div>
        </div>
        <aside class="order-rail">
          <div class="rail-title">履约进度</div>
          <el-timeline class="order-flow">
            <el-timeline-item
              v-for="step in timelineOf(o)"
              :key="step.key"
              :type="step.type"
              :hollow="step.hollow"
              :timestamp="step.timestamp"
            >
              <span class="step-title">{{ step.title }}</span>
              <div class="text-muted order-step-desc">{{ step.desc }}</div>
            </el-timeline-item>
          </el-timeline>
        </aside>
      </article>
    </div>

    <div v-else-if="!loading" class="empty-panel">
      <el-empty class="soft-empty" :image-size="120">
        <template #description>
          <p class="empty-title">还没有商品订单</p>
          <p class="empty-desc">去宠物商城挑选用品并下单，接单、备货和配送进度会显示在这里。</p>
        </template>
        <el-button type="primary" round @click="router.push('/store')">去宠物商城下单</el-button>
      </el-empty>
    </div>
  </div>
</template>

<style scoped>
.order-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.order-card {
  --st: var(--app-primary);
  display: grid;
  grid-template-columns: minmax(0, 1fr) 250px;
  gap: 8px 8px;
  align-items: stretch;
  padding: 0;
  overflow: hidden;
  border-left: 5px solid var(--st);
}
.order-card[data-status="pending"] { --st: #f59e0b; }
.order-card[data-status="accepted"] { --st: #ff6a00; }
.order-card[data-status="preparing"] { --st: #2563eb; }
.order-card[data-status="delivering"] { --st: #7c3aed; }
.order-card[data-status="completed"] { --st: #00b578; }
.order-card[data-status="cancelled"] { --st: #94a3b8; }
.order-main {
  padding: 16px 18px 14px;
}
.order-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}
.order-kicker {
  font-size: 12px;
  color: var(--app-text-muted);
  font-weight: 600;
}
.order-id {
  margin-top: 2px;
  font-family: "Outfit", "Noto Sans SC", sans-serif;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.03em;
}
.order-head-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}
.order-price {
  font-size: 22px;
  line-height: 1;
}
.order-items {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 14px;
}
.item-chip {
  background: var(--app-primary-soft);
  color: var(--app-text);
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
}
.order-meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 16px;
  margin-top: 14px;
  font-size: 13px;
  color: var(--app-text-secondary);
}
.order-meta .text-muted {
  display: block;
  margin-bottom: 2px;
  font-size: 12px;
}
.meta-wide {
  grid-column: 1 / -1;
}
.order-actions {
  margin-top: 12px;
  min-height: 8px;
}
.order-rail {
  margin: 10px 10px 10px 0;
  padding: 14px 14px 6px 16px;
  border-radius: 14px;
  background: color-mix(in srgb, var(--app-bg) 72%, var(--app-surface));
}
.rail-title {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--app-text-muted);
  margin-bottom: 10px;
}
.order-flow {
  margin: 0;
  padding-left: 2px;
}
.step-title {
  font-weight: 700;
  font-size: 13px;
}
.order-step-desc {
  font-size: 12px;
  margin-top: 2px;
}
.empty-panel {
  background: var(--app-surface);
  border: 1px dashed color-mix(in srgb, var(--app-primary) 35%, var(--app-border));
  border-radius: 18px;
  padding: 12px 8px 20px;
}
@media (max-width: 800px) {
  .order-card {
    grid-template-columns: 1fr;
  }
  .order-rail {
    margin: 0 10px 10px;
  }
  .order-meta {
    grid-template-columns: 1fr;
  }
}
</style>
