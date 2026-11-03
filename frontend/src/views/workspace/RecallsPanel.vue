<script setup lang="ts">
import { ref } from "vue";
import { ElMessage } from "element-plus";
import { workspaceApi } from "@/api/workspace";
import { storeApi } from "@/api/store";
import type { VaccineRecall } from "@/types";

const recalls = ref<VaccineRecall[]>([]);
const recallLoading = ref(false);
const hospitals = ref<{ id: number; name: string; city?: string | null }[]>([]);
const showInviteDialog = ref(false);
const inviting = ref(false);
const inviteTarget = ref<VaccineRecall | null>(null);
const inviteHospitalId = ref<number | null>(null);
const inviteTime = ref("");

async function reload() {
  recallLoading.value = true;
  try {
    recalls.value = await workspaceApi.vaccineRecalls();
    if (!hospitals.value.length) {
      const stores = await storeApi.stores({ store_type: "hospital" });
      hospitals.value = stores.map((s) => ({ id: s.id, name: s.name, city: s.city }));
      if (!inviteHospitalId.value && hospitals.value[0]) inviteHospitalId.value = hospitals.value[0].id;
    }
  } finally {
    recallLoading.value = false;
  }
}

function openInvite(r: VaccineRecall) {
  inviteTarget.value = r;
  inviteTime.value = "";
  if (!inviteHospitalId.value && hospitals.value[0]) inviteHospitalId.value = hospitals.value[0].id;
  showInviteDialog.value = true;
}

async function confirmInvite() {
  if (!inviteTarget.value) return;
  if (!inviteHospitalId.value) {
    ElMessage.warning("请选择代约的接种医院");
    return;
  }
  inviting.value = true;
  try {
    const appt = await workspaceApi.inviteVaccine({
      pet_id: inviteTarget.value.pet_id,
      vaccine_id: inviteTarget.value.vaccine_id,
      hospital_id: inviteHospitalId.value,
      appt_time: inviteTime.value || undefined,
      notes: "宠物店中转代约",
    });
    const hName = hospitals.value.find((h) => h.id === inviteHospitalId.value)?.name || "医院";
    ElMessage.success(`已代约「${hName}」接种，预约单 #${appt.id} 已推送到医院端`);
    showInviteDialog.value = false;
  } finally {
    inviting.value = false;
  }
}

defineExpose({ reload });
</script>

<template>
  <el-alert
    type="warning"
    :closable="false"
    show-icon
    style="margin-bottom: 12px"
    title="宠物店不负责接种，只做中转：发现客户疫苗临期后，代约到合作医院；医院在「预约处理台」确认并完成接种。"
  />
  <el-table v-loading="recallLoading" :data="recalls" style="width: 100%">
    <el-table-column prop="owner_name" label="主人" width="110" />
    <el-table-column prop="pet_name" label="宠物" width="110" />
    <el-table-column prop="vaccine_name" label="疫苗" min-width="140" />
    <el-table-column prop="next_due_date" label="到期日" width="120" />
    <el-table-column label="状态" width="100">
      <template #default="{ row }">{{ row.status === "overdue" ? "已过期" : "临期" }} {{ row.days_left }}天</template>
    </el-table-column>
    <el-table-column label="操作" width="150" align="right">
      <template #default="{ row }">
        <el-button size="small" type="primary" @click="openInvite(row)">代约医院</el-button>
      </template>
    </el-table-column>
  </el-table>
  <el-empty v-if="!recallLoading && !recalls.length" description="暂无临期疫苗客户" :image-size="70" />

  <el-dialog v-model="showInviteDialog" title="代约医院接种（中转）" width="480px">
    <el-alert
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 14px"
      title="本店不打针：只是帮客户把预约推到医院。医院确认后，用户可在「我的预约」看到进度。"
    />
    <el-form label-position="top" v-if="inviteTarget">
      <el-form-item label="客户 / 宠物">
        <div>{{ inviteTarget.owner_name }} · {{ inviteTarget.pet_name }} · {{ inviteTarget.vaccine_name }}</div>
      </el-form-item>
      <el-form-item label="接种医院" required>
        <el-select v-model="inviteHospitalId" placeholder="选择合作医院" style="width: 100%">
          <el-option v-for="h in hospitals" :key="h.id" :label="h.city ? `${h.name}（${h.city}）` : h.name" :value="h.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="预约时间（可选，默认两天后上午10点）">
        <el-date-picker
          v-model="inviteTime"
          type="datetime"
          value-format="YYYY-MM-DDTHH:mm:ss"
          placeholder="选择时间"
          style="width: 100%"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showInviteDialog = false">取消</el-button>
      <el-button type="primary" :loading="inviting" @click="confirmInvite">确认代约</el-button>
    </template>
  </el-dialog>
</template>
