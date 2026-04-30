"""
供应链决策Agent - LLM驱动的智能供应链管理
库存预警、采购建议、供应商评估、物流优化
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import math

logger = logging.getLogger(__name__)


class InventoryStatus(Enum):
    """库存状态"""
    CRITICAL = "critical"      # 危急（<7天）
    LOW = "low"               # 偏低（7-14天）
    NORMAL = "normal"         # 正常（14-60天）
    HIGH = "high"            # 偏高（60-90天）
    EXCESSIVE = "excessive"   # 过剩（>90天）


class AlertLevel(Enum):
    """预警等级"""
    URGENT = "urgent"         # 紧急
    WARNING = "warning"       # 警告
    INFO = "info"            # 提示
    NORMAL = "normal"        # 正常


class SupplierGrade(Enum):
    """供应商等级"""
    A = "A"  # 优质供应商
    B = "B"  # 合格供应商
    C = "C"  # 需改进供应商
    D = "D"  # 风险供应商


@dataclass
class InventoryItem:
    """库存项"""
    sku: str
    name: str
    quantity: int
    reserved: int = 0
    in_transit: int = 0
    daily_sales_rate: float = 0.0
    safety_stock: int = 0
    reorder_point: int = 0
    last_restock_date: Optional[datetime] = None
    category: str = ""
    warehouse: str = ""


@dataclass
class Supplier:
    """供应商信息"""
    id: str
    name: str
    grade: SupplierGrade
    lead_time_days: int
    min_order_qty: int
    price: float
    quality_score: float = 0.8
    delivery_score: float = 0.8
    response_time_hours: float = 24.0
    location: str = ""
    products: List[str] = field(default_factory=list)


@dataclass
class PurchaseOrder:
    """采购订单"""
    supplier_id: str
    sku: str
    quantity: int
    unit_price: float
    total_amount: float
    expected_delivery: datetime
    priority: str = "normal"
    status: str = "pending"


@dataclass
class SupplyChainAlert:
    """供应链预警"""
    alert_id: str
    level: AlertLevel
    type: str
    sku: str
    message: str
    recommendations: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None


class SupplyChainAgent:
    """LLM驱动的供应链管理Agent"""
    
    def __init__(self, llm_client=None, config: Optional[Dict] = None):
        self.llm = llm_client
        self.config = config or {}
        
        # 库存阈值配置
        self.thresholds = {
            "critical_days": 7,
            "low_days": 14,
            "high_days": 60,
            "excessive_days": 90,
            "safety_stock_multiplier": 1.5,
        }
        
        # 供应商数据库（模拟）
        self.suppliers: Dict[str, Supplier] = {}
        
        # 预警历史
        self.alerts: List[SupplyChainAlert] = []
        
        # 采购订单历史
        self.purchase_orders: List[PurchaseOrder] = []
    
    async def analyze_inventory(
        self,
        items: List[InventoryItem],
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        综合库存分析
        
        Returns:
            包含库存状态、预警、采购建议的综合报告
        """
        # 1. 计算每个SKU的库存状态
        inventory_status = []
        alerts = []
        
        for item in items:
            status = self._calculate_inventory_status(item)
            inventory_status.append(status)
            
            # 生成预警
            if status["status"] in [InventoryStatus.CRITICAL, InventoryStatus.LOW]:
                alert = self._generate_inventory_alert(item, status)
                alerts.append(alert)
        
        # 2. 生成采购建议
        purchase_recommendations = []
        for item in items:
            rec = self._generate_purchase_recommendation(item)
            if rec:
                purchase_recommendations.append(rec)
        
        # 3. LLM增强分析（可选）
        llm_insights = None
        if use_llm and self.llm:
            llm_insights = await self._get_llm_inventory_insights(
                items, inventory_status, alerts
            )
        
        # 4. 汇总报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_skus": len(items),
            "inventory_summary": self._summarize_inventory(inventory_status),
            "inventory_details": inventory_status,
            "alerts": [self._alert_to_dict(a) for a in alerts],
            "purchase_recommendations": purchase_recommendations,
            "llm_insights": llm_insights,
        }
        
        # 记录预警
        self.alerts.extend(alerts)
        
        return report
    
    def _calculate_inventory_status(self, item: InventoryItem) -> Dict:
        """计算单个SKU的库存状态"""
        available_qty = item.quantity - item.reserved
        total_qty = available_qty + item.in_transit
        
        # 计算库存周转天数
        if item.daily_sales_rate > 0:
            days_of_stock = available_qty / item.daily_sales_rate
        else:
            days_of_stock = float('inf') if available_qty > 0 else 0
        
        # 判断库存状态
        if days_of_stock < self.thresholds["critical_days"]:
            status = InventoryStatus.CRITICAL
        elif days_of_stock < self.thresholds["low_days"]:
            status = InventoryStatus.LOW
        elif days_of_stock < self.thresholds["high_days"]:
            status = InventoryStatus.NORMAL
        elif days_of_stock < self.thresholds["excessive_days"]:
            status = InventoryStatus.HIGH
        else:
            status = InventoryStatus.EXCESSIVE
        
        # 计算是否需要补货
        needs_restock = available_qty <= item.reorder_point
        
        # 计算建议补货量
        suggested_qty = 0
        if needs_restock or status in [InventoryStatus.CRITICAL, InventoryStatus.LOW]:
            # 目标库存 = 安全库存 + (周转天数 × 日销量)
            target_days = 30  # 目标30天库存
            target_qty = int(item.safety_stock + target_days * item.daily_sales_rate)
            suggested_qty = max(0, target_qty - total_qty)
        
        return {
            "sku": item.sku,
            "name": item.name,
            "available_qty": available_qty,
            "in_transit": item.in_transit,
            "total_qty": total_qty,
            "daily_sales_rate": item.daily_sales_rate,
            "days_of_stock": round(days_of_stock, 1) if days_of_stock != float('inf') else 999,
            "status": status.value,
            "needs_restock": needs_restock,
            "suggested_restock_qty": suggested_qty,
            "warehouse": item.warehouse,
        }
    
    def _generate_inventory_alert(
        self,
        item: InventoryItem,
        status: Dict
    ) -> SupplyChainAlert:
        """生成库存预警"""
        if status["status"] == InventoryStatus.CRITICAL.value:
            level = AlertLevel.URGENT
            alert_type = "critical_stock"
            message = f"SKU {item.sku} 库存危急，仅剩 {status['days_of_stock']} 天库存"
            recommendations = [
                f"立即下单采购，建议数量: {status['suggested_restock_qty']}",
                "联系供应商确认加急发货",
                "考虑临时下架或限购",
            ]
        elif status["status"] == InventoryStatus.LOW.value:
            level = AlertLevel.WARNING
            alert_type = "low_stock"
            message = f"SKU {item.sku} 库存偏低，剩余 {status['days_of_stock']} 天库存"
            recommendations = [
                f"近期需下单采购，建议数量: {status['suggested_restock_qty']}",
                "监控销售速度变化",
            ]
        else:
            level = AlertLevel.INFO
            alert_type = "restock_needed"
            message = f"SKU {item.sku} 需要补货"
            recommendations = [
                f"建议采购数量: {status['suggested_restock_qty']}",
            ]
        
        return SupplyChainAlert(
            alert_id=f"alert_{item.sku}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            level=level,
            type=alert_type,
            sku=item.sku,
            message=message,
            recommendations=recommendations,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=7),
        )
    
    def _generate_purchase_recommendation(
        self,
        item: InventoryItem
    ) -> Optional[Dict]:
        """生成采购建议"""
        status = self._calculate_inventory_status(item)
        
        if not status["needs_restock"] and status["status"] not in [
            InventoryStatus.CRITICAL.value,
            InventoryStatus.LOW.value
        ]:
            return None
        
        # 查找最佳供应商
        best_supplier = self._find_best_supplier(item.sku)
        
        qty = status["suggested_restock_qty"]
        if qty <= 0:
            return None
        
        # 调整到最小起订量
        if best_supplier:
            min_qty = best_supplier.min_order_qty
            qty = max(qty, min_qty)
            unit_price = best_supplier.price
            supplier_name = best_supplier.name
            lead_time = best_supplier.lead_time_days
        else:
            unit_price = 0
            supplier_name = "待分配"
            lead_time = 7
        
        total_amount = qty * unit_price
        expected_delivery = datetime.now() + timedelta(days=lead_time)
        
        # 判断优先级
        if status["status"] == InventoryStatus.CRITICAL.value:
            priority = "urgent"
        elif status["status"] == InventoryStatus.LOW.value:
            priority = "high"
        else:
            priority = "normal"
        
        return {
            "sku": item.sku,
            "name": item.name,
            "quantity": qty,
            "unit_price": unit_price,
            "total_amount": total_amount,
            "supplier": supplier_name,
            "expected_delivery": expected_delivery.isoformat(),
            "priority": priority,
            "reason": f"当前库存{status['days_of_stock']}天，建议补货",
        }
    
    def _find_best_supplier(self, sku: str) -> Optional[Supplier]:
        """查找最佳供应商"""
        # 筛选可供应该SKU的供应商
        candidates = [
            s for s in self.suppliers.values()
            if sku in s.products or not s.products
        ]
        
        if not candidates:
            return None
        
        # 综合评分：价格(40%) + 质量(30%) + 交付(30%)
        def score(s: Supplier) -> float:
            # 价格越低越好（反向归一化）
            prices = [x.price for x in candidates]
            max_price = max(prices) if prices else 1
            price_score = (max_price - s.price) / max_price if max_price > 0 else 0
            
            quality_score = s.quality_score
            delivery_score = s.delivery_score
            
            return price_score * 0.4 + quality_score * 0.3 + delivery_score * 0.3
        
        best = max(candidates, key=score)
        return best
    
    async def _get_llm_inventory_insights(
        self,
        items: List[InventoryItem],
        inventory_status: List[Dict],
        alerts: List[SupplyChainAlert]
    ) -> Optional[Dict]:
        """使用LLM获取库存洞察"""
        if not self.llm:
            return None
        
        # 构建提示词
        critical_items = [
            s for s in inventory_status
            if s["status"] == InventoryStatus.CRITICAL.value
        ]
        low_items = [
            s for s in inventory_status
            if s["status"] == InventoryStatus.LOW.value
        ]
        
        prompt = f"""
作为供应链管理专家，请分析以下库存数据并提供专业建议：

库存总览:
- SKU总数: {len(items)}
- 危急库存: {len(critical_items)} 个
- 低库存: {len(low_items)} 个

危急库存详情:
{self._format_critical_items(critical_items[:5])}

预警信息:
{self._format_alerts(alerts[:5])}

请提供：
1. 库存风险整体评估
2. 优先处理建议
3. 潜在供应链风险
4. 长期优化建议

以JSON格式返回结果。
"""
        
        try:
            response = await self.llm.complete(prompt, temperature=0.3)
            return {"llm_analysis": response}
        except Exception as e:
            logger.error(f"LLM库存分析失败: {e}")
            return None
    
    def _summarize_inventory(self, inventory_status: List[Dict]) -> Dict:
        """汇总库存统计"""
        status_counts = {}
        for status in inventory_status:
            s = status["status"]
            status_counts[s] = status_counts.get(s, 0) + 1
        
        total_value = sum(
            s["available_qty"] * s.get("unit_cost", 0)
            for s in inventory_status
        )
        
        return {
            "status_distribution": status_counts,
            "total_skus": len(inventory_status),
            "critical_count": status_counts.get(InventoryStatus.CRITICAL.value, 0),
            "low_count": status_counts.get(InventoryStatus.LOW.value, 0),
            "healthy_count": status_counts.get(InventoryStatus.NORMAL.value, 0),
            "excess_count": (
                status_counts.get(InventoryStatus.HIGH.value, 0) +
                status_counts.get(InventoryStatus.EXCESSIVE.value, 0)
            ),
        }
    
    def _alert_to_dict(self, alert: SupplyChainAlert) -> Dict:
        """转换预警为字典"""
        return {
            "alert_id": alert.alert_id,
            "level": alert.level.value,
            "type": alert.type,
            "sku": alert.sku,
            "message": alert.message,
            "recommendations": alert.recommendations,
            "created_at": alert.created_at.isoformat(),
        }
    
    def _format_critical_items(self, items: List[Dict]) -> str:
        """格式化危急库存列表"""
        if not items:
            return "无"
        lines = []
        for item in items[:5]:
            lines.append(
                f"- {item['sku']}: {item['days_of_stock']}天库存, "
                f"可用{item['available_qty']}件"
            )
        return "\n".join(lines)
    
    def _format_alerts(self, alerts: List[SupplyChainAlert]) -> str:
        """格式化预警列表"""
        if not alerts:
            return "无预警"
        lines = []
        for alert in alerts[:5]:
            lines.append(f"- [{alert.level.value}] {alert.message}")
        return "\n".join(lines)
    
    async def evaluate_supplier(
        self,
        supplier_id: str,
        performance_data: Optional[Dict] = None
    ) -> Dict:
        """评估供应商"""
        supplier = self.suppliers.get(supplier_id)
        if not supplier:
            return {"error": f"供应商 {supplier_id} 不存在"}
        
        # 计算综合评分
        quality_score = supplier.quality_score
        delivery_score = supplier.delivery_score
        price_score = self._calculate_price_score(supplier)
        
        overall_score = (
            quality_score * 0.35 +
            delivery_score * 0.35 +
            price_score * 0.30
        )
        
        # 确定等级
        if overall_score >= 0.85:
            grade = SupplierGrade.A
        elif overall_score >= 0.70:
            grade = SupplierGrade.B
        elif overall_score >= 0.55:
            grade = SupplierGrade.C
        else:
            grade = SupplierGrade.D
        
        # 生成改进建议
        improvements = []
        if quality_score < 0.7:
            improvements.append("质量问题频发，建议加强质检或寻找替代供应商")
        if delivery_score < 0.7:
            improvements.append("交付延迟严重，建议协商改善或增加备选供应商")
        if price_score < 0.5:
            improvements.append("价格竞争力不足，建议议价或寻找性价比更高的供应商")
        
        return {
            "supplier_id": supplier_id,
            "name": supplier.name,
            "overall_score": round(overall_score, 2),
            "grade": grade.value,
            "scores": {
                "quality": round(quality_score, 2),
                "delivery": round(delivery_score, 2),
                "price": round(price_score, 2),
            },
            "improvements": improvements,
        }
    
    def _calculate_price_score(self, supplier: Supplier) -> float:
        """计算价格竞争力得分"""
        # 简化实现：价格越低得分越高
        # 假设市场价格在 supplier.price 的 0.8-1.2 倍区间
        reference_price = supplier.price
        competitive_price = supplier.price * 0.85
        
        if supplier.price <= competitive_price:
            return 1.0
        elif supplier.price >= reference_price * 1.2:
            return 0.3
        else:
            # 线性插值
            return 0.3 + 0.7 * (1.2 * reference_price - supplier.price) / (0.35 * reference_price)
    
    def add_supplier(self, supplier: Supplier):
        """添加供应商"""
        self.suppliers[supplier.id] = supplier
    
    def get_active_alerts(self) -> List[Dict]:
        """获取活跃预警"""
        now = datetime.now()
        active = [
            self._alert_to_dict(a)
            for a in self.alerts
            if a.expires_at is None or a.expires_at > now
        ]
        return active
    
    def create_purchase_order(
        self,
        supplier_id: str,
        sku: str,
        quantity: int,
        unit_price: float,
        priority: str = "normal"
    ) -> PurchaseOrder:
        """创建采购订单"""
        supplier = self.suppliers.get(supplier_id)
        if not supplier:
            raise ValueError(f"供应商 {supplier_id} 不存在")
        
        order = PurchaseOrder(
            supplier_id=supplier_id,
            sku=sku,
            quantity=quantity,
            unit_price=unit_price,
            total_amount=quantity * unit_price,
            expected_delivery=datetime.now() + timedelta(days=supplier.lead_time_days),
            priority=priority,
            status="pending",
        )
        
        self.purchase_orders.append(order)
        logger.info(f"创建采购订单: {sku} x{quantity}, 供应商: {supplier.name}")
        
        return order


# 简化接口（向后兼容）
async def check_inventory_health(
    items: List[Dict],
    llm_client=None
) -> Dict:
    """
    简化的库存健康检查接口
    
    Args:
        items: 库存项列表 [{"sku": ..., "quantity": ..., "daily_sales_rate": ...}]
        llm_client: LLM客户端（可选）
    
    Returns:
        库存健康报告
    """
    inventory_items = [
        InventoryItem(
            sku=item["sku"],
            name=item.get("name", item["sku"]),
            quantity=item["quantity"],
            daily_sales_rate=item.get("daily_sales_rate", 0),
            safety_stock=item.get("safety_stock", 0),
            reorder_point=item.get("reorder_point", 0),
        )
        for item in items
    ]
    
    agent = SupplyChainAgent(llm_client=llm_client)
    return await agent.analyze_inventory(inventory_items, use_llm=bool(llm_client))
