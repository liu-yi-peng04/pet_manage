<script setup lang="ts">
import { ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { staffApi, type StaffMember } from "@/api/workspace";
import { useUserStore } from "@/stores/user";

const props = defineProps<{ storeId: number | null }>();

const userStore = useUserStore();
const staffList = ref<StaffMember[]>([]);
const staffLoading = ref(false);
const showStaffDialog = ref(false);
const staffKeyword = ref("");
const candidates = ref<{ id: number; username: string; email: string | null }[]>([]);
const selectedUid = ref<number | null>(null);
const staffRole = ref("assistant");
const assigning = ref(false);

const emit = defineEmits<{ changed: [] }>();

async function reload() {
  if (!props.storeId) return;
  staffLoading.value = true;
  try {
    staffList.value = await staffApi.list(props.storeId);
  } finally {
    staffLoading.value = false;
  }
}

async function searchCandidates() {
  if (!props.storeId || !staffKeyword.value.trim()) return;
  candidates.value = await staffApi.search(props.storeId, staffKeyword.value.trim());
  selectedUid.value = candidates.value[0]?.id ?? null;
}

async function assignStaff() {
  if (!props.storeId || !selectedUid.value) {
    ElMessage.warning("请先搜索并选择用户");
    return;
  }
  assigning.value = true;
  try {
    await staffApi.assign(props.storeId, {
      user_id: selectedUid.value,
      staff_role: staffRole.value,
    });
    ElMessage.success("已添加店员");
    showStaffDialog.value = false;
    await reload();
    emit("changed");
  } finally {
    assigning.value = false;
  }
}

async function removeStaff(m: StaffMember) {
  if (!props.storeId) return;
  await ElMessageBox.confirm(`确定解除「${m.username}」的店员身份？`, "解除确认", {
    type: "warning",
    confirmButtonText: "解除",
    cancelButtonText: "取消",
    confirmButtonClass: "el-button--danger",
  });
  await staffApi.remove(props.storeId, m.id);
  ElMessage.success("已解除");
  await reload();
  emit("changed");
}

defineExpose({ reload });
</script>

<template>
  <div>
  <div class="panel-toolbar">
    <span class="meta-cell">协作账号，一起处理本店预约与订单</span>
    <el-button type="primary" size="small" round @click="showStaffDialog = true">
      <el-icon style="margin-right: 4px"><Plus /></el-icon>添加店员
    </el-button>
  </div>
  <div class="sheet" v-loading="staffLoading">
  <el-table v-if="staffList.length" :data="staffList" style="width: 100%">
    <el-table-column prop="username" label="用户名" min-width="140" />
    <el-table-column prop="email" label="邮箱" min-width="160">
      <template #default="{ row }"><span class="meta-cell">{{ row.email || "—" }}</span></template>
    </el-table-column>
    <el-table-column label="身份" width="110">
      <template #default="{ row }">
        <el-tag size="small" :type="row.staff_role === 'manager' ? 'warning' : 'primary'" effect="plain">
          {{ row.staff_role === "manager" ? "店主" : "店员" }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="110" align="right">
      <template #default="{ row }">
        <el-button
          v-if="!(row.id === userStore.userInfo?.id)"
          size="small"
          type="danger"
          link
          @click="removeStaff(row)"
        >解除</el-button>
      </template>
    </el-table-column>
  </el-table>
  <el-empty v-else-if="!staffLoading" class="soft-empty" :image-size="84">
    <template #description>
      <p class="empty-title">暂无店员</p>
      <p class="empty-desc">添加后，店员可以用自己的账号处理本店预约和订单。</p>
    </template>
  </el-empty>
  </div>
  </div>

  <el-dialog v-model="showStaffDialog" title="添加店员" width="480px">
    <el-form label-position="top">
      <el-form-item label="搜索用户（按用户名）">
        <div style="display: flex; gap: 8px; width: 100%">
          <el-input v-model="staffKeyword" placeholder="输入用户名关键字" @keyup.enter="searchCandidates" />
          <el-button @click="searchCandidates"><el-icon><Search /></el-icon></el-button>
        </div>
      </el-form-item>
      <el-form-item label="选择用户">
        <el-select v-model="selectedUid" style="width: 100%" placeholder="先搜索再选择" filterable>
          <el-option
            v-for="c in candidates"
            :key="c.id"
            :label="`${c.username}${c.email ? '（' + c.email + '）' : ''}`"
            :value="c.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="身份">
        <el-radio-group v-model="staffRole">
          <el-radio-button value="assistant">店员</el-radio-button>
          <el-radio-button value="manager">店主</el-radio-button>
        </el-radio-group>
        <div v-if="!userStore.isAdmin" class="text-muted" style="font-size: 12px; margin-top: 6px">
          只有超管可以指定店主
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showStaffDialog = false">取消</el-button>
      <el-button type="primary" :loading="assigning" @click="assignStaff">添加</el-button>
    </template>
  </el-dialog>
</template>
