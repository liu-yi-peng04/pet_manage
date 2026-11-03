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
  <el-table v-loading="customerLoading" :data="customers" style="width: 100%">
    <el-table-column prop="username" label="客户" min-width="120" />
    <el-table-column prop="email" label="邮箱" min-width="160">
      <template #default="{ row }">{{ row.email || "—" }}</template>
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
      <template #default="{ row }">{{ fmtDate(row.last_appointment_at) }}</template>
    </el-table-column>
  </el-table>
  <el-empty v-if="!customerLoading && !customers.length" description="暂无客户" :image-size="70" />
</template>
