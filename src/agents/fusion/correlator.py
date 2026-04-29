"""
跨平台关联Agent
发现不同平台之间的数据关联模式
"""

import logging
from collections import defaultdict
from typing import List, Dict

from src.agents.base import CollectedData

logger = logging.getLogger(__name__)


class CorrelationAgent:
    """分析跨平台数据关联性"""

    def __init__(self):
        self.patterns = []

    def analyze(self, data: List[CollectedData]) -> List[Dict]:
        """
        在多个平台的数据中寻找关联模式
        例如：同一商品在不同平台的价格差异
        """
        by_keyword = defaultdict(list)
        for item in data:
            by_keyword[item.title[:20]].append(item)

        correlations = []
        for key, items in by_keyword.items():
            platforms = set(i.platform for i in items)
            if len(platforms) > 1:
                correlations.append({
                    "keyword": key,
                    "platforms": list(platforms),
                    "items": [i.to_dict() for i in items],
                    "type": "cross_platform_match",
                })

        logger.info(f"发现 {len(correlations)} 条跨平台关联")
        return correlations
