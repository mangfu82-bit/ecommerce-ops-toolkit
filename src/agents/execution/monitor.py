"""
监控Agent
跟踪执行结果，检测异常
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class MonitorAgent:
    """执行结果监控与异常告警"""

    def check(self, execution_result: Dict, expected: Dict = None) -> Dict:
        anomalies = []

        # 简单异常检测逻辑
        if execution_result.get("status") == "error":
            anomalies.append("execution_failed")

        if expected and execution_result.get("metrics"):
            actual = execution_result["metrics"].get("conversion_rate", 0)
            target = expected.get("target_conversion", 0)
            if target and actual < target * 0.5:
                anomalies.append("conversion_drop")

        result = {
            "healthy": len(anomalies) == 0,
            "anomalies": anomalies,
        }

        if anomalies:
            logger.warning(f"[MonitorAgent] 异常: {anomalies}")
        else:
            logger.info("[MonitorAgent] 状态正常")

        return result
