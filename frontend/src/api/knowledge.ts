import http from "./http";
import type { KnowledgeBase } from "@/types";

export interface KbCreatePayload {
  name: string;
  description?: string;
}

export const kbApi = {
  list() {
    return http.get<KnowledgeBase[], KnowledgeBase[]>("/kb");
  },
  create(data: KbCreatePayload) {
    return http.post<KnowledgeBase, KnowledgeBase>("/kb", data);
  },
  remove(id: number) {
    return http.delete<{ detail: string }, { detail: string }>(`/kb/${id}`);
  },
};