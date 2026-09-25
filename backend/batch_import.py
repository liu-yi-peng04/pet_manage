"""批量导入(纯同步稳定版): pymysql 写库 + 同步嵌入 + Milvus 写入，无 asyncio，绝无事件循环崩溃。

用法:
  python batch_import.py <kb_id> [目录]
默认目录 D:\\ai_agent\\kb_docs
"""
import datetime as dt
import re
import sys
from pathlib import Path

import pymysql

from app.core.config import get_settings
from app.services.document_service import extract_text, split_into_chunks

DEFAULT_DIR = Path(r"D:\ai_agent\kb_docs")
ALLOWED = {"pdf", "docx", "txt", "md", "markdown", "mdx", "csv"}


def _parse_db_url(url: str) -> dict:
    m = re.match(r"mysql://([^:]+):([^@]+)@([^:]+):(\d+)/(\w+)", url)
    u, p, h, port, db = m.groups()
    return {"user": u, "password": p, "host": h, "port": int(port), "database": db}


def main():
    kb_id = int(sys.argv[1])
    src = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_DIR
    s = get_settings()
    cfg = _parse_db_url(s.DATABASE_URL)

    conn = pymysql.connect(
        host=cfg["host"], user=cfg["user"], password=cfg["password"],
        database=cfg["database"], port=cfg["port"], charset="utf8mb4", autocommit=True,
    )
    cur = conn.cursor()
    cur.execute("SELECT filename FROM document WHERE kb_id=%s AND status='indexed'", (kb_id,))
    existing = {r[0] for r in cur.fetchall()}

    files = sorted(
        (p for p in src.rglob("*") if p.is_file() and p.suffix.lstrip(".") in ALLOWED),
        key=lambda x: str(x),
    )
    todo = [p for p in files if p.relative_to(src).as_posix() not in existing]
    print(f"待处理 {len(todo)} 个文档 (已跳过 {len(files)-len(todo)} 个)")

    from app.services.embedding_service import embedding_service
    from app.services.vectordb_service import vector_db_service

    ok, fail, skip = 0, 0, 0
    for i, p in enumerate(todo, 1):
        rel = p.relative_to(src).as_posix()
        try:
            text = extract_text(str(p), p.suffix.lstrip("."))
            chunks = split_into_chunks(text)
            if not chunks:
                skip += 1
                print(f"  [{i}/{len(todo)}] SKIP(empty) {rel}", flush=True)
                continue
            now = dt.datetime.now()
            cur.execute(
                "INSERT INTO document (filename,file_path,file_type,status,created_at,kb_id) "
                "VALUES (%s,%s,%s,'indexing',%s,%s)",
                (rel, str(p), p.suffix.lstrip("."), now, kb_id),
            )
            doc_id = cur.lastrowid
            vector_db_service.add_document_chunks(doc_id, kb_id, chunks)
            cur.execute("UPDATE document SET status='indexed' WHERE id=%s", (doc_id,))
            ok += 1
            print(f"  [{i}/{len(todo)}] OK {rel} ({len(chunks)}chunks)", flush=True)
        except Exception as e:
            fail += 1
            print(f"  [{i}/{len(todo)}] FAIL {rel}: {e}", flush=True)

    conn.close()
    print(f"\n完成: 成功 {ok}，跳过 {skip}，失败 {fail}")


if __name__ == "__main__":
    main()