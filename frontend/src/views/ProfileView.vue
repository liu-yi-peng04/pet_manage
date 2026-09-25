<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage, type FormInstance, type FormRules } from "element-plus";
import { useUserStore } from "@/stores/user";

const userStore = useUserStore();

const pwdFormRef = ref<FormInstance>();
const pwdForm = ref({ old_password: "", new_password: "", confirm: "" });
const saving = ref(false);

const pwdRules: FormRules = {
  old_password: [{ required: true, message: "请输入当前密码", trigger: "blur" }],
  new_password: [
    { required: true, message: "请输入新密码", trigger: "blur" },
    { min: 8, message: "新密码至少 8 位", trigger: "blur" },
  ],
  confirm: [
    {
      validator: (_r: unknown, v: string, cb: (e?: Error) => void) => {
        if (v !== pwdForm.value.new_password) cb(new Error("两次密码不一致"));
        else cb();
      },
      trigger: "blur",
    },
  ],
};

async function changePwd() {
  if (!pwdFormRef.value) return;
  const ok = await pwdFormRef.value.validate().catch(() => false);
  if (!ok) return;
  saving.value = true;
  try {
    await userStore.changePassword(pwdForm.value.old_password, pwdForm.value.new_password);
    ElMessage.success("密码修改成功，请重新登录");
    pwdForm.value = { old_password: "", new_password: "", confirm: "" };
    userStore.logout();
  } catch {
    /* 拦截器已提示 */
  } finally {
    saving.value = false;
  }
}

onMounted(() => userStore.fetchMe());
</script>

<template>
  <div class="page-container" style="max-width: 860px">
    <h2 class="page-title">个人中心</h2>

    <div style="display: grid; grid-template-columns: 300px 1fr; gap: 20px; align-items: start">
      <!-- 个人信息卡片 -->
      <div class="card" style="text-align: center; padding: 32px 20px">
        <el-avatar :size="72" style="background: #2563eb; font-size: 28px">{{ (userStore.username || "?").slice(0, 1).toUpperCase() }}</el-avatar>
        <h3 style="margin: 14px 0 4px">{{ userStore.username }}</h3>
        <p class="text-muted" style="font-size: 13px; margin: 0">
          {{ userStore.userInfo?.email || "未绑定邮箱" }}
        </p>
        <el-button link type="primary" style="margin-top: 12px" disabled>修改头像</el-button>
      </div>

      <!-- 信息详情 -->
      <div style="display: flex; flex-direction: column; gap: 20px">
        <div class="card">
          <div style="font-weight: 600; margin-bottom: 16px">账号信息</div>
          <div v-for="row in [
            { k: '用户 ID', v: userStore.userInfo?.id ?? '-' },
            { k: '用户名', v: userStore.username },
            { k: '邮箱', v: userStore.userInfo?.email ?? '-' },
            { k: '身份', v: userStore.userInfo?.role ?? '-' },
            { k: '积分', v: userStore.userInfo?.points ?? 0 },
            { k: '注册时间', v: userStore.userInfo?.created_at?.slice(0, 10) ?? '-' },
          ]" :key="row.k" style="display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid var(--app-border)">
            <span class="text-secondary">{{ row.k }}</span>
            <span>{{ row.v }}</span>
          </div>
        </div>

        <div class="card">
          <div style="font-weight: 600; margin-bottom: 16px">修改密码</div>
          <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-position="top" style="max-width: 420px">
            <el-form-item label="当前密码" prop="old_password">
              <el-input v-model="pwdForm.old_password" type="password" show-password />
            </el-form-item>
            <el-form-item label="新密码" prop="new_password">
              <el-input v-model="pwdForm.new_password" type="password" show-password placeholder="至少 8 位，含大小写/数字/符号" />
            </el-form-item>
            <el-form-item label="确认新密码" prop="confirm">
              <el-input v-model="pwdForm.confirm" type="password" show-password />
            </el-form-item>
            <el-button type="primary" :loading="saving" @click="changePwd">保存修改</el-button>
          </el-form>
        </div>
      </div>
    </div>
  </div>
</template>