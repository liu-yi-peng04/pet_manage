import http from "./http";
import type { DocumentItem } from "@/types";

// 后端仅返回 id/filename/file_type/status/created_at，
// 前端扩展字段在 view 层填充
export interface DocEx extends DocumentItem {
  size?: number;
  kb_id?: number;
}

export const docApi = {
  listByKb(kbId: number) {
    return http.get<DocumentItem[], DocumentItem[]>(`/kb/${kbId}/documents`);
  },
  listAll() {
    return http.get<DocumentItem[], DocumentItem[]>("/documents");
  },
  upload(kbId: number, file: File, onProgress?: (pct: number) => void) {
    const fd = new FormData();
    fd.append("file", file);
    return http.post<DocumentItem, DocumentItem>(`/kb/${kbId}/documents`, fd, {
      onUploadProgress: (e) => {
        if (e.total && onProgress) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      },
    });
  },
  remove(id: number) {
    return http.delete<{ detail: string }, { detail: string }>(`/documents/${id}`);
  },
};