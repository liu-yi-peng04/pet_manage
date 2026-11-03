<script setup lang="ts">
import { ref } from "vue";
import { ElMessage } from "element-plus";
import { ordersApi } from "@/api/orders";
import type { Order } from "@/types";

const storeOrders = ref<Order[]>([]);
const loading = ref(false);

const STATUS_LABEL: Record<string, string> = {
  pending: "待接单",
  accepted: "已接单",
  preparing: "备货中",
  delivering: "配送中",
  completed: "已完成",
  cancelled: "已取消",
};

async function reload() {
  loading.value = true;
  try {
    storeOrders.value = await ordersApi.storeOrders();
  } finally {
    loading.value = false;
  }
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
  <div class="sheet" v-loading="loading">
    <el-table v-if="storeOrders.length" :data="storeOrders">
      <el-table-column prop="id" label="单号" width="88">
        <template #default="{ row }"><span class="money-cell">#{{ row.id }}</span></template>
      </el-table-column>
      <el-table-column label="商品" min-width="180">
        <template #default="{ row }">
          <span class="meta-cell">{{ row.items?.map((i) => `${i.name}×${i.qty}`).join("、") || "无商品明细" }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="address" label="地址" min-width="160">
        <template #default="{ row }"><span class="meta-cell">{{ row.address || "—" }}</span></template>
      </el-table-column>
      <el-table-column prop="total" label="金额" width="100">
        <template #default="{ row }"><span class="money-cell">¥{{ row.total }}</span></template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="110">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ STATUS_LABEL[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="履约" width="220">
        <template #default="{ row }">
          <el-button v-if="row.status === 'pending'" size="small" @click="pushOrder(row, 'accepted')">接单</el-button>
          <el-button v-if="row.status === 'accepted'" size="small" @click="pushOrder(row, 'preparing')">备货</el-button>
          <el-button v-if="row.status === 'preparing'" size="small" @click="pushOrder(row, 'delivering')">配送</el-button>
          <el-button v-if="row.status === 'delivering'" size="small" type="primary" @click="pushOrder(row, 'completed')">完成</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-else-if="!loading" class="soft-empty" :image-size="84">
      <template #description>
        <p class="empty-title">还没有商品订单</p>
        <p class="empty-desc">顾客在商城下单后，接单、备货和配送会显示在这里。</p>
      </template>
    </el-empty>
  </div>
</template>
