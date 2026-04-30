"""
定价决策Agent - LLM驱动的智能定价引擎
基于竞品分析、库存压力、市场趋势、历史数据生成动态定价方案
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class PricingStrategy(Enum):
    """定价策略枚举"""
    AGGRESSIVE = "aggressive"      # 激进定价（抢占市场）
    BALANCED = "balanced"          # 平衡定价（稳定利润）
    PREMIUM = "premium"           # 高端定价（品牌溢价）
    CLEARANCE = "clearance"       # 清仓定价（去库存）
    DYNAMIC = "dynamic"           # 动态定价（实时调整）


class MarketCondition(Enum):
    """市场环境枚举"""
    BOOM = "boom"                 # 繁荣期
    NORMAL = "normal"             # 正常期
    RECESSION = "recession"       # 衰退期
    PEAK_SEASON = "peak_season"   # 旺季
    OFF_SEASON = "off_season"     # 淡季


@dataclass
class CompetitorInfo:
    """竞品信息"""
    sku: str
    price: float
    platform: str
    rating: Optional[float] = None
    sales_volume: Optional[int] = None
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class PricingContext:
    """定价上下文"""
    sku: str
    current_price: float
    cost_price: Optional[float] = None
    inventory_level: str = "normal"  # low/normal/high/critical
    days_of_stock: Optional[float] = None
    historical_prices: List[Dict] = field(default_factory=list)
    competitors: List[CompetitorInfo] = field(default_factory=list)
    market_condition: MarketCondition = MarketCondition.NORMAL
    platform_fees: Dict[str, float] = field(default_factory=dict)
    target_margin: float = 0.15  # 目标利润率 15%


@dataclass
class PricingOption:
    """定价方案"""
    price: float
    strategy: PricingStrategy
    confidence: float
    expected_margin: float
    expected_sales_change: float
    reasoning: str
    risks: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)


class PricingAgent:
    """LLM驱动的智能定价Agent"""
    
    def __init__(self, llm_client=None, config: Optional[Dict] = None):
        self.llm = llm_client
        self.config = config or {}
        self.price_history: Dict[str, List[Dict]] = {}
        self.margin_thresholds = {
            "min_margin": 0.05,   # 最低利润率 5%
            "target_margin": 0.15,
            "premium_margin": 0.25,
        }
        
    async def generate_recommendations(
        self,
        context: PricingContext,
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        生成多维度定价建议
        
        Args:
            context: 定价上下文数据
            use_llm: 是否使用LLM增强决策
            
        Returns:
            包含多个定价方案和详细分析的结果
        """
        # 1. 基础数据分析
        analysis = await self._analyze_market(context)
        
        # 2. 生成多个定价方案
        options = []
        
        # 方案A: 基于竞品的定价
        comp_option = self._competitor_based_pricing(context, analysis)
        options.append(comp_option)
        
        # 方案B: 基于库存压力的定价
        inv_option = self._inventory_based_pricing(context, analysis)
        options.append(inv_option)
        
        # 方案C: 基于利润目标的定价
        margin_option = self._margin_based_pricing(context, analysis)
        options.append(margin_option)
        
        # 方案D: 动态市场定价
        dynamic_option = await self._dynamic_pricing(context, analysis, use_llm)
        if dynamic_option:
            options.append(dynamic_option)
        
        # 3. LLM增强决策（可选）
        if use_llm and self.llm:
            llm_insights = await self._get_llm_insights(context, analysis, options)
            if llm_insights:
                options = self._merge_llm_insights(options, llm_insights)
        
        # 4. 选择最佳推荐
        best_option = self._select_best_option(options, context)
        
        # 5. 记录价格历史
        self._record_price_history(context.sku, best_option)
        
        return {
            "sku": context.sku,
            "current_price": context.current_price,
            "recommended_price": best_option.price,
            "recommended_strategy": best_option.strategy.value,
            "confidence": best_option.confidence,
            "expected_margin": best_option.expected_margin,
            "expected_sales_change": best_option.expected_sales_change,
            "reasoning": best_option.reasoning,
            "risks": best_option.risks,
            "all_options": [
                {
                    "price": opt.price,
                    "strategy": opt.strategy.value,
                    "confidence": opt.confidence,
                    "reasoning": opt.reasoning,
                }
                for opt in options
            ],
            "market_analysis": analysis,
            "timestamp": datetime.now().isoformat(),
        }
    
    async def _analyze_market(self, context: PricingContext) -> Dict[str, Any]:
        """分析市场环境"""
        analysis = {
            "competitor_count": len(context.competitors),
            "price_range": {},
            "market_position": "unknown",
            "pressure_level": "normal",
        }
        
        if context.competitors:
            prices = [c.price for c in context.competitors]
            analysis["price_range"] = {
                "min": min(prices),
                "max": max(prices),
                "avg": sum(prices) / len(prices),
                "median": sorted(prices)[len(prices) // 2],
            }
            
            # 计算市场定位
            if context.current_price < analysis["price_range"]["min"]:
                analysis["market_position"] = "price_leader"
            elif context.current_price > analysis["price_range"]["max"]:
                analysis["market_position"] = "premium"
            else:
                analysis["market_position"] = "competitive"
        
        # 库存压力分析
        if context.days_of_stock is not None:
            if context.days_of_stock < 7:
                analysis["pressure_level"] = "critical"
            elif context.days_of_stock < 30:
                analysis["pressure_level"] = "high"
            elif context.days_of_stock > 90:
                analysis["pressure_level"] = "low"
        
        return analysis
    
    def _competitor_based_pricing(
        self, 
        context: PricingContext,
        analysis: Dict
    ) -> PricingOption:
        """基于竞品的定价策略"""
        if not context.competitors:
            return PricingOption(
                price=context.current_price,
                strategy=PricingStrategy.BALANCED,
                confidence=0.3,
                expected_margin=0.0,
                expected_sales_change=0.0,
                reasoning="无竞品数据，维持原价",
                risks=["缺乏市场参考数据"],
                conditions=["需要采集竞品价格信息"],
            )
        
        avg_price = analysis["price_range"]["avg"]
        min_price = analysis["price_range"]["min"]
        
        # 计算略低于市场均价的价格
        target_price = round(avg_price * 0.97, 2)
        
        # 计算预期利润率
        margin = self._calculate_margin(context, target_price)
        
        # 预期销量变化
        price_change_ratio = (target_price - context.current_price) / context.current_price
        expected_sales_change = -price_change_ratio * 1.5  # 价格弹性系数 1.5
        
        return PricingOption(
            price=target_price,
            strategy=PricingStrategy.BALANCED,
            confidence=0.75,
            expected_margin=margin,
            expected_sales_change=expected_sales_change,
            reasoning=f"基于{len(context.competitors)}个竞品的均价调整，略低于市场平均以获取竞争优势",
            risks=[
                "竞品可能跟进降价",
                "利润空间压缩",
            ],
            conditions=[
                "持续监控竞品价格变化",
                "确保库存充足",
            ],
        )
    
    def _inventory_based_pricing(
        self,
        context: PricingContext,
        analysis: Dict
    ) -> PricingOption:
        """基于库存压力的定价策略"""
        pressure = analysis["pressure_level"]
        
        if pressure == "critical":
            # 清仓定价
            discount = 0.85
            strategy = PricingStrategy.CLEARANCE
            confidence = 0.9
            reasoning = "库存危急，启动清仓定价快速回笼资金"
            risks = ["可能造成亏损", "影响品牌形象"]
        elif pressure == "high":
            # 激进定价
            discount = 0.92
            strategy = PricingStrategy.AGGRESSIVE
            confidence = 0.85
            reasoning = "库存偏高，降价促销提升周转"
            risks = ["利润率下降"]
        elif pressure == "low":
            # 维持或提价
            discount = 1.05
            strategy = PricingStrategy.PREMIUM
            confidence = 0.6
            reasoning = "库存充足，可尝试提价测试市场反应"
            risks = ["可能降低销量"]
        else:
            # 正常库存
            discount = 0.98
            strategy = PricingStrategy.BALANCED
            confidence = 0.7
            reasoning = "库存正常，维持稳健定价"
            risks = []
        
        target_price = round(context.current_price * discount, 2)
        margin = self._calculate_margin(context, target_price)
        
        return PricingOption(
            price=target_price,
            strategy=strategy,
            confidence=confidence,
            expected_margin=margin,
            expected_sales_change=0.0,
            reasoning=reasoning,
            risks=risks,
            conditions=[],
        )
    
    def _margin_based_pricing(
        self,
        context: PricingContext,
        analysis: Dict
    ) -> PricingOption:
        """基于利润目标的定价策略"""
        target_margin = context.target_margin
        min_margin = self.margin_thresholds["min_margin"]
        
        if context.cost_price:
            # 计算达到目标利润率的价格
            target_price = round(
                context.cost_price / (1 - target_margin - context.platform_fees.get("rate", 0.03)),
                2
            )
            min_price = round(
                context.cost_price / (1 - min_margin - context.platform_fees.get("rate", 0.03)),
                2
            )
            
            # 确保不低于最低利润率
            if target_price < min_price:
                target_price = min_price
                strategy = PricingStrategy.BALANCED
                reasoning = f"调整为最低可接受价格以保障{min_margin*100}%利润率"
            else:
                strategy = PricingStrategy.BALANCED
                reasoning = f"基于成本核算，目标利润率{target_margin*100}%"
            
            return PricingOption(
                price=target_price,
                strategy=strategy,
                confidence=0.8,
                expected_margin=target_margin,
                expected_sales_change=0.0,
                reasoning=reasoning,
                risks=["成本波动影响利润"],
                conditions=["需要准确的成本核算"],
            )
        else:
            # 无成本数据，基于当前价格估算
            return PricingOption(
                price=context.current_price,
                strategy=PricingStrategy.BALANCED,
                confidence=0.5,
                expected_margin=0.0,
                expected_sales_change=0.0,
                reasoning="缺少成本数据，无法计算利润导向定价",
                risks=["定价可能偏离合理区间"],
                conditions=["需要提供成本价格数据"],
            )
    
    async def _dynamic_pricing(
        self,
        context: PricingContext,
        analysis: Dict,
        use_llm: bool
    ) -> Optional[PricingOption]:
        """动态定价策略（结合实时市场变化）"""
        # 检查历史价格趋势
        history = context.historical_prices
        if not history or len(history) < 3:
            return None
        
        # 计算价格趋势
        recent_prices = [h["price"] for h in history[-7:]]  # 最近7次价格
        trend = "stable"
        if len(recent_prices) >= 3:
            if recent_prices[-1] > recent_prices[0]:
                trend = "rising"
            elif recent_prices[-1] < recent_prices[0]:
                trend = "falling"
        
        # 根据趋势调整价格
        if trend == "rising" and context.market_condition == MarketCondition.BOOM:
            adjustment = 1.03
            reasoning = "市场繁荣期，价格上升趋势，小幅提价"
        elif trend == "falling" and context.market_condition == MarketCondition.RECESSION:
            adjustment = 0.95
            reasoning = "市场衰退期，价格下降趋势，降价促销"
        else:
            adjustment = 1.0
            reasoning = "市场稳定，维持当前价格"
        
        target_price = round(context.current_price * adjustment, 2)
        margin = self._calculate_margin(context, target_price)
        
        return PricingOption(
            price=target_price,
            strategy=PricingStrategy.DYNAMIC,
            confidence=0.7,
            expected_margin=margin,
            expected_sales_change=0.0,
            reasoning=reasoning,
            risks=["趋势判断可能失误"],
            conditions=["需要持续监控市场动态"],
        )
    
    async def _get_llm_insights(
        self,
        context: PricingContext,
        analysis: Dict,
        options: List[PricingOption]
    ) -> Optional[Dict]:
        """使用LLM获取定价洞察"""
        if not self.llm:
            return None
        
        prompt = f"""
作为电商定价专家，请分析以下定价场景并提供专业建议：

商品SKU: {context.sku}
当前价格: ¥{context.current_price}
成本价格: ¥{context.cost_price if context.cost_price else '未知'}
库存状态: {context.inventory_level}
库存周转天数: {context.days_of_stock}

竞品分析:
- 竞品数量: {len(context.competitors)}
- 价格区间: ¥{analysis['price_range'].get('min', 'N/A')} - ¥{analysis['price_range'].get('max', 'N/A')}
- 市场均价: ¥{analysis['price_range'].get('avg', 'N/A')}

市场环境: {context.market_condition.value}

已生成的定价方案:
{self._format_options_for_llm(options)}

请提供：
1. 对各方案的专业评价
2. 最优定价建议（价格 + 策略）
3. 潜在风险提醒
4. 执行建议

以JSON格式返回结果。
"""
        
        try:
            response = await self.llm.complete(prompt, temperature=0.3)
            # 解析LLM响应（简化实现）
            return {"llm_analysis": response}
        except Exception as e:
            logger.error(f"LLM定价分析失败: {e}")
            return None
    
    def _merge_llm_insights(
        self,
        options: List[PricingOption],
        llm_insights: Dict
    ) -> List[PricingOption]:
        """融合LLM洞察到定价方案"""
        # 简化实现：保持原方案不变，仅增加LLM分析标记
        for opt in options:
            opt.conditions.append("LLM分析已完成")
        return options
    
    def _select_best_option(
        self,
        options: List[PricingOption],
        context: PricingContext
    ) -> PricingOption:
        """选择最优定价方案"""
        if not options:
            return PricingOption(
                price=context.current_price,
                strategy=PricingStrategy.BALANCED,
                confidence=0.5,
                expected_margin=0.0,
                expected_sales_change=0.0,
                reasoning="无可用方案，维持原价",
                risks=[],
                conditions=[],
            )
        
        # 综合评分：置信度 + 利润率 + 销量预期
        def score(opt: PricingOption) -> float:
            margin_score = max(0, opt.expected_margin) * 0.4
            confidence_score = opt.confidence * 0.4
            sales_score = max(0, opt.expected_sales_change) * 0.2
            return margin_score + confidence_score + sales_score
        
        best = max(options, key=score)
        return best
    
    def _calculate_margin(self, context: PricingContext, price: float) -> float:
        """计算利润率"""
        if not context.cost_price:
            return 0.0
        
        platform_fee_rate = context.platform_fees.get("rate", 0.03)
        actual_revenue = price * (1 - platform_fee_rate)
        margin = (actual_revenue - context.cost_price) / actual_revenue
        return round(margin, 4)
    
    def _format_options_for_llm(self, options: List[PricingOption]) -> str:
        """格式化方案列表供LLM分析"""
        lines = []
        for i, opt in enumerate(options, 1):
            lines.append(
                f"{i}. {opt.strategy.value}: ¥{opt.price} "
                f"(置信度: {opt.confidence}, 预期利润率: {opt.expected_margin*100:.1f}%)"
            )
        return "\n".join(lines)
    
    def _record_price_history(self, sku: str, option: PricingOption):
        """记录价格历史"""
        if sku not in self.price_history:
            self.price_history[sku] = []
        
        self.price_history[sku].append({
            "price": option.price,
            "strategy": option.strategy.value,
            "confidence": option.confidence,
            "timestamp": datetime.now().isoformat(),
        })
        
        # 只保留最近30条记录
        if len(self.price_history[sku]) > 30:
            self.price_history[sku] = self.price_history[sku][-30:]
    
    def get_price_history(self, sku: str) -> List[Dict]:
        """获取价格历史"""
        return self.price_history.get(sku, [])
    
    async def batch_price(
        self,
        items: List[PricingContext],
        use_llm: bool = True
    ) -> List[Dict]:
        """批量定价"""
        results = []
        for item in items:
            result = await self.generate_recommendations(item, use_llm)
            results.append(result)
        return results


# 向后兼容的简单接口
async def generate_pricing_recommendation(
    sku: str,
    current_price: float,
    competitor_prices: List[float],
    inventory_level: str = "normal",
    llm_client=None,
) -> Dict:
    """
    简化的定价建议接口（向后兼容）
    """
    context = PricingContext(
        sku=sku,
        current_price=current_price,
        inventory_level=inventory_level,
        competitors=[
            CompetitorInfo(sku=f"comp_{i}", price=p, platform="unknown")
            for i, p in enumerate(competitor_prices)
        ],
    )
    
    agent = PricingAgent(llm_client=llm_client)
    return await agent.generate_recommendations(context, use_llm=bool(llm_client))
