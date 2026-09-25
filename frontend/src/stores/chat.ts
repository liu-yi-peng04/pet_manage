import { ref, watch } from "vue";
import { defineStore } from "pinia";
import type { MessageItem } from "@/types";

interface ChatSnapshot {
  messages: MessageItem[];
  currentConvId: number | null;
  historyCount: number;
  currentPetId: number | null;
}

function channelOf(role: string | null | undefined): string {
  const r = (role || "user").toLowerCase();
  if (r === "staff" || r === "admin" || r === "operator" || r === "trainer") return r;
  return "user";
}

function storageKey(userId: number | null, channel: string): string {
  return `pet_chat_state_${userId ?? "guest"}_${channel}`;
}

function load(key: string): ChatSnapshot {
  try {
    const raw = localStorage.getItem(key);
    if (raw) return JSON.parse(raw) as ChatSnapshot;
  } catch {
    /* 解析失败则忽略 */
  }
  return { messages: [], currentConvId: null, historyCount: 0, currentPetId: null };
}

/** 各端 AI 独立持久化：按用户 + channel 隔离，互不串话 */
export const useChatStore = defineStore("chat", () => {
  const boundUserId = ref<number | null>(null);
  const boundChannel = ref("user");
  const messages = ref<MessageItem[]>([]);
  const currentConvId = ref<number | null>(null);
  const historyCount = ref(0);
  const currentPetId = ref<number | null>(null);

  function persist() {
    try {
      localStorage.setItem(
        storageKey(boundUserId.value, boundChannel.value),
        JSON.stringify({
          messages: messages.value,
          currentConvId: currentConvId.value,
          historyCount: historyCount.value,
          currentPetId: currentPetId.value,
        })
      );
    } catch {
      /* 存储满等异常忽略 */
    }
  }

  watch([messages, currentConvId, historyCount, currentPetId], persist, { deep: true });

  /** 登录/切号后绑定端通道，加载对应会话 */
  function bindIdentity(userId: number | null, role: string | null | undefined) {
    const nextChannel = channelOf(role);
    if (boundUserId.value === userId && boundChannel.value === nextChannel) return;
    boundUserId.value = userId;
    boundChannel.value = nextChannel;
    const snap = load(storageKey(userId, nextChannel));
    messages.value = snap.messages;
    currentConvId.value = snap.currentConvId;
    historyCount.value = snap.historyCount;
    currentPetId.value = snap.currentPetId ?? null;
  }

  function clear() {
    messages.value = [];
    currentConvId.value = null;
    historyCount.value = 0;
    persist();
  }

  /** 退出登录：清空内存态，不删其它账号的本地缓存 */
  function resetSession() {
    messages.value = [];
    currentConvId.value = null;
    historyCount.value = 0;
    currentPetId.value = null;
    boundUserId.value = null;
    boundChannel.value = "user";
  }

  return {
    messages,
    currentConvId,
    historyCount,
    currentPetId,
    boundChannel,
    clear,
    bindIdentity,
    resetSession,
  };
});
