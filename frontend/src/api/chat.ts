import http from "./http";
import type { ChatReply } from "@/types";

export const chatApi = {
  ask(kbId: number, content: string, conversationId?: number) {
    return http.post<ChatReply, ChatReply>("/chat", {
      kb_id: kbId,
      content,
      conversation_id: conversationId ?? null,
    });
  },
  conversations() {
    return http.get<ChatReply[], ChatReply[]>("/chat/conversations");
  },
};