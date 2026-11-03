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
  <div class="page-container" v-loading="loading">
    <h2 class="page-title">我的订单</h2>
    <p class="page-sub">查看商品订单的接单、备货与配送进度。待接单或已接单时可以取消。</p>

    <div v-if="list.length" class="order-list">
      <article v-for="o in list" :key="o.id" class="card order-card">
        <div class="order-main">
          <div class="order-head">
            <div>
              <span class="order-id">单号 #{{ o.id }}</span>
              <el-tag size="small" effect="plain" style="margin-left: 8px">{{ LABEL[o.status] || o.status }}</el-tag>
            </div>
            <el-button
              v-if="o.status === 'pending' || o.status === 'accepted'"
              size="small"
              link
              type="danger"
              @click="cancel(o)"
            >取消</el-button>
          </div>
          <div class="order-meta">
            <div><span class="text-muted">门店</span>{{ o.store_name || o.store_id }}</div>
            <div><span class="text-muted">金额</span>¥{{ o.total }}</div>
            <div><span class="text-muted">配送</span>{{ o.shipping_mode === "express" ? "快递" : "即时" }}</div>
            <div><span class="text-muted">地址</span>{{ o.address || "—" }}</div>
          </div>
          <div class="order-items">
            {{ o.items.map((i) => `${i.name}×${i.qty}`).join("、") || "无商品明细" }}
          </div>
        </div>
        <el-timeline class="order-flow">
          <el-timeline-item
            v-for="step in timelineOf(o)"
            :key="step.key"
            :type="step.type"
            :hollow="step.hollow"
            :timestamp="step.timestamp"
          >
            {{ step.title }}
            <div class="text-muted order-step-desc">{{ step.desc }}</div>
          </el-timeline-item>
        </el-timeline>
      </article>
    </div>

    <el-empty v-else-if="!loading" :image-size="120">
      <template #description>
        <p class="empty-title">还没有商品订单</p>
        <p class="text-muted empty-desc">去宠物商城挑选用品并下单，接单、备货和配送进度会显示在这里。</p>
      </template>
      <el-button type="primary" @click="router.push('/store')">去宠物商城下单</el-button>
    </el-empty>
  </div>
</template>

<style scoped>
.order-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.order-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 240px;
  gap: 8px 20px;
  align-items: start;
}
.order-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
.order-id {
  font-weight: 700;
}
.order-meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 16px;
  margin-top: 12px;
  font-size: 13px;
}
.order-meta .text-muted {
  margin-right: 8px;
}
.order-items {
  margin-top: 10px;
  font-size: 13px;
  line-height: 1.6;
}
.order-flow {
  margin: 0;
  padding-left: 4px;
}
.order-step-desc {
  font-size: 12px;
  margin-top: 2px;
}
.empty-title {
  margin: 0 0 4px;
  font-weight: 700;
  color: var(--app-text);
}
.empty-desc {
  margin: 0;
  max-width: 360px;
  line-height: 1.6;
}
@media (max-width: 800px) {
  .order-card {
    grid-template-columns: 1fr;
  }
  .order-meta {
    grid-template-columns: 1fr;
  }
}
</style>
