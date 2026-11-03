<script setup lang="ts">
import { ref } from "vue";
import { ElMessage } from "element-plus";
import { workspaceApi } from "@/api/workspace";
import type { Boarding } from "@/types";
import { statusLabel, statusType } from "./shared";

const boardings = ref<Boarding[]>([]);
const boardingFilter = ref("");
const boardingLoading = ref(false);

const emit = defineEmits<{ changed: [] }>();

async function reload() {
  boardingLoading.value = true;
  try {
    boardings.value = await workspaceApi.boardings(boardingFilter.value || undefined);
  } finally {
    boardingLoading.value = false;
  }
}

async function setBoardingStatus(b: Boarding, status: string) {
  await workspaceApi.setBoardingStatus(b.id, status);
  ElMessage.success("已更新");
  await reload();
  emit("changed");
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
    title="这里是用户预约寄养到本店的宠物排期。商家没有「我的宠物」，也不在此发起预约——只接收并处理。"
  />
  <div class="panel-toolbar">
    <el-radio-group v-model="boardingFilter" @change="reload">
      <el-radio-button value="">全部</el-radio-button>
      <el-radio-button value="pending">待确认</el-radio-button>
      <el-radio-button value="confirmed">已确认</el-radio-button>
      <el-radio-button value="completed">已完成</el-radio-button>
      <el-radio-button value="cancelled">已取消</el-radio-button>
    </el-radio-group>
  </div>
  <div class="sheet" v-loading="boardingLoading">
  <el-table v-if="boardings.length" :data="boardings" style="width: 100%">
    <el-table-column prop="start_date" label="入住" width="110" />
    <el-table-column prop="end_date" label="离店" width="110" />
    <el-table-column prop="user_id" label="客户 ID" width="90">
      <template #default="{ row }"><span class="meta-cell">{{ row.user_id }}</span></template>
    </el-table-column>
    <el-table-column prop="pet_id" label="宠物 ID" width="90">
      <template #default="{ row }"><span class="meta-cell">{{ row.pet_id ?? "—" }}</span></template>
    </el-table-column>
    <el-table-column label="日费" width="110">
      <template #default="{ row }">
        <span class="money-cell">{{ row.daily_fee != null ? `¥${row.daily_fee}` : "—" }}</span>
        <span v-if="row.daily_fee != null" class="meta-cell"> /天</span>
      </template>
    </el-table-column>
    <el-table-column label="状态" width="100">
      <template #default="{ row }">
        <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
      </template>
    </el-table-column>
    <el-table-column prop="notes" label="备注" min-width="140">
      <template #default="{ row }"><span class="meta-cell">{{ row.notes || "—" }}</span></template>
    </el-table-column>
    <el-table-column label="操作" width="200" align="right">
      <template #default="{ row }">
        <template v-if="row.status === 'pending'">
          <el-button size="small" type="primary" link @click="setBoardingStatus(row, 'confirmed')">确认</el-button>
          <el-button size="small" type="danger" link @click="setBoardingStatus(row, 'cancelled')">取消</el-button>
        </template>
        <el-button
          v-else-if="row.status === 'confirmed'"
          size="small"
          type="success"
          link
          @click="setBoardingStatus(row, 'completed')"
        >完成</el-button>
      </template>
    </el-table-column>
  </el-table>
  <el-empty v-else-if="!boardingLoading" class="soft-empty" :image-size="84">
    <template #description>
      <p class="empty-title">暂无寄养订单</p>
      <p class="empty-desc">用户预约寄养到本店后，入住和离店排期会列在这里。</p>
    </template>
  </el-empty>
  </div>
  </div>
</template>
