from app.core.config import get_settings
from app.services.embedding_service import embedding_service

settings = get_settings()


class VectorDBService:
    """封装 Milvus 集合操作与检索。"""

    def __init__(self):
        self.collection_name = settings.MILVUS_COLLECTION
        self.dim = settings.EMBEDDING_DIM

    def _connect(self):
        from pymilvus import MilvusClient

        return MilvusClient(f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}")

    def _ensure_index(self, client):
        """Milvus 检索必须为 collection 建立向量索引。"""
        idx = client.list_indexes(self.collection_name)
        if not idx:
            from pymilvus import DataType
            index_params = client.prepare_index_params()
            index_params.add_index(
                field_name="vector",
                index_type="AUTOINDEX",
                metric_type="COSINE",
            )
            client.create_index(self.collection_name, index_params)

    def ensure_collection(self):
        client = self._connect()
        if not client.has_collection(self.collection_name):
            from pymilvus import DataType
            # schema 显式声明: 主键 id(int64, auto_id) + 向量 + 元数据字段
            from pymilvus.orm.schema import CollectionSchema, FieldSchema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.dim),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=4096),
                FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="kb_id", dtype=DataType.VARCHAR, max_length=64),
            ]
            schema = CollectionSchema(fields, description="knowledge chunks")
            client.create_collection(
                collection_name=self.collection_name,
                schema=schema,
            )
        self._ensure_index(client)
        # Milvus 检索前必须先把集合加载进内存
        if client.get_load_state(self.collection_name) != "LoadStateLoaded":
            client.load_collection(self.collection_name)
        return client

    def add_document_chunks(self, doc_id: int, kb_id: int, chunks: list[str]):
        """将文档切块向量化后写入 Milvus，metadata 记录来源文档与知识库。"""
        if not chunks:
            return
        client = self.ensure_collection()
        vectors = embedding_service.embed(chunks)
        self._insert(client, doc_id, kb_id, chunks, vectors)

    def add_document_chunks_precomputed(
        self, doc_id: int, kb_id: int, chunks: list[str], vectors
    ):
        """写入已计算好的向量（供批量导入复用，避免重复编码）。"""
        if not chunks:
            return
        client = self.ensure_collection()
        self._insert(client, doc_id, kb_id, chunks, vectors)

    def _insert(self, client, doc_id, kb_id, chunks, vectors):
        data = []
        for chunk, vec in zip(chunks, vectors):
            data.append(
                {
                    "vector": vec.tolist() if hasattr(vec, "tolist") else vec,
                    "text": chunk,
                    "doc_id": str(doc_id),
                    "kb_id": str(kb_id),
                }
            )
        client.insert(self.collection_name, data)

    def delete_by_kb(self, kb_id: int):
        """按知识库删除 Milvus 中所有向量。"""
        client = self.ensure_collection()
        expr = f'kb_id == "{kb_id}"'
        client.delete(self.collection_name, filter=expr)

    def delete_by_doc(self, doc_id: int):
        """按文档 id 删除 Milvus 中对应向量。"""
        client = self.ensure_collection()
        expr = f'doc_id == "{doc_id}"'
        client.delete(self.collection_name, filter=expr)

    def search(self, query: str, kb_id: int, top_k: int | None = None) -> list[dict]:
        """查询向量化后召回最相关 chunk，可按知识库过滤。"""
        client = self.ensure_collection()
        top_k = top_k or settings.TOP_K
        query_vec = embedding_service.embed_one(query)
        expr = f'kb_id == "{kb_id}"'
        res = client.search(
            collection_name=self.collection_name,
            data=[query_vec],
            limit=top_k,
            output_fields=["text"],
            filter=expr,
        )
        hits = []
        for hit in res[0]:
            hits.append({"text": hit["entity"]["text"], "score": hit["distance"]})
        return hits


vector_db_service = VectorDBService()