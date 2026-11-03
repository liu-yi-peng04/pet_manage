<script setup lang="ts">
import { reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { workspaceApi } from "@/api/workspace";
import { docApi } from "@/api/document";
import type { DocumentItem } from "@/types";
import { fmtDate } from "./shared";

interface KbMsg {
  role: "user" | "assistant";
  text: string;
  tools: string[];
}

const storeKb = ref<{ id: number; name: string; description: string } | null>(null);
const kbDocs = ref<DocumentItem[]>([]);
const kbLoading = ref(false);
const uploading = ref(false);
const kbFileInput = ref<HTMLInputElement | null>(null);

const kbConsult = ref<"policy" | "pet">("policy");
const kbMsgs = ref<KbMsg[]>([]);
const kbQ = ref("");
const kbAsking = ref(false);
const kbWaitingHint = ref(false);
let kbConvId: number | null = null;
let kbWaitTimer: ReturnType<typeof setTimeout> | null = null;

async function fetchKbDocs() {
  kbLoading.value = true;
  try {
    kbDocs.value = await workspaceApi.storeKbDocuments();
  } finally {
    kbLoading.value = false;
  }
}

async function reload() {
  storeKb.value = await workspaceApi.storeKb();
  await fetchKbDocs();
}

function pickKbFile() {
  kbFileInput.value?.click();
}

async function onKbFile(ev: Event) {
  const input = ev.target as HTMLInputElement;
  const f = input.files?.[0];
  if (!f) return;
  if (!storeKb.value) await reload();
  uploading.value = true;
  try {
    await docApi.upload(storeKb.value!.id, f);
    ElMessage.success("已上传并入库");
    await fetchKbDocs();
  } finally {
    uploading.value = false;
    input.value = "";
  }
}

async function removeKbDoc(d: DocumentItem) {
  await ElMessageBox.confirm(`确定删除「${d.filename}」？`, "删除确认", {
    type: "warning",
    confirmButtonText: "删除",
    cancelButtonText: "取消",
    confirmButtonClass: "el-button--danger",
  });
  await docApi.remove(d.id);
  ElMessage.success("已删除");
  await fetchKbDocs();
}

function kbRoleLabel(r: string) {
  return r === "user" ? "我" : kbConsult.value === "policy" ? "制度助手" : "养宠顾问";
}

function clearKbChat() {
  kbMsgs.value = [];
  kbConvId = null;
}

async function askKb() {
  const q = kbQ.value.trim();
  if (!q || kbAsking.value) return;
  if (!storeKb.value) await reload();
  const kbId = storeKb.value!.id;
  kbMsgs.value.push({ role: "user", text: q, tools: [] });
  kbQ.value = "";
  const asst = reactive<KbMsg>({ role: "assistant", text: "", tools: [] });
  kbMsgs.value.push(asst);
  kbAsking.value = true;
  kbWaitingHint.value = false;
  if (kbWaitTimer) clearTimeout(kbWaitTimer);
  kbWaitTimer = setTimeout(() => {
    if (kbAsking.value) kbWaitingHint.value = true;
  }, 3500);
  const token = localStorage.getItem("token");
  try {
    const resp = await fetch("/api/chat/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        kb_id: kbId,
        content: q,
        conversation_id: kbConvId,
        consult_type: "policy",
        pet_id: null,
      }),
    });
    const reader = resp.body!.getReader();
    const dec = new TextDecoder();
    let buf = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let idx: number;
      while ((idx = buf.indexOf("\n\n")) >= 0) {
        const chunk = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        const line = chunk.split("\n").find((l) => l.startsWith("data: "));
        if (!line) continue;
        const payload = line.slice(6);
        try {
          const ev = JSON.parse(payload);
          if (ev.type === "tool" && ev.summary) asst.tools.push(ev.summary);
          else if (ev.type === "conv" && ev.id) kbConvId = ev.id;
          else if (ev.type === "delta" && ev.content) asst.text += ev.content;
          else if (ev.type === "error") asst.text += `\n（出错：${ev.content}）`;
        } catch {
          if (payload.startsWith("[TOOL]")) asst.tools.push(payload.slice(6));
          else if (payload.startsWith("[MSG]")) kbConvId = Number(payload.slice(6));
          else if (payload !== "[DONE]") asst.text += payload;
        }
      }
    }
  } catch (e) {
    asst.text += (asst.text ? "\n" : "") + `（请求失败：${e}）`;
  }
  kbAsking.value = false;
  kbWaitingHint.value = false;
  if (kbWaitTimer) {
    clearTimeout(kbWaitTimer);
    kbWaitTimer = null;
  }
}

