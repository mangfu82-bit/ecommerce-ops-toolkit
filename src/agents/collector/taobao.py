"""
淘宝数据采集Agent
采集搜索排名、评价数据、活动规则
"""

import re
import time
import logging
from typing import List

import httpx

from src.agents.base import BaseCollector, CollectedData

logger = logging.getLogger(__name__)


class TaobaoCollector(BaseCollector):
    platform = "taobao"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

    def check_access(self) -> bool:
        try:
            with httpx.Client(headers=self.headers, timeout=10) as c:
                r = c.get("https://www.taobao.com")
                return r.status_code == 200
        except Exception:
            return False

    def collect(self, keywords: List[str] = None) -> List[CollectedData]:
        results = []
        keywords = keywords or ["鲜花闪购", "淘宝闪购入驻", "淘宝商家规则"]

        with httpx.Client(headers=self.headers, timeout=30, follow_redirects=True) as client:
            for kw in keywords:
                try:
                    items = self._scrape_search(client, kw)
                    results.extend(items)
                except Exception as e:
                    logger.error(f"[taobao] 采集失败 [{kw}]: {e}")
                time.sleep(self.delay)

        self.log_result(len(results))
        return results

    def _scrape_search(self, client: httpx.Client, keyword: str) -> List[CollectedData]:
        """通过Bing搜索淘宝相关运营内容"""
        from urllib.parse import quote_plus
        url = f"https://cn.bing.com/search?q={quote_plus(keyword + ' site:taobao.com')}&count=8"
        resp = client.get(url)
        resp.raise_for_status()

        results = []
        blocks = re.split(r'<li class="b_algo"[^>]*>', resp.text)
        for block in blocks[1:]:
            link_match = re.search(r'href="(https?://[^"]*taobao[^"]*)"', block, re.IGNORECASE)
            title_match = re.search(r'<a[^>]*>(.*?)</a>', block, re.DOTALL | re.IGNORECASE)
            if link_match and title_match:
                title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
                results.append(CollectedData(
                    platform=self.platform,
                    data_type="search_ranking",
                    title=title,
                    value=link_match.group(1),
                ))
        return results[:8]
