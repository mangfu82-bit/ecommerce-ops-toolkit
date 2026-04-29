"""
市场情报Agent
追踪竞品动态：调价、上新、促销
"""

import logging
from typing import List, Dict

from src.agents.base import CollectedData

logger = logging.getLogger(__name__)


class MarketIntelAgent:
    """竞品动态监控"""

    def analyze(self, data: List[CollectedData]) -> List[Dict]:
        """识别市场信号"""
        signals = []
        for item in data:
            title_lower = item.title.lower()
            if any(kw in title_lower for kw in ["调价", "降价", "涨价", "促销", "上新", "入驻"]):
                signals.append({
                    "platform": item.platform,
                    "signal": "price_change" if "价" in title_lower else "promotion",
                    "title": item.title,
                    "url": item.value,
                })

        logger.info(f"检测到 {len(signals)} 条市场信号")
        return signals
