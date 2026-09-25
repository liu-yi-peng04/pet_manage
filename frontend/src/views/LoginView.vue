<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import type { FormInstance, FormRules } from "element-plus";
import { ElMessage } from "element-plus";
import { useUserStore } from "@/stores/user";

const userStore = useUserStore();
const router = useRouter();

const mode = ref<"login" | "register">("login");
const loading = ref(false);
const formRef = ref<FormInstance>();

const form = ref({
  username: "",
  email: "",
  password: "",
  confirm: "",
  role: "user",
});

const rules: FormRules = {
  username: [
    { required: true, message: "请输入用户名", trigger: "blur" },
    { min: 3, max: 24, message: "用户名需 3-24 位", trigger: "blur" },
  ],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
    { min: 8, message: "密码至少 8 位", trigger: "blur" },
  ],
  email: [
    { type: "email", message: "邮箱格式不正确", trigger: "blur" },
  ],
  confirm: [
    {
      validator: (_r: unknown, v: string, cb: (e?: Error) => void) => {
        if (v !== form.value.password) cb(new Error("两次密码不一致"));
        else cb();
      },
      trigger: "blur",
    },
  ],
};

async function submit() {
  if (!formRef.value) return;
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;
  loading.value = true;
  try {
    if (mode.value === "register") {
      await userStore.register({
        username: form.value.username,
        email: form.value.email,
        password: form.value.password,
        role: form.value.role,
      });
      ElMessage.success("注册成功，已自动登录");
    } else {
      await userStore.login(form.value.username, form.value.password);
    }
    router.push(userStore.homePath());
  } catch {
    /* 错误已在拦截器提示 */
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div style="display: flex; height: 100vh">
    <!-- 左：品牌区 -->
    <div style="flex: 1; background: #1c1c1e; color: #fff; display: flex; align-items: center; justify-content: center; padding: 48px; position: relative; overflow: hidden">
      <div style="position: absolute; inset: 0; background: radial-gradient(600px 400px at 15% 20%, rgba(255,209,0,.28), transparent), radial-gradient(520px 320px at 85% 75%, rgba(255,106,0,.28), transparent)"></div>
      <div style="max-width: 440px; position: relative">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 28px">
          <span style="width: 36px; height: 36px; border-radius: 10px; background: #ffd100; color: #1a1a1a; display: inline-flex; align-items: center; justify-content: center; font-weight: 800">宠</span>
          <span style="font-size: 22px; font-weight: 700; font-family: Outfit, Noto Sans SC, sans-serif">宠智联</span>
        </div>
        <h1 style="font-size: 30px; line-height: 1.4; margin: 0 0 16px; font-family: Outfit, Noto Sans SC, sans-serif">
          像美团一样约服务<br />像淘宝一样逛选宠
        </h1>
        <p style="font-size: 15px; line-height: 1.8; color: #cbd5e1; margin: 0">
          选宠、买粮、预约医院与训犬师，养宠服务一站搞定。
        </p>
        <div style="margin-top: 36px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px">
          <div v-for="f in ['AI 顾问', '到店预约', '订单履约']" :key="f" style="background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.1); border-radius: 12px; padding: 14px; text-align: center">
            <div style="font-size: 13px; color: #e2e8f0">{{ f }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 右：表单区 -->
    <div style="width: 480px; display: flex; align-items: center; justify-content: center; background: var(--app-surface); padding: 40px">
      <div style="width: 340px">
        <h2 style="font-size: 22px; margin: 0 0 6px">{{ mode === "login" ? "欢迎回来" : "创建账号" }}</h2>
        <p class="text-muted" style="margin: 0 0 28px">
          {{ mode === "login" ? "登录后按身份进入服务页" : "选择身份注册：养宠用户或服务方" }}
        </p>

        <el-tabs v-model="mode" stretch>
          <el-tab-pane label="登录" name="login" />
          <el-tab-pane label="注册" name="register" />
        </el-tabs>

        <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.username" placeholder="3-24 位，字母开头" size="large" />
          </el-form-item>
          <el-form-item v-if="mode === 'register'" label="我是">
            <el-select v-model="form.role" size="large" style="width: 100%">
              <el-option label="养宠用户（免费顾问）" value="user" />
              <el-option label="服务运营者（获客匹配）" value="operator" />
              <el-option label="训犬师入驻" value="trainer" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="mode === 'register'" label="邮箱" prop="email">
            <el-input v-model="form.email" placeholder="用于账号找回" size="large" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input v-model="form.password" type="password" show-password size="large" placeholder="至少 8 位，含大小写/数字/符号" />
          </el-form-item>
          <el-form-item v-if="mode === 'register'" label="确认密码" prop="confirm">
            <el-input v-model="form.confirm" type="password" size="large" placeholder="再次输入密码" @keyup.enter="submit" />
          </el-form-item>

          <el-form-item v-if="mode === 'login'">
            <el-checkbox v-model="form.remember">记住我</el-checkbox>
          </el-form-item>

          <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="submit">
            {{ mode === "login" ? "登录" : "注册" }}
          </el-button>
        </el-form>

        <el-button v-if="mode === 'register'" link type="primary" style="width: 100%; margin-top: 12px" @click="mode = 'login'">
          已有账号？去登录
        </el-button>
      </div>
    </div>
  </div>
</template>