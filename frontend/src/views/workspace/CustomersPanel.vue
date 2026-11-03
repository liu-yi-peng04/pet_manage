<script setup lang="ts">
import { ref } from "vue";
import { workspaceApi, type Customer } from "@/api/workspace";
import { fmtDate, speciesLabel } from "./shared";

const customers = ref<Customer[]>([]);
const customerLoading = ref(false);

async function reload() {
  customerLoading.value = true;
  try {
    customers.value = await workspaceApi.customers();
  } finally {
    customerLoading.value = false;
  }
}

defineExpose({ reload });
</script>

<template>
  <div class="sheet" v-loading="customerLoading">
  <el-table v-if="customers.length" :data="customers" style="width: 100%">
    <el-table-column prop="username" label="客户" min-width="120" />
    <el-table-column prop="email" label="邮箱" min-width="160">
      <template #default="{ row }"><span class="meta-cell">{{ row.email || "—" }}</span></template>
    </el-table-column>
    <el-table-column label="宠物" min-width="180">
      <template #default="{ row }">
        <template v-if="row.pets.length">
          <el-tag
            v-for="p in row.pets"
            :key="p.id"
            size="small"
            effect="plain"
            style="margin: 2px"
          >{{ p.name }}（{{ speciesLabel(p.species) }}）</el-tag>
        </template>
        <span v-else class="text-muted">—</span>
      </template>
    </el-table-column>
    <el-table-column label="最近到店" width="170">
      <template #default="{ row }"><span class="meta-cell">{{ fmtDate(row.last_appointment_at) }}</span></template>
    </el-table-column>
  </el-table>
  <el-empty v-else-if="!customerLoading" class="soft-empty" :image-size="84">
    <template #description>
      <p class="empty-title">暂无客户</p>
      <p class="empty-desc">有到店预约或消费后，客户档案会汇总在这张表里。</p>
    </template>
  </el-empty>
  </div>
</template>
