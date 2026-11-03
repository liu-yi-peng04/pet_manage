<script setup lang="ts">
import type { StoreOverview } from "@/api/workspace";

defineProps<{
  overview: StoreOverview | null;
  isHospital: boolean;
  isShop: boolean;
}>();

const emit = defineEmits<{
  openAppointments: [];
  openBoardings: [];
  openCustomers: [];
  openOrders: [];
  openRecalls: [];
}>();
</script>

<template>
  <div class="ov">
    <div class="loop-strip ov-loop">
      <strong>{{ isHospital ? "医院闭环" : "门店闭环" }}</strong>
      <span v-if="isHospital">用户预约就诊 → 你在此确认 → 用户端状态更新</span>
      <span v-else>用户下单/预约看宠/寄养 → 你接单确认 → 用户在订单与预约里看到进度</span>
    </div>
    <div v-if="overview" class="ov-grid">
      <button type="button" class="ov-tile tone-orange" @click="emit('openAppointments')">
        <span class="ov-ico"><el-icon :size="20"><Calendar /></el-icon></span>
        <span class="ov-body">
          <span class="label">待处理预约</span>
          <span class="value">{{ overview.pending_appointments }}</span>
          <span class="hint">点此去确认</span>
        </span>
      </button>
      <button v-if="!isHospital" type="button" class="ov-tile tone-blue" @click="emit('openBoardings')">
        <span class="ov-ico"><el-icon :size="20"><House /></el-icon></span>
        <span class="ov-body">
          <span class="label">进行中寄养</span>
          <span class="value">{{ overview.active_boardings }}</span>
          <span class="hint">客户寄养排期</span>
        </span>
      </button>
      <button type="button" class="ov-tile tone-green" @click="emit('openCustomers')">
        <span class="ov-ico"><el-icon :size="20"><User /></el-icon></span>
        <span class="ov-body">
          <span class="label">客户数</span>
          <span class="value">{{ overview.customers }}</span>
          <span class="hint">到店客户档案</span>
        </span>
      </button>
      <button v-if="isShop" type="button" class="ov-tile tone-purple" @click="emit('openOrders')">
        <span class="ov-ico"><el-icon :size="20"><Goods /></el-icon></span>
        <span class="ov-body">
          <span class="label">商品 / 履约</span>
          <span class="value">{{ overview.products }}</span>
          <span class="hint">去处理订单</span>
        </span>
      </button>
      <button v-if="isShop" type="button" class="ov-tile tone-red" @click="emit('openRecalls')">
        <span class="ov-ico"><el-icon :size="20"><Bell /></el-icon></span>
        <span class="ov-body">
          <span class="label">疫苗临期（代约）</span>
          <span class="value">{{ overview.due_vaccines }}</span>
          <span class="hint">中转预约医院</span>
        </span>
      </button>
    </div>
    <el-empty v-else class="soft-empty" :image-size="90">
      <template #description>
        <p class="empty-title">暂无门店数据</p>
        <p class="empty-desc">门店概览加载完成后，预约、寄养和客户数会显示在这里。</p>
      </template>
    </el-empty>
  </div>
</template>

<style scoped>
.ov-loop {
  margin-top: 0;
  margin-bottom: 14px;
  background: color-mix(in srgb, var(--app-primary) 8%, var(--app-surface));
  border-style: solid;
}
.ov-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}
.ov-tile {
  display: flex;
  align-items: center;
  gap: 12px;
  text-align: left;
  border: 1px solid var(--app-border);
  background: var(--app-surface);
  border-radius: 16px;
  padding: 14px;
  cursor: pointer;
  box-shadow: var(--app-shadow);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.ov-tile:hover {
  transform: translateY(-2px);
  box-shadow: var(--app-shadow-hover);
}
.ov-ico {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #fff;
}
.ov-body {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.label {
  font-size: 12px;
  color: var(--app-text-muted);
}
.value {
  margin-top: 2px;
  font-family: "Outfit", sans-serif;
  font-size: 28px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--tone, var(--app-text));
}
.hint {
  margin-top: 4px;
  font-size: 12px;
  font-weight: 700;
  color: var(--app-primary);
}
.tone-orange { --tone: var(--app-primary); }
.tone-orange .ov-ico { background: linear-gradient(135deg, #ff6a00, #ff9a4d); }
.tone-blue { --tone: #2563eb; }
.tone-blue .ov-ico { background: linear-gradient(135deg, #2563eb, #60a5fa); }
.tone-green { --tone: #16a34a; }
.tone-green .ov-ico { background: linear-gradient(135deg, #00b578, #34d399); }
.tone-purple { --tone: #7c3aed; }
.tone-purple .ov-ico { background: linear-gradient(135deg, #7c3aed, #a78bfa); }
.tone-red { --tone: #dc2626; }
.tone-red .ov-ico { background: linear-gradient(135deg, #dc2626, #fb7185); }
</style>
