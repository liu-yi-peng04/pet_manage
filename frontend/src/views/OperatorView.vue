<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { ElMessage } from "element-plus";
import { marketplaceApi } from "@/api/marketplace";
import { storeApi } from "@/api/store";
import type { Lead, Store, Trainer } from "@/types";

const leads = ref<Lead[]>([]);
const stores = ref<Store[]>([]);
const trainers = ref<Trainer[]>([]);
const loading = ref(false);
const matchId = ref<number | null>(null);
const showMatch = computed({
  get: () => matchId.value != null,
  set: (v: boolean) => {
    if (!v) matchId.value = null;
  },
});
const storeId = ref<number | null>(null);
const trainerId = ref<number | null>(null);
const NEED: Record<string, string> = {
  buy_pet: "选宠",
  product: "用品",
  train: "训练",
  hospital: "医院",
  boarding: "寄养",
  consult: "咨询",
};

async function load() {
  loading.value = true;
  try {
    leads.value = await marketplaceApi.leads();
    stores.value = await storeApi.stores();
    trainers.value = await marketplaceApi.trainers({ verified_only: false });
  } finally {
    loading.value = false;
  }
}

async function claim(id: number) {
  await marketplaceApi.claimLead(id);
  ElMessage.success("已领取");
  await load();
}

async function match() {
  if (!matchId.value) return;
  await marketplaceApi.matchLead(matchId.value, {
    store_id: storeId.value || undefined,
    trainer_id: trainerId.value || undefined,
  });
  ElMessage.success("已匹配资源");
  matchId.value = null;
  await load();
}

onMounted(load);
</script>

<template>
  <div class="page-container">
    <h2 style="margin: 0 0 4px">服务商运营台</h2>
    <p class="text-muted" style="margin: 0 0 16px; font-size: 13px">领取用户需求线索，匹配合作门店 / 训犬师 / 医院</p>
    <el-table v-loading="loading" :data="leads">
      <el-table-column prop="id" label="#" width="70" />
      <el-table-column label="用户" width="110">
        <template #default="{ row }">{{ row.user_name }}</template>
      </el-table-column>
      <el-table-column label="类型" width="90">
        <template #default="{ row }">{{ NEED[row.need_type] || row.need_type }}</template>
      </el-table-column>
      <el-table-column prop="summary" label="需求" min-width="220" />
      <el-table-column prop="city" label="城市" width="90" />
      <el-table-column prop="status" label="状态" width="90" />
      <el-table-column label="已匹配" min-width="160">
        <template #default="{ row }">{{ [row.matched_store_name, row.matched_trainer_name].filter(Boolean).join(" / ") || "—" }}</template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button v-if="row.status === 'open'" size="small" @click="claim(row.id)">领取</el-button>
          <el-button size="small" type="primary" @click="matchId = row.id">匹配</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showMatch" title="匹配资源" width="420px">
      <template #default>
        <el-form label-position="top">
          <el-form-item label="门店">
            <el-select v-model="storeId" clearable style="width: 100%">
              <el-option v-for="s in stores" :key="s.id" :label="`${s.name}（${s.store_type}）`" :value="s.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="训犬师">
            <el-select v-model="trainerId" clearable style="width: 100%">
              <el-option v-for="t in trainers" :key="t.id" :label="t.display_name" :value="t.id" />
            </el-select>
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="matchId = null">取消</el-button>
        <el-button type="primary" @click="match">确认匹配</el-button>
      </template>
    </el-dialog>
  </div>
</template>
