"""
供应链Agent
7天销量预测 + 采购提醒
使用Prophet做时序预测，LLM做上下文推理
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class SupplyChainAgent:
    """销量预测与采购建议"""

    def forecast(self, sku: str, sales_history: List[Dict], days: int = 7) -> Dict:
        """
        基于历史销量做预测
        sales_history: [{"date": "2026-04-20", "qty": 45}, ...]
        """
        if len(sales_history) < 7:
            return {"sku": sku, "forecast": None, "warning": "数据不足，至少需要7天历史"}

        # 简单移动平均预测（生产环境替换为Prophet）
        recent = [h["qty"] for h in sales_history[-7:]]
        avg = sum(recent) / len(recent)
        trend = (recent[-1] - recent[0]) / len(recent)

        predictions = []
        for i in range(days):
            predictions.append(round(avg + trend * (i + 1)))

        reorder_needed = avg * days > sum(recent) * 1.5

        logger.info(f"[SupplyChainAgent] SKU {sku}: 7日预测={predictions}")
        return {
            "sku": sku,
            "7day_forecast": predictions,
            "avg_daily": round(avg, 1),
            "trend": "up" if trend > 0 else "down" if trend < 0 else "flat",
            "reorder_needed": reorder_needed,
        }
