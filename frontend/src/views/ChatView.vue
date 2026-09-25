<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from "vue";
import { useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import { marked } from "marked";
import { markedHighlight } from "marked-highlight";
import hljs from "highlight.js";
import "highlight.js/styles/github.css";
import { useChatStore } from "@/stores/chat";
import { useUserStore } from "@/stores/user";
import { petsApi, petDisplayName, type Pet } from "@/api/pets";
import { workspaceApi } from "@/api/workspace";

const router = useRouter();
const userStore = useUserStore();
const chat = useChatStore();
const { messages, currentConvId, historyCount, currentPetId } = storeToRefs(chat);
const question = ref("");
const asking = ref(false);
const waitingHint = ref(false);
const scrollRef = ref<HTMLElement>();
const pets = ref<Pet[]>([]);
// 商家端固定制度助手；养宠用户固定养宠顾问；管理端走平台公共库
const consultType = ref<"pet" | "policy">(userStore.isStaff ? "policy" : "pet");
const storeKbId = ref<number | null>(null);
let waitTimer: ReturnType<typeof setTimeout> | null = null;

const isStaffChat = computed(() => userStore.isStaff);
const isUserChat = computed(() => userStore.isEndUser || (!userStore.isStaff && !userStore.isAdmin && !userStore.isOperator));

const currentPet = computed(() => pets.value.find((p) => p.id === currentPetId.value) ?? null);

const petSamples = [
  { q: "根据档案给我一周喂养和运动计划", hint: "个性化方案" },
  { q: "接下来该打哪些疫苗、间隔多久", hint: "疫苗日程" },
  { q: "最近皮肤痒，先在家怎么处理、什么时候必须就医", hint: "分诊建议" },
  { q: "按体重推荐狗粮和用品，带上门店联系方式", hint: "用品导购" },
];
const policySamples = [
  { q: "本店寄养中型犬怎么收费、要带什么证明？", hint: "寄养制度" },
  { q: "退换货和售后怎么跟顾客解释？", hint: "售后规则" },
  { q: "美容服务包含哪些项目、注意事项？", hint: "服务 SOP" },
  { q: "员工接待新客户的标准话术是什么？", hint: "培训材料" },
];
const adminSamples = [
  { q: "平台对入驻宠物店有哪些规范要求？", hint: "平台制度" },
  { q: "用户投诉售后纠纷时运营应怎么处理？", hint: "运营规范" },
];
const samples = computed(() => {
  if (isStaffChat.value) return policySamples;
  if (userStore.isAdmin || userStore.isOperator) return adminSamples;
  return petSamples;
});

onMounted(async () => {
  // 仅养宠用户加载「我的宠物」；商家没有自家宠物
  if (userStore.isEndUser || userStore.userInfo?.role === "user") {
    try {
      pets.value = await petsApi.list();
      if (!currentPetId.value && pets.value.length === 1) currentPetId.value = pets.value[0].id;
    } catch {
      /* ignore */
    }
  }
  if (userStore.isStaff) {
    consultType.value = "policy";
    try {
      const kb = await workspaceApi.storeKb();
      storeKbId.value = kb.id;
    } catch {
      /* 无本店库 */
    }
  } else if (userStore.isAdmin || userStore.isOperator) {
    consultType.value = "pet"; // 平台公共知识，不绑用户宠物
  }
});

marked.use(
  markedHighlight({
    langPrefix: "hljs language-",
    highlight(code: string, lang: string) {
      const language = lang && hljs.getLanguage(lang) ? lang : "plaintext";
      try {
        return hljs.highlight(code, { language }).value;
      } catch {
        return hljs.highlightAuto(code).value;
      }
    },
  })
);

function renderMarkdown(src: string): string {
  return marked.parse(src, { breaks: true, gfm: true }) as string;
}

async function scrollBottom() {
  await nextTick();
  if (scrollRef.value) scrollRef.value.scrollTop = scrollRef.value.scrollHeight;
}

function setConsult(t: "pet" | "policy") {
  // 商家端不可切到用户养宠顾问
  if (isStaffChat.value && t === "pet") return;
  if (consultType.value === t) return;
  consultType.value = t;
  chat.clear();
}

function clearWaitHint() {
  waitingHint.value = false;
  if (waitTimer) {
    clearTimeout(waitTimer);
    waitTimer = null;
  }
}

async function ask() {
  if (!question.value.trim() || asking.value) return;
  const q = question.value;
  messages.value.push({ role: "user", content: q });
  question.value = "";
  asking.value = true;
  waitingHint.value = false;
  if (waitTimer) clearTimeout(waitTimer);
  // 正常检索/生成会花几秒：提示用户可先去做别的事
  waitTimer = setTimeout(() => {
    if (asking.value) waitingHint.value = true;
  }, 3500);

  const idx = messages.value.push({ role: "assistant", content: "", tools: [] as string[] }) - 1;
  await scrollBottom();

  const token = localStorage.getItem("token") ?? "";
  try {
    const resp = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        content: q,
        conversation_id: currentConvId.value,
        pet_id: consultType.value === "pet" && isUserChat.value ? currentPetId.value : null,
        consult_type: consultType.value,
        kb_id: consultType.value === "policy" ? storeKbId.value : null,
      }),
    });

    if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);

    const reader = resp.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (asking.value) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let sep: number;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const raw = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        for (const line of raw.split("\n")) {
          if (!line.startsWith("data:")) continue;
          const payload = line.slice(5).trim();
          await handleSse(payload, idx);
        }
        await scrollBottom();
      }
    }
    historyCount.value++;
  } catch (e) {
    messages.value[idx].content = "回答失败：" + (e as Error).message;
  } finally {
    asking.value = false;
    clearWaitHint();
    await scrollBottom();
  }
}

