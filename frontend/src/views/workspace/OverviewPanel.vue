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
  <div class="loop-strip" style="margin-top: 0">
    <strong>{{ isHospital ? "医院闭环" : "门店闭环" }}</strong>
    <span v-if="isHospital">用户预约就诊 → 你在此确认 → 用户端状态更新</span>
    <span v-else>用户下单/预约看宠/寄养 → 你接单确认 → 用户在订单与预约里看到进度</span>
  </div>
  <div v-if="overview" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px">
    <div class="stat-tile" @click="emit('openAppointments')">
      <div class="label">待处理预约</div>
      <div class="value" style="color: var(--app-primary)">{{ overview.pending_appointments }}</div>
      <div class="hint">点此去确认 ›</div>
    </div>
    <div v-if="!isHospital" class="stat-tile" @click="emit('openBoardings')">
      <div class="label">进行中寄养</div>
      <div class="value" style="color: #2563eb">{{ overview.active_boardings }}</div>
      <div class="hint">客户寄养排期 ›</div>
    </div>
    <div class="stat-tile" @click="emit('openCustomers')">
      <div class="label">客户数</div>
      <div class="value" style="color: #16a34a">{{ overview.customers }}</div>
      <div class="hint">到店客户档案 ›</div>
    </div>
    <div v-if="isShop" class="stat-tile" @click="emit('openOrders')">
      <div class="label">商品 / 履约</div>
      <div class="value" style="color: #9333ea">{{ overview.products }}</div>
      <div class="hint">去处理订单 ›</div>
    </div>
    <div v-if="isShop" class="stat-tile" @click="emit('openRecalls')">
      <div class="label">疫苗临期（代约）</div>
      <div class="value" style="color: #dc2626">{{ overview.due_vaccines }}</div>
      <div class="hint">中转预约医院 ›</div>
    </div>
  </div>
  <el-empty v-else description="暂无门店数据" :image-size="90" />
</template>
