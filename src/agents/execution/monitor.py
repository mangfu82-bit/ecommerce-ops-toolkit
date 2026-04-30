"""
监控Agent - LLM驱动的智能监控与预警系统
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import random

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AlertType(Enum):
    PRICE_ANOMALY = "price_anomaly"
    SALES_DROP = "sales_drop"
    INVENTORY_LOW = "inventory_low"
    COMPETITOR_ALERT = "competitor_alert"
    OPPORTUNITY = "opportunity"


@dataclass
class Alert:
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    platform: str
    title: str
    description: str
    metrics: Dict[str, Any]
    suggested_action: str = ""
    created_at: str = ""
    acknowledged: bool = False


class MonitoringAgent:
    """LLM驱动的智能监控Agent"""
    
    def __init__(self, llm_client=None, config: Optional[Dict] = None):
        self.llm = llm_client
        self.config = config or {}
        self.active_alerts: List[Alert] = []
        self.metrics_history: Dict[str, List] = {}
        self.thresholds = {
            "price_change_pct": 0.15,
            "sales_drop_pct": 0.30,
            "inventory_min": 10,
        }
    
    async def check_anomalies(self, metrics: List[Dict]) -> List[Alert]:
        """检查异常"""
        alerts = []
        
        for m in metrics:
            platform = m.get("platform", "unknown")
            item_id = m.get("item_id", "")
            
            # 价格异常
            if "price" in m:
                price_change = m.get("price_change", 0)
                if abs(price_change) > self.thresholds["price_change_pct"]:
                    alerts.append(Alert(
                        alert_id=f"alert_{datetime.now().strftime('%Y%m%d%H%M%S')}_{item_id}",
                        alert_type=AlertType.PRICE_ANOMALY,
                        severity=AlertSeverity.HIGH,
                        platform=platform,
                        title=f"价格异常波动 {price_change*100:.1f}%",
                        description=f"商品{item_id}价格变化超过阈值",
                        metrics={"price_change": price_change},
                        suggested_action="检查竞品定价，调整策略",
                        created_at=datetime.now().isoformat(),
                    ))
            
            # 销量下降
            if "sales_drop" in m:
                if m["sales_drop"] > self.thresholds["sales_drop_pct"]:
                    alerts.append(Alert(
                        alert_id=f"alert_{datetime.now().strftime('%Y%m%d%H%M%S')}_{item_id}",
                        alert_type=AlertType.SALES_DROP,
                        severity=AlertSeverity.MEDIUM,
                        platform=platform,
                        title=f"销量下降 {m['sales_drop']*100:.1f}%",
                        description=f"商品{item_id}销量显著下降",
                        metrics={"sales_drop": m["sales_drop"]},
                        suggested_action="分析原因，优化商品或促销",
                        created_at=datetime.now().isoformat(),
                    ))
        
        self.active_alerts.extend(alerts)
        return alerts
    
    async def get_dashboard_data(self) -> Dict:
        """获取仪表盘数据"""
        return {
            "active_alerts": len(self.active_alerts),
            "alerts_by_severity": {
                s.value: sum(1 for a in self.active_alerts if a.severity == s)
                for s in AlertSeverity
            },
            "metrics_summary": {
                "total_monitored": len(self.metrics_history),
                "last_updated": datetime.now().isoformat(),
            },
        }
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """确认告警"""
        for alert in self.active_alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False


# 简化接口
async def check_alerts(metrics: List[Dict], llm_client=None) -> List[Dict]:
    agent = MonitoringAgent(llm_client=llm_client)
    alerts = await agent.check_anomalies(metrics)
    return [
        {
            "alert_id": a.alert_id,
            "type": a.alert_type.value,
            "severity": a.severity.value,
            "title": a.title,
        }
        for a in alerts
    ]
