"""
定价Agent
基于竞品+库存+历史数据生成价格建议
"""

import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class PricingAgent:
    """生成SKU定价建议"""

    def generate_recommendations(
        self,
        sku: str,
        current_price: float,
        competitor_prices: List[float],
        inventory_level: str = "normal",
    ) -> Dict:
        """
        输出3个定价方案及置信度
        """
        if not competitor_prices:
            return {"sku": sku, "recommendation": "no_data", "options": []}

        avg_comp = sum(competitor_prices) / len(competitor_prices)
        min_comp = min(competitor_prices)

        options = [
            {"price": round(min_comp * 0.95, 2), "label": "aggressive", "confidence": 0.6},
            {"price": round(avg_comp * 0.98, 2), "label": "balanced", "confidence": 0.8},
            {"price": round(avg_comp * 1.02, 2), "label": "premium", "confidence": 0.5},
        ]

        if inventory_level == "high":
            options[0]["confidence"] += 0.1
        elif inventory_level == "low":
            options[2]["confidence"] += 0.1

        logger.info(f"[PricingAgent] SKU {sku}: balanced={options[1]['price']}")
        return {"sku": sku, "recommendation": "balanced", "options": options}
