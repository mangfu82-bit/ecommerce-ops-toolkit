"""
数据采集模块
负责多平台关键词搜索和结果收集
"""

import json
import logging
from dataclasses import dataclass, asdict
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """单条搜索结果"""
    platform: str
    keyword: str
    title: str
    url: str
    snippet: str

    def to_dict(self):
        return asdict(self)


class Crawler:
    """
    搜索爬虫
    
    通过搜索 API 采集各平台的运营资料，
    支持多关键词并行搜索和结果去重。
    """

    def __init__(self, search_api_url: Optional[str] = None, timeout: float = 30.0):
        self.api_url = search_api_url
        self.timeout = timeout
        self._results: list[SearchResult] = []
        self._seen_urls: set[str] = set()

    async def search(self, keywords: list[str]) -> list[SearchResult]:
        """
        搜索多个关键词，返回去重后的结果
        
        Args:
            keywords: 搜索关键词列表
            
        Returns:
            去重后的搜索结果列表
        """
        self._results = []
        self._seen_urls = set()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for kw in keywords:
                logger.info(f"搜索关键词: {kw}")
                try:
                    items = await self._search_one(client, kw)
                    for item in items:
                        if item.url not in self._seen_urls:
                            self._seen_urls.add(item.url)
                            self._results.append(item)
                except Exception as e:
                    logger.error(f"搜索失败 [{kw}]: {e}")

        logger.info(f"共获取 {len(self._results)} 条不重复结果")
        return self._results

    async def _search_one(self, client: httpx.AsyncClient, keyword: str) -> list[SearchResult]:
        """执行单次搜索"""
        # 这里对接实际的搜索 API（如元宝搜索、Google Custom Search 等）
        # 当前为示例实现，实际使用时替换为真实 API 调用
        
        if not self.api_url:
            logger.warning("未配置搜索 API URL，返回空结果")
            return []

        try:
            resp = await client.post(self.api_url, json={
                "query": keyword,
                "num": 10,
            })
            resp.raise_for_status()
            data = resp.json()

            results = []
            for item in data.get("items", []):
                results.append(SearchResult(
                    platform=item.get("platform", ""),
                    keyword=keyword,
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("snippet", ""),
                ))
            return results
        except httpx.HTTPError as e:
            logger.error(f"API 请求错误: {e}")
            return []

    def export_json(self, filepath: str) -> None:
        """导出搜索结果到 JSON 文件"""
        data = [r.to_dict() for r in self._results]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"已导出 {len(data)} 条结果到 {filepath}")

    def get_results(self) -> list[SearchResult]:
        return list(self._results)

    def filter_by_platform(self, platform: str) -> list[SearchResult]:
        """按平台过滤结果"""
        return [r for r in self._results if platform in r.platform.lower()]
