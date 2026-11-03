<script setup lang="ts">
import { ref } from "vue";
import { ElMessage } from "element-plus";
import { workspaceApi } from "@/api/workspace";
import type { Appointment } from "@/types";
import { APPT_TYPES, fmtDate, statusLabel, statusType } from "./shared";

const appointments = ref<Appointment[]>([]);
const apptFilter = ref("");
const apptLoading = ref(false);

const emit = defineEmits<{ changed: [] }>();

async function reload() {
  apptLoading.value = true;
  try {
    appointments.value = await workspaceApi.appointments(apptFilter.value || undefined);
  } finally {
    apptLoading.value = false;
  }
}

/** 概览磁贴与新预约通知会把筛选切到待处理后再拉取。 */
function setFilter(status: string) {
  apptFilter.value = status;
  return reload();
}

/** 轮询在「预约处理台 + 待处理」时直接覆盖列表，避免多打一次请求。 */
function setRowsIfPending(rows: Appointment[]) {
  if (apptFilter.value === "pending") appointments.value = rows;
}

async function setApptStatus(a: Appointment, status: string) {
  await workspaceApi.setAppointmentStatus(a.id, status);
  ElMessage.success("已更新");
  await reload();
  emit("changed");
}

defineExpose({ reload, setFilter, setRowsIfPending });
</script>

<template>
  <el-alert
    type="info"
    :closable="false"
    show-icon
    style="margin-bottom: 12px"
    title="用户在「预约到店」提交后会出现在这里。商家端只确认/完成，不能自己发起预约。"
  />
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px">
    <el-radio-group v-model="apptFilter" @change="reload">
      <el-radio-button value="">全部</el-radio-button>
      <el-radio-button value="pending">待处理</el-radio-button>
      <el-radio-button value="confirmed">已确认</el-radio-button>
      <el-radio-button value="completed">已完成</el-radio-button>
      <el-radio-button value="cancelled">已取消</el-radio-button>
    </el-radio-group>
  </div>
  <el-table v-loading="apptLoading" :data="appointments" style="width: 100%">
    <el-table-column prop="appt_time" label="时间" width="160">
      <template #default="{ row }">{{ fmtDate(row.appt_time) }}</template>
    </el-table-column>
    <el-table-column label="类型" width="90">
      <template #default="{ row }">{{ APPT_TYPES[row.appt_type] ?? row.appt_type }}</template>
    </el-table-column>
    <el-table-column prop="user_id" label="客户 ID" width="90" />
    <el-table-column label="宠物" min-width="120">
      <template #default="{ row }">{{ row.pet_name || (row.pet_id ? `#${row.pet_id}` : "—") }}</template>
    </el-table-column>
    <el-table-column label="状态" width="100">
      <template #default="{ row }">
        <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
      </template>
    </el-table-column>
    <el-table-column prop="notes" label="备注" min-width="140">
      <template #default="{ row }">{{ row.notes || "—" }}</template>
    </el-table-column>
    <el-table-column label="操作" width="200" align="right">
      <template #default="{ row }">
        <template v-if="row.status === 'pending'">
          <el-button size="small" type="primary" link @click="setApptStatus(row, 'confirmed')">确认</el-button>
          <el-button size="small" type="danger" link @click="setApptStatus(row, 'cancelled')">取消</el-button>
        </template>
        <el-button
          v-else-if="row.status === 'confirmed'"
          size="small"
          type="success"
          link
          @click="setApptStatus(row, 'completed')"
        >完成</el-button>
      </template>
    </el-table-column>
  </el-table>
  <el-empty v-if="!apptLoading && !appointments.length" description="暂无预约" :image-size="70" />
</template>
