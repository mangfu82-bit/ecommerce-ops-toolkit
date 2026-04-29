"""
向量知识库
基于embedding的语义检索
"""

import json
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)


class VectorStore:
    """简单的向量知识库（生产环境替换为FAISS/Milvus）"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self.entries: List[Dict] = []
        if db_path and Path(db_path).exists():
            self._load()

    def _load(self):
        with open(self.db_path, "r", encoding="utf-8") as f:
            self.entries = json.load(f)
        logger.info(f"加载 {len(self.entries)} 条知识")

    def add(self, text: str, metadata: Dict = None):
        self.entries.append({"text": text, "metadata": metadata or {}})

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        简单关键词匹配检索（生产环境替换为向量相似度）
        """
        query_terms = set(query.lower().split())
        scored = []
        for entry in self.entries:
            entry_terms = set(entry["text"].lower().split())
            overlap = len(query_terms & entry_terms)
            if overlap > 0:
                scored.append((overlap, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:top_k]]

    def save(self, path: str = None):
        out = path or self.db_path
        if out:
            with open(out, "w", encoding="utf-8") as f:
                json.dump(self.entries, f, ensure_ascii=False, indent=2)
            logger.info(f"保存 {len(self.entries)} 条知识到 {out}")
