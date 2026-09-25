from functools import lru_cache

import httpx
import numpy as np

from app.core.config import get_settings

settings = get_settings()


class EmbeddingService:
    """把文本向量化。provider=local 用本地 bge-m3；provider=api 走 OpenAI 兼容接口。"""

    def embed(self, texts: list[str]) -> np.ndarray:
        if settings.EMBEDDING_PROVIDER == "local":
            return self._embed_local(texts)
        return self._embed_api(texts)

    def embed_one(self, text: str) -> list[float]:
        vec = self.embed([text])[0]
        return vec.tolist()

    def _embed_local(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, settings.EMBEDDING_DIM), dtype=np.float32)
        model = self._get_model()
        # bge 系列建议加入 query 前缀提示，normalize_embeddings 统一长度便于余弦相似度
        vectors = model.encode(texts, normalize_embeddings=True)
        return np.asarray(vectors, dtype=np.float32)

    @lru_cache
    def _get_model(self):
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(settings.EMBEDDING_MODEL)

    def _embed_api(self, texts: list[str]) -> np.ndarray:
        payload = {"model": settings.EMBEDDING_MODEL, "input": texts}
        headers = {"Authorization": f"Bearer {settings.EMBEDDING_API_KEY}"}
        with httpx.Client(timeout=30) as client:
            resp = client.post(settings.EMBEDDING_API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()["data"]
        vectors = [item["embedding"] for item in data]
        arr = np.asarray(vectors, dtype=np.float32)
        arr = arr / np.linalg.norm(arr, axis=1, keepdims=True)
        return arr


embedding_service = EmbeddingService()