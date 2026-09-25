import http from "./http";

export interface MediaOut {
  id: number;
  url: string;
  filename: string;
  content_type: string;
  size: number;
  purpose: string;
}

/** 上传图片到数据库，返回可直接用于 <img src> 的 /api/media/{id} */
export async function uploadMedia(
  file: File,
  purpose: "pet" | "listing" | "product" | "trainer" | "other" = "other",
) {
  const fd = new FormData();
  fd.append("file", file);
  // 不要手动设 Content-Type，让浏览器带 multipart boundary
  return http.post(`/media/upload?purpose=${purpose}`, fd) as Promise<MediaOut>;
}

/** 外链保持原样；相对路径补全，便于展示 */
export function mediaSrc(url: string | null | undefined, fallback = ""): string {
  if (!url) return fallback;
  if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("data:")) return url;
  if (url.startsWith("/")) return url;
  return `/${url}`;
}