async function handleSse(payload: string, idx: number) {
  if (!payload) return;
  let ev: { type?: string; content?: string; summary?: string; id?: number };
  try {
    ev = JSON.parse(payload);
  } catch {
    if (payload.startsWith("[DONE]")) {
      asking.value = false;
      return;
    }
    if (payload.startsWith("[MSG]")) {
      currentConvId.value = Number(payload.slice(5));
      return;
    }
    if (payload.startsWith("[TOOL]")) {
      const sep = payload.indexOf("|");
      const summary = sep >= 0 ? payload.slice(sep + 1) : payload.slice(6);
      (messages.value[idx].tools as string[]).push(summary);
      return;
    }
    if (payload.startsWith("[ERR]")) {
      messages.value[idx].content += `\n\n> 出错：${payload.slice(5)}`;
      return;
    }
    messages.value[idx].content += payload;
    return;
  }
  if (ev.type === "done") {
    asking.value = false;
    return;
  }
  if (ev.type === "conv" && ev.id) {
    currentConvId.value = ev.id;
    return;
  }
  if (ev.type === "tool" && ev.summary) {
    (messages.value[idx].tools as string[]).push(ev.summary);
    return;
  }
  if (ev.type === "error") {
    messages.value[idx].content += `\n\n> 出错：${ev.content ?? ""}`;
    return;
  }
  if (ev.type === "delta" && ev.content) {
    messages.value[idx].content += ev.content;
  }
}

function newConversation() {
  chat.clear();
}
</script>