defineExpose({ reload });
</script>

<template>
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px">
    <div>
      <b>{{ storeKb?.name ?? "本店内容库" }}</b>
      <span class="text-muted" style="margin-left: 8px; font-size: 12px">
        店内制度/条款/商品说明/SOP，供店员问答与培训
      </span>
    </div>
    <el-button type="primary" size="small" :loading="uploading" @click="pickKbFile">上传文档</el-button>
    <input
      ref="kbFileInput"
      type="file"
      style="display: none"
      accept=".pdf,.docx,.txt,.md,.mdx,.csv"
      @change="onKbFile"
    />
  </div>

  <el-table v-loading="kbLoading" :data="kbDocs" style="width: 100%">
    <el-table-column prop="filename" label="文档" min-width="220" />
    <el-table-column prop="file_type" label="类型" width="90" />
    <el-table-column label="状态" width="110">
      <template #default="{ row }">
        <el-tag size="small" :type="row.status === 'indexed' ? 'success' : 'info'" effect="plain">
          {{ row.status === "indexed" ? "已入库" : "处理中" }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="上传时间" width="180">
      <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
    </el-table-column>
    <el-table-column label="操作" width="90" align="right">
      <template #default="{ row }">
        <el-button size="small" type="danger" link @click="removeKbDoc(row)">删除</el-button>
      </template>
    </el-table-column>
  </el-table>
  <el-empty v-if="!kbLoading && !kbDocs.length" description="尚未上传文档，上传后店员可据此问答" :image-size="70" />

  <el-divider content-position="left">店内 AI（与用户端隔离）</el-divider>
  <el-alert
    type="info"
    :closable="false"
    show-icon
    style="margin-bottom: 12px"
    title="只答本店制度/SOP（寄养收费、售宠话术等）。用户养宠问答不会出现在这里；商家没有「我的宠物」。"
  />
  <el-alert
    v-if="kbWaitingHint"
    type="warning"
    :closable="false"
    show-icon
    style="margin-bottom: 12px"
    title="回答需要一点时间，可先处理预约或订单，稍后再回来查看。"
  />
  <div>
    <div v-for="(m, i) in kbMsgs" :key="i" style="margin-bottom: 10px">
      <div style="font-size: 12px; color: #909399; margin-bottom: 2px">
        {{ kbRoleLabel(m.role) }}
        <el-tag
          v-for="(t, ti) in m.tools"
          :key="ti"
          size="small"
          type="info"
          effect="plain"
          style="margin-left: 6px"
        >{{ t }}</el-tag>
      </div>
      <div style="white-space: pre-wrap">{{ m.text }}</div>
    </div>
    <el-empty v-if="!kbMsgs.length" description="问寄养收费、售宠话术、退换货 SOP，将检索本店内容库" :image-size="60" />
    <div style="display: flex; gap: 8px; margin-top: 12px">
      <el-input
        v-model="kbQ"
        placeholder="例如：顾客要寄养中型犬怎么收费？"
        @keyup.enter="askKb"
        :disabled="kbAsking"
      />
      <el-button type="primary" :loading="kbAsking" @click="askKb">发送</el-button>
    </div>
    <el-button
      v-if="kbMsgs.length"
      size="small"
      link
      type="info"
      style="margin-top: 6px"
      @click="clearKbChat"
    >清空对话</el-button>
  </div>
</template>
