"""
学习Agent
将执行结果反馈到决策层，优化参数
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class LearningAgent:
    """从执行结果中学习，优化决策参数"""

    def learn(self, decision: Dict, outcome: Dict) -> Dict:
        """
        根据决策和结果，生成参数调整建议
        """
        adjustments = {}

        if decision.get("action") == "price_change":
            price_before = decision.get("price_before", 0)
            price_after = decision.get("price_after", 0)
            sales_delta = outcome.get("sales_change_pct", 0)

            if sales_delta > 0:
                adjustments["price_sensitivity"] = "low"
            else:
                adjustments["price_sensitivity"] = "high"

        logger.info(f"[LearningAgent] 参数调整: {adjustments}")
        return {"adjustments": adjustments, "source": "outcome_feedback"}
