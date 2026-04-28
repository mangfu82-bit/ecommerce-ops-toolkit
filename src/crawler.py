"""
数据采集模块
直接抓取 Bing 搜索结果，不依赖第三方搜索 API
"""

import json
import logging
import re
import time
from dataclasses import dataclass, asdict
from urllib.parse import quote_plus

import httpx

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """单条搜索结果"""
    keyword: str
    title: str
    url: str
    snippet: str

    def to_dict(self):
        return asdict(self)


class Crawler:
    """
    搜索爬虫
    基于 Bing 搜索，免费无需 API Key
    """

    def __init__(self, max_results: int = 8):
        self.max_results = max_results
        self._results: list[SearchResult] = []
        self._seen_urls: set[str] = set()

    def search(self, keywords: list[str]) -> list[SearchResult]:
        """搜索多个关键词，返回去重后的结果"""
        self._results = []
        self._seen_urls = set()

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

        with httpx.Client(headers=headers, timeout=30, follow_redirects=True) as client:
            for kw in keywords:
                logger.info(f"搜索: {kw}")
                try:
                    items = self._search_bing(client, kw)
                    for item in items:
                        if item.url not in self._seen_urls:
                            self._seen_urls.add(item.url)
                            self._results.append(item)
                except Exception as e:
                    logger.error(f"搜索失败 [{kw}]: {e}")

                time.sleep(1.5)

        logger.info(f"共获取 {len(self._results)} 条不重复结果")
        return self._results

    def _clean_html(self, text: str) -> str:
        """清理 HTML 标签"""
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'")
        # 去掉开头的域名残片（如 "zhihu.com › question › "）
        text = re.sub(r'^[\w.-]+\.(com|cn|net|org)\s*›\s*', '', text)
        return text.strip()

    def _search_bing(self, client: httpx.Client, keyword: str) -> list[SearchResult]:
        """抓取 Bing 搜索结果"""
        url = f"https://cn.bing.com/search?q={quote_plus(keyword)}&count={self.max_results}"
        resp = client.get(url)
        resp.raise_for_status()

        html = resp.text
        results = []

        # Bing 搜索结果在 <li class="b_algo"> 中
        # 每条结果: <h2><a href="URL">标题</a></h2> ... <p>摘要</p>
        blocks = re.split(r'<li class="b_algo"[^>]*>', html)

        for block in blocks[1:]:  # 跳过第一个空块
            # 提取链接和标题
            link_match = re.search(r'<h2[^>]*>.*?<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>.*?</h2>', block, re.DOTALL | re.IGNORECASE)
            if not link_match:
                continue

            link = link_match.group(1)
            title = self._clean_html(link_match.group(2))

            # 跳过 bing 和 microsoft 自身链接
            if 'bing.com' in link or 'microsoft.com' in link:
                continue

            # 提取摘要
            snippet = ""
            snippet_match = re.search(r'<div class="b_caption"[^>]*>.*?(?:<p[^>]*>(.*?)</p>|<div[^>]*class="b_factrow.*?">(.*?)</div>)', block, re.DOTALL | re.IGNORECASE)
            if snippet_match:
                snippet = self._clean_html(snippet_match.group(1) or snippet_match.group(2) or "")
            else:
                # 备用：直接找 <p> 标签
                p_match = re.search(r'<p[^>]*>(.*?)</p>', block, re.DOTALL | re.IGNORECASE)
                if p_match:
                    snippet = self._clean_html(p_match.group(1))

            if title:
                results.append(SearchResult(
                    keyword=keyword,
                    title=title,
                    url=link,
                    snippet=snippet[:200] if snippet else "",
                ))

            if len(results) >= self.max_results:
                break

        logger.info(f"  命中 {len(results)} 条")
        return results[:self.max_results]

    def export_json(self, filepath: str) -> None:
        """导出搜索结果到 JSON 文件"""
        data = [r.to_dict() for r in self._results]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"已导出 {len(data)} 条结果到 {filepath}")

    def get_results(self) -> list[SearchResult]:
        return list(self._results)
