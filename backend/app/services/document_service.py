import re
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()


def extract_text(file_path: str, file_type: str) -> str:
    suffix = file_type.lower()
    if suffix == "pdf":
        from pypdf import PdfReader

        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix in ("docx",):
        from docx import Document

        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)
    if suffix in ("txt", "md", "markdown", "mdx"):
        raw = Path(file_path).read_text(encoding="utf-8")
        # 剥掉 mdx frontmatter(---...---) 与 top-level import，避免库内容被前端样板污染
        lines = raw.splitlines()
        cleaned = []
        in_fm = False
        for ln in lines:
            if ln.startswith("---") and not in_fm:
                in_fm = True
                continue
            if in_fm and ln.startswith("---"):
                in_fm = False
                continue
            if in_fm:
                continue
            if ln.startswith("import ") or ln.startswith("export ") or ln.startswith("//"):
                continue
            cleaned.append(ln)
        return "\n".join(cleaned)
    if suffix in ("csv",):
        return Path(file_path).read_text(encoding="utf-8")
    raise ValueError(f"不支持的文件类型: {file_type}")


def split_into_chunks(text: str) -> list[str]:
    """按字符块切分，带重叠，避免割断上下文。"""
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    size, overlap = settings.CHUNK_SIZE, settings.CHUNK_OVERLAP
    chunks: list[str] = []
    start = 0
    while start < len(text):
        piece = text[start : start + size]
        if piece.strip():
            chunks.append(piece)
        if start + size >= len(text):
            break
        start = start + size - overlap
    return chunks