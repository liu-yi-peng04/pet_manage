<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { ordersApi } from "@/api/orders";
import type { Order } from "@/types";

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
  <div class="page-container">
    <h2 style="margin: 0 0 16px">我的订单</h2>
    <el-table v-loading="loading" :data="list">
      <el-table-column prop="id" label="单号" width="80" />
      <el-table-column label="门店" min-width="140">
        <template #default="{ row }">{{ row.store_name || row.store_id }}</template>
      </el-table-column>
      <el-table-column label="商品" min-width="200">
        <template #default="{ row }">{{ row.items.map((i: { name: string; qty: number }) => `${i.name}×${i.qty}`).join("、") }}</template>
      </el-table-column>
      <el-table-column label="金额" width="100">
        <template #default="{ row }">¥{{ row.total }}</template>
      </el-table-column>
      <el-table-column label="配送" width="90">
        <template #default="{ row }">{{ row.shipping_mode === "express" ? "快递" : "即时" }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">{{ LABEL[row.status] || row.status }}</template>
      </el-table-column>
      <el-table-column prop="address" label="地址" min-width="160" />
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button v-if="row.status === 'pending' || row.status === 'accepted'" size="small" link type="danger" @click="cancel(row)">取消</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !list.length" description="暂无订单" />
  </div>
</template>
