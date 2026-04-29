"""
美团闪购数据采集Agent
采集配送时效、竞对出价、店铺评分
"""

import re
import time
import logging
from typing import List

import httpx

from src.agents.base import BaseCollector, CollectedData

logger = logging.getLogger(__name__)


class MeituanCollector(BaseCollector):
    platform = "meituan"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

    def check_access(self) -> bool:
        try:
            with httpx.Client(headers=self.headers, timeout=10) as c:
                r = c.get("https://www.meituan.com")
                return r.status_code == 200
        except Exception:
            return False

    def collect(self, keywords: List[str] = None) -> List[CollectedData]:
        results = []
        keywords = keywords or ["美团闪购鲜花", "美团闪购商家入驻", "美团有花漾"]

        with httpx.Client(headers=self.headers, timeout=30, follow_redirects=True) as client:
            for kw in keywords:
                try:
                    items = self._scrape_search(client, kw)
                    results.extend(items)
                except Exception as e:
                    logger.error(f"[meituan] 采集失败 [{kw}]: {e}")
                time.sleep(self.delay)

        self.log_result(len(results))
        return results

    def _scrape_search(self, client: httpx.Client, keyword: str) -> List[CollectedData]:
        from urllib.parse import quote_plus
        url = f"https://cn.bing.com/search?q={quote_plus(keyword + ' site:meituan.com')}&count=8"
        resp = client.get(url)
        resp.raise_for_status()

        results = []
        blocks = re.split(r'<li class="b_algo"[^>]*>', resp.text)
        for block in blocks[1:]:
            link_match = re.search(r'href="(https?://[^"]*)"', block, re.IGNORECASE)
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
