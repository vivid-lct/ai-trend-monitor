"""
vector_store.py - ChromaDB 封装（建库、增量入库、相似度检索）
持久化目录：data/chroma_db/（不提交 git）
"""
import logging
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

COLLECTION_NAME = "ai_trends"


class VectorStore:
    """
    封装 ChromaDB，提供：
      - add_items(items)  : 将 Item 列表向量化后入库（按 URL 去重）
      - search(query, k)  : 相似度检索，返回 top-k 条元数据
      - count()           : 返回当前库中记录数
    """

    def __init__(self,
                 persist_dir: str = "data/chroma_db",
                 embed_base_url: str = "http://localhost:11434"):
        import chromadb
        from chromadb.config import Settings

        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self._col = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self._embed_base_url = embed_base_url

    # ── 公开接口 ──────────────────────────────────────────────

    def add_items(self, items) -> int:
        """
        将 Item 列表增量入库。
        以 URL 作为 ChromaDB document id（URL 规范化后 hash）。
        返回实际新增条数（已存在的跳过）。
        """
        from src.rag.embedder import get_embedding
        import hashlib

        existing_ids = set(self._col.get(include=[])["ids"])
        added = 0

        for item in items:
            doc_id = hashlib.md5(item.url.encode()).hexdigest()
            if doc_id in existing_ids:
                continue

            text = f"{item.title}\n{item.content or ''}"
            embedding = get_embedding(text, base_url=self._embed_base_url)
            if not embedding:
                logger.warning(f"[VectorStore] 跳过（向量化失败）: {item.title[:40]}")
                continue

            pub_str = item.published_at.isoformat() if item.published_at else ""
            self._col.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[{
                    "title":    item.title,
                    "url":      item.url,
                    "source":   item.source,
                    "category": item.category,
                    "published_at": pub_str,
                    "score":    float(item.score),
                }],
            )
            existing_ids.add(doc_id)
            added += 1

        return added

    def search(self, query: str, top_k: int = 5) -> List[dict]:
        """
        向量相似度检索，返回 top_k 条元数据列表。
        每条包含：title / url / source / category / published_at / score / content
        """
        from src.rag.embedder import get_embedding

        if self.count() == 0:
            return []

        q_vec = get_embedding(query, base_url=self._embed_base_url)
        if not q_vec:
            return []

        results = self._col.query(
            query_embeddings=[q_vec],
            n_results=min(top_k, self.count()),
            include=["metadatas", "documents"],
        )

        hits = []
        for meta, doc in zip(results["metadatas"][0], results["documents"][0]):
            hits.append({**meta, "content": doc})
        return hits

    def count(self) -> int:
        return self._col.count()
