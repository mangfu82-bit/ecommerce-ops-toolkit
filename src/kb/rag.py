"""
RAG检索管线
本地知识库优先，Bing补充
"""

import logging
from typing import List, Dict

from src.kb.vector_store import VectorStore
from src.crawler import Crawler

logger = logging.getLogger(__name__)


class RAGPipeline:
    """检索增强生成管线"""

    def __init__(self, vector_store: VectorStore = None, bing_fallback: bool = True):
        self.kb = vector_store or VectorStore()
        self.bing_fallback = bing_fallback
        self.crawler = Crawler() if bing_fallback else None

    def query(self, question: str, top_k: int = 5) -> Dict:
        """
        1. 先从本地知识库检索
        2. 检索不足时调Bing补充
        3. 合并结果
        """
        # 本地检索
        local_results = self.kb.search(question, top_k=top_k)

        sources = {"local": local_results, "bing": []}

        # 本地不够，Bing补充
        if len(local_results) < 3 and self.crawler:
            logger.info("本地结果不足，调Bing补充")
            bing_results = self.crawler.search([question])
            sources["bing"] = [r.to_dict() for r in bing_results]

        total = len(sources["local"]) + len(sources["bing"])
        logger.info(f"RAG查询完成: 本地{len(sources['local'])}条 + Bing{len(sources['bing'])}条")

        return {
            "question": question,
            "sources": sources,
            "total_results": total,
        }