<template>
  <div style="display: flex; height: calc(100vh - var(--app-header-h)); overflow: hidden">
    <div style="width: 260px; border-right: 1px solid var(--app-border); background: var(--app-surface); display: flex; flex-direction: column">
      <div style="padding: 16px">
        <el-button type="primary" style="width: 100%" @click="newConversation">
          <el-icon style="margin-right: 4px"><Plus /></el-icon>新建会话
        </el-button>
      </div>
      <div style="padding: 0 16px 16px; font-size: 13px; line-height: 1.7; color: var(--app-text-secondary)">
        <div style="font-weight: 600; color: var(--app-text); margin-bottom: 6px">
          {{ isStaffChat ? "店内 / 医院 AI（独立通道）" : userStore.isAdmin ? "平台 AI（独立通道）" : "养宠顾问（独立通道）" }}
        </div>
        <div v-if="isStaffChat">只答本店制度与接待 SOP。商家没有「我的宠物」，用户养宠问答不会出现在这里。</div>
        <div v-else-if="userStore.isAdmin || userStore.isOperator">平台侧问答与用户/商家会话隔离，不可见对方聊天内容。</div>
        <div v-else>按自家宠物档案给方案。检索需要几秒属正常，可先去做别的事稍后再回来看。</div>
      </div>
      <div style="flex: 1; overflow-y: auto; padding: 0 12px">
        <div class="text-muted" style="font-size: 13px; padding: 12px; text-align: center">
          共进行 {{ historyCount }} 次问答
        </div>
      </div>
    </div>

    <div style="flex: 1; display: flex; flex-direction: column; min-width: 0">
      <div ref="scrollRef" style="flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 20px">
        <div v-if="!messages.length" style="flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--app-text-muted); padding: 0 24px">
          <el-icon :size="48"><ChatDotRound /></el-icon>
          <h3 style="color: var(--app-text); margin: 16px 0 8px">
            {{ isStaffChat ? "店内制度助手" : userStore.isAdmin || userStore.isOperator ? "平台助手" : "AI 宠物顾问" }}
          </h3>
          <p style="font-size: 14px; max-width: 520px; text-align: center; line-height: 1.7; margin: 0 0 20px">
            <template v-if="isStaffChat">只回答本店已上传的制度与流程；寄养收费、售宠话术等可直接问。</template>
            <template v-else-if="userStore.isAdmin || userStore.isOperator">平台规范与运营问题；不管理商家商品上架。</template>
            <template v-else>把档案写全并选中宠物，顾问会按体重、过敏、疫苗给步骤方案。</template>
          </p>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; max-width: 560px; width: 100%">
            <el-button v-for="s in samples" :key="s.q" @click="question = s.q" style="height: auto; padding: 10px 12px; white-space: normal; text-align: left">
              <span>
                <span style="display: block; font-size: 11px; color: var(--app-text-muted)">{{ s.hint }}</span>
                {{ s.q }}
              </span>
            </el-button>
          </div>
        </div>

        <template v-for="(m, i) in messages" :key="i">
          <div v-if="m.role === 'user'" style="display: flex; justify-content: flex-end">
            <div style="max-width: 70%; background: #2563eb; color: #fff; padding: 12px 16px; border-radius: 12px 12px 2px 12px; line-height: 1.6; white-space: pre-wrap">{{ m.content }}</div>
          </div>
          <div v-else style="display: flex; gap: 12px">
            <div style="width: 32px; height: 32px; border-radius: 8px; background: #2563eb18; color: #2563eb; display: flex; align-items: center; justify-content: center; flex-shrink: 0">
              <el-icon><MagicStick /></el-icon>
            </div>
            <div style="flex: 1; min-width: 0">
              <div class="text-muted" style="font-size: 12px; margin-bottom: 4px">AI 顾问</div>
              <div style="background: var(--app-surface); border: 1px solid var(--app-border); border-radius: 4px 12px 12px 12px; padding: 16px 20px">
                <template v-if="m.tools && m.tools.length">
                  <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px">
                    <el-tag v-for="(t, ti) in m.tools" :key="ti" size="small" type="info" effect="plain" style="color: var(--app-primary); border-color: var(--app-primary)">
                      <el-icon style="margin-right: 4px; vertical-align: -2px"><Loading v-if="asking && ti === m.tools.length - 1 && i === messages.length - 1" /></el-icon>{{ t }}
                    </el-tag>
                  </div>
                </template>
                <div v-if="!m.content && asking && i === messages.length - 1" class="text-muted" style="font-size: 13px">
                  正在检索知识库与档案，通常需要几秒…
                </div>
                <div class="markdown-body" v-html="renderMarkdown(m.content)"></div>
              </div>
            </div>
          </div>
        </template>
      </div>

      <div style="padding: 16px 24px 24px; border-top: 1px solid var(--app-border); background: var(--app-bg)">
        <el-alert
          v-if="waitingHint"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 10px"
          title="回答需要一点时间（检索档案/联网属正常）。你可以先去做别的事，稍后再回来查看结果。"
        />
        <el-alert
          v-if="isUserChat && consultType === 'pet' && !pets.length"
          type="warning"
          :closable="false"
          show-icon
          style="margin-bottom: 10px"
          title="还没有宠物档案。顾问只能给通用建议，个性化方案请先建档。"
        >
          <template #default>
            <el-button type="primary" link @click="router.push('/pets')">去添加宠物</el-button>
          </template>
        </el-alert>
        <el-alert
          v-else-if="isUserChat && consultType === 'pet' && !currentPetId"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 10px"
          title="请选择当前宠物。家里有两只同名狗时，用下拉框或昵称指定，避免方案给错。"
        />
        <div v-if="isUserChat && consultType === 'pet'" style="display: flex; gap: 12px; align-items: center; margin-bottom: 8px; flex-wrap: wrap">
          <span class="text-muted" style="font-size: 12px">方案针对</span>
          <el-select v-model="currentPetId" clearable placeholder="未绑定档案" style="width: 280px" size="small">
            <el-option v-for="p in pets" :key="p.id" :label="petDisplayName(p)" :value="p.id" />
          </el-select>
          <span v-if="currentPet?.allergies" class="text-muted" style="font-size: 12px">过敏：{{ currentPet.allergies }}</span>
        </div>
        <div style="display: flex; gap: 12px; align-items: flex-end">
          <el-input
            v-model="question"
            type="textarea"
            :rows="2"
            resize="none"
            :placeholder="isStaffChat ? '例如：顾客要寄养中型犬怎么收费？' : '例如：按旺财的体重和过敏，给一周饮食和运动安排'"
            :disabled="asking"
            @keyup.enter.exact.prevent="ask"
          />
          <el-button type="primary" :loading="asking" style="height: 56px; padding: 0 24px" @click="ask">
            {{ asking ? "生成中" : "发送" }}
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
:deep(.markdown-body) {
  line-height: 1.75;
  color: var(--app-text);
  font-size: 14.5px;
}
:deep(.markdown-body h1),
:deep(.markdown-body h2),
:deep(.markdown-body h3) {
  margin: 16px 0 8px;
  font-weight: 700;
  line-height: 1.4;
  color: var(--app-text);
}
:deep(.markdown-body h2) {
  font-size: 17px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--app-border);
}
:deep(.markdown-body h3) {
  font-size: 15px;
}
:deep(.markdown-body ul),
:deep(.markdown-body ol) {
  padding-left: 22px;
  margin: 6px 0 12px;
}
:deep(.markdown-body li) {
  margin: 4px 0;
}
:deep(.markdown-body blockquote) {
  margin: 8px 0;
  padding: 8px 12px;
  border-left: 3px solid var(--app-primary);
  background: #2563eb0d;
  color: var(--app-text-secondary);
}
:deep(.markdown-body pre) {
  background: #f6f8fa;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
}
:deep(.markdown-body code) {
  font-family: "JetBrains Mono", Consolas, monospace;
  font-size: 13px;
  background: #f3f4f6;
  padding: 1px 5px;
  border-radius: 4px;
}
:deep(.markdown-body pre code) {
  padding: 0;
  background: transparent;
}
:deep(.markdown-body p) {
  margin: 0 0 10px;
}
:deep(.markdown-body a) {
  color: var(--app-primary);
}
:deep(.markdown-body table) {
  border-collapse: collapse;
  margin: 8px 0 12px;
  width: 100%;
}
:deep(.markdown-body th),
:deep(.markdown-body td) {
  border: 1px solid var(--app-border);
  padding: 6px 10px;
}
.el-textarea__inner {
  box-shadow: none;
}
textarea {
  max-height: 120px;
}
</style>
