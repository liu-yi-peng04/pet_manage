<script setup lang="ts">
import { ref } from "vue";
import { ElMessage } from "element-plus";
import { ordersApi } from "@/api/orders";
import type { Order } from "@/types";

const storeOrders = ref<Order[]>([]);

async function reload() {
  storeOrders.value = await ordersApi.storeOrders();
}

function setRows(rows: Order[]) {
  storeOrders.value = rows;
}

async function pushOrder(o: Order, status: string) {
  await ordersApi.setStatus(o.id, status);
  ElMessage.success("已更新");
  await reload();
}

defineExpose({ reload, setRows });
</script>

<template>
  <el-table :data="storeOrders">
    <el-table-column prop="id" label="#" width="70" />
    <el-table-column prop="address" label="地址" min-width="160" />
    <el-table-column prop="total" label="金额" width="90" />
    <el-table-column prop="status" label="状态" width="110" />
    <el-table-column label="履约" width="220">
      <template #default="{ row }">
        <el-button v-if="row.status === 'pending'" size="small" @click="pushOrder(row, 'accepted')">接单</el-button>
        <el-button v-if="row.status === 'accepted'" size="small" @click="pushOrder(row, 'preparing')">备货</el-button>
        <el-button v-if="row.status === 'preparing'" size="small" @click="pushOrder(row, 'delivering')">配送</el-button>
        <el-button v-if="row.status === 'delivering'" size="small" type="primary" @click="pushOrder(row, 'completed')">完成</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>
