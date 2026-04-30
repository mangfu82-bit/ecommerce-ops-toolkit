"""
市场情报Agent - LLM驱动的市场分析与洞察
竞争态势、市场趋势、机会识别、风险评估
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class MarketTrend(Enum):
    """市场趋势"""
    GROWING = "growing"       # 增长
    STABLE = "stable"         # 稳定
    DECLINING = "declining"   # 衰退
    VOLATILE = "volatile"     # 波动


class OpportunityType(Enum):
    """机会类型"""
    PRICE_GAP = "price_gap"           # 价格洼地
    EMERGING_DEMAND = "emerging"       # 新兴需求
    UNDERSERVED = "underserved"        # 供给不足
    SEASONAL_PEAK = "seasonal_peak"    # 季节性高峰
    COMPETITOR_WEAKNESS = "comp_weak"  # 竞品弱势


class RiskLevel(Enum):
    """风险等级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class CompetitorInfo:
    """竞品信息"""
    name: str
    platform: str
    market_share: float = 0.0
    avg_price: float = 0.0
    rating: float = 0.0
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)


@dataclass
class MarketOpportunity:
    """市场机会"""
    opportunity_id: str
    type: OpportunityType
    description: str
    potential_value: float
    difficulty: str  # easy/medium/hard
    time_to_capture: str
    requirements: List[str]
    confidence: float


@dataclass
class MarketRisk:
    """市场风险"""
    risk_id: str
    level: RiskLevel
    category: str
    description: str
    impact: str
    mitigation: str


class MarketIntelligenceAgent:
    """LLM驱动的市场情报Agent"""
    
    def __init__(self, llm_client=None, config: Optional[Dict] = None):
        self.llm = llm_client
        self.config = config or {}
        
        # 竞品数据库
        self.competitors: Dict[str, CompetitorInfo] = {}
        
        # 市场历史数据
        self.market_history: List[Dict] = []
        
        # 分析配置
        self.analysis_config = {
            "trend_window_days": 30,
            "min_sample_size": 10,
            "growth_threshold": 0.15,
            "decline_threshold": -0.10,
        }
    
    async def analyze_market(
        self,
        category: str,
        platform_data: Dict[str, List[Dict]],
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        综合市场分析
        
        Args:
            category: 商品类目
            platform_data: 各平台数据
            use_llm: 是否使用LLM
            
        Returns:
            市场分析报告
        """
        # 1. 竞争态势分析
        competition = self._analyze_competition(platform_data)
        
        # 2. 市场趋势分析
        trend = self._analyze_trend(platform_data)
        
        # 3. 机会识别
        opportunities = self._identify_opportunities(platform_data, competition)
        
        # 4. 风险评估
        risks = self._assess_risks(platform_data, competition)
        
        # 5. LLM深度洞察
        llm_insights = None
        if use_llm and self.llm:
            llm_insights = await self._get_llm_market_insights(
                category, platform_data, competition, opportunities, risks
            )
        
        # 6. 生成报告
        report = {
            "category": category,
            "timestamp": datetime.now().isoformat(),
            "market_trend": trend,
            "competition": {
                "competitor_count": len(competition),
                "top_competitors": [
                    {
                        "name": c.name,
                        "platform": c.platform,
                        "market_share": c.market_share,
                    }
                    for c in sorted(competition, key=lambda x: x.market_share, reverse=True)[:5]
                ],
            },
            "opportunities": [
                {
                    "type": o.type.value,
                    "description": o.description,
                    "potential_value": o.potential_value,
                    "difficulty": o.difficulty,
                }
                for o in opportunities
            ],
            "risks": [
                {
                    "level": r.level.value,
                    "category": r.category,
                    "description": r.description,
                }
                for r in risks
            ],
            "llm_insights": llm_insights,
            "recommendations": self._generate_recommendations(opportunities, risks),
        }
        
        return report
    
    def _analyze_competition(
        self,
        platform_data: Dict[str, List[Dict]]
    ) -> List[CompetitorInfo]:
        """分析竞争态势"""
        competitors = []
        
        for platform, items in platform_data.items():
            # 统计平台数据
            total_sales = 0
            total_rating = 0
            price_list = []
            seller_counts = defaultdict(int)
            
            for item in items:
                sales = item.get("sales", item.get("monthly_sales", 0))
                if sales:
                    total_sales += float(sales)
                
                rating = item.get("rating", item.get("score", 0))
                if rating:
                    total_rating += float(rating)
                
                price = item.get("price", 0)
                if price:
                    price_list.append(float(price))
                
                seller = item.get("seller", item.get("shop_name", "unknown"))
                seller_counts[seller] += 1
            
            # 计算市场集中度
            if seller_counts:
                top_seller_sales = max(seller_counts.values())
                market_concentration = top_seller_sales / len(items) if items else 0
            else:
                market_concentration = 0
            
            avg_price = statistics.mean(price_list) if price_list else 0
            avg_rating = total_rating / len(items) if items else 0
            
            # 识别主要竞品
            top_sellers = sorted(seller_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            
            for seller, count in top_sellers:
                market_share = count / len(items) if items else 0
                competitors.append(CompetitorInfo(
                    name=seller,
                    platform=platform,
                    market_share=market_share,
                    avg_price=avg_price,
                    rating=avg_rating,
                    strengths=["市场占有率高"] if market_share > 0.2 else [],
                    weaknesses=[],
                ))
        
        return competitors
    
    def _analyze_trend(
        self,
        platform_data: Dict[str, List[Dict]]
    ) -> Dict[str, Any]:
        """分析市场趋势"""
        # 简化实现：基于销量数据分析
        all_sales = []
        price_trends = []
        
        for platform, items in platform_data.items():
            for item in items:
                sales = item.get("sales", item.get("monthly_sales", 0))
                if sales:
                    all_sales.append(float(sales))
        
        if not all_sales:
            return {
                "trend": MarketTrend.STABLE.value,
                "confidence": 0.3,
                "description": "数据不足，无法判断趋势",
            }
        
        # 计算趋势
        if len(all_sales) >= 10:
            # 分段比较
            mid = len(all_sales) // 2
            first_half = all_sales[:mid]
            second_half = all_sales[mid:]
            
            avg_first = statistics.mean(first_half)
            avg_second = statistics.mean(second_half)
            
            change_rate = (avg_second - avg_first) / avg_first if avg_first > 0 else 0
            
            if change_rate > self.analysis_config["growth_threshold"]:
                trend = MarketTrend.GROWING
                description = f"市场处于增长期，销量增长 {change_rate*100:.1f}%"
            elif change_rate < self.analysis_config["decline_threshold"]:
                trend = MarketTrend.DECLINING
                description = f"市场处于衰退期，销量下降 {abs(change_rate)*100:.1f}%"
            elif abs(change_rate) < 0.05:
                trend = MarketTrend.STABLE
                description = "市场稳定，无明显趋势"
            else:
                trend = MarketTrend.VOLATILE
                description = "市场波动较大，需密切关注"
            
            confidence = 0.7
        else:
            trend = MarketTrend.STABLE
            description = "样本量不足，趋势判断置信度较低"
            confidence = 0.4
        
        return {
            "trend": trend.value,
            "confidence": confidence,
            "description": description,
            "sample_size": len(all_sales),
        }
    
    def _identify_opportunities(
        self,
        platform_data: Dict[str, List[Dict]],
        competition: List[CompetitorInfo]
    ) -> List[MarketOpportunity]:
        """识别市场机会"""
        opportunities = []
        
        # 1. 价格洼地机会
        prices_by_platform = {}
        for platform, items in platform_data.items():
            prices = [item.get("price", 0) for item in items if item.get("price", 0) > 0]
            if prices:
                prices_by_platform[platform] = {
                    "avg": statistics.mean(prices),
                    "min": min(prices),
                    "max": max(prices),
                }
        
        if len(prices_by_platform) >= 2:
            # 找价格最低的平台
            min_platform = min(prices_by_platform.items(), key=lambda x: x[1]["avg"])
            max_platform = max(prices_by_platform.items(), key=lambda x: x[1]["avg"])
            
            price_gap = (max_platform[1]["avg"] - min_platform[1]["avg"]) / min_platform[1]["avg"]
            
            if price_gap > 0.2:
                opportunities.append(MarketOpportunity(
                    opportunity_id=f"price_gap_{datetime.now().strftime('%Y%m%d')}",
                    type=OpportunityType.PRICE_GAP,
                    description=f"{min_platform[0]}平台价格洼地，比{max_platform[0]}低{price_gap*100:.1f}%",
                    potential_value=price_gap * 10000,  # 估算
                    difficulty="medium",
                    time_to_capture="1-2周",
                    requirements=["资金准备", "渠道对接"],
                    confidence=0.8,
                ))
        
        # 2. 供给不足机会
        for platform, items in platform_data.items():
            # 统计卖家数量
            sellers = set(item.get("seller", item.get("shop_name", "")) for item in items)
            if len(sellers) < 5 and len(items) > 50:
                opportunities.append(MarketOpportunity(
                    opportunity_id=f"underserved_{platform}",
                    type=OpportunityType.UNDERSERVED,
                    description=f"{platform}平台卖家数量少({len(sellers)}家)，供给可能不足",
                    potential_value=5000,
                    difficulty="easy",
                    time_to_capture="即时",
                    requirements=["入驻资质"],
                    confidence=0.7,
                ))
        
        # 3. 竞品弱势机会
        for comp in competition:
            if comp.rating < 3.5 and comp.market_share > 0.1:
                opportunities.append(MarketOpportunity(
                    opportunity_id=f"comp_weak_{comp.name}",
                    type=OpportunityType.COMPETITOR_WEAKNESS,
                    description=f"竞品{comp.name}评分较低({comp.rating})，有机会抢占份额",
                    potential_value=comp.market_share * 10000,
                    difficulty="medium",
                    time_to_capture="1-3月",
                    requirements=["提升产品/服务质量"],
                    confidence=0.65,
                ))
        
        return opportunities
    
    def _assess_risks(
        self,
        platform_data: Dict[str, List[Dict]],
        competition: List[CompetitorInfo]
    ) -> List[MarketRisk]:
        """评估市场风险"""
        risks = []
        
        # 1. 竞争风险
        top_competitor_share = max([c.market_share for c in competition], default=0)
        if top_competitor_share > 0.3:
            risks.append(MarketRisk(
                risk_id="competition_concentrated",
                level=RiskLevel.HIGH,
                category="competition",
                description=f"市场集中度高，头部竞品市占率{top_competitor_share*100:.1f}%",
                impact="新进入者获取份额难度大",
                mitigation="差异化定位或细分市场切入",
            ))
        
        # 2. 价格战风险
        all_prices = []
        for platform, items in platform_data.items():
            all_prices.extend([item.get("price", 0) for item in items if item.get("price", 0) > 0])
        
        if all_prices:
            price_std = statistics.stdev(all_prices) if len(all_prices) > 1 else 0
            price_mean = statistics.mean(all_prices)
            
            if price_mean > 0 and price_std / price_mean > 0.3:
                risks.append(MarketRisk(
                    risk_id="price_war",
                    level=RiskLevel.MEDIUM,
                    category="pricing",
                    description="价格离散度大，可能存在价格战",
                    impact="利润空间被压缩",
                    mitigation="避免纯价格竞争，加强价值塑造",
                ))
        
        # 3. 供应链风险
        total_items = sum(len(items) for items in platform_data.values())
        unique_sellers = set()
        for platform, items in platform_data.items():
            for item in items:
                seller = item.get("seller", item.get("shop_name", ""))
                if seller:
                    unique_sellers.add(seller)
        
        if len(unique_sellers) < 10 and total_items > 100:
            risks.append(MarketRisk(
                risk_id="supply_chain",
                level=RiskLevel.LOW,
                category="supply",
                description="供应商集中，供应链风险",
                impact="断供风险",
                mitigation="建立备选供应商",
            ))
        
        return risks
    
    async def _get_llm_market_insights(
        self,
        category: str,
        platform_data: Dict[str, List[Dict]],
        competition: List[CompetitorInfo],
        opportunities: List[MarketOpportunity],
        risks: List[MarketRisk]
    ) -> Optional[Dict]:
        """使用LLM获取市场洞察"""
        if not self.llm:
            return None
        
        # 构建摘要
        platform_summary = [
            f"- {p}: {len(items)}条数据"
            for p, items in platform_data.items()
        ]
        
        opp_summary = [
            f"- {o.type.value}: {o.description}"
            for o in opportunities[:3]
        ]
        
        risk_summary = [
            f"- [{r.level.value}] {r.description}"
            for r in risks
        ]
        
        prompt = f"""
作为市场分析专家，请分析以下{category}市场：

平台数据:
{chr(10).join(platform_summary)}

竞争态势:
- 竞品数量: {len(competition)}

机会:
{chr(10).join(opp_summary) if opp_summary else '暂无'}

风险:
{chr(10).join(risk_summary) if risk_summary else '暂无'}

请提供：
1. 市场整体评估
2. 竞争策略建议
3. 潜在风险预警
4. 优先行动项

以JSON格式返回。
"""
        
        try:
            response = await self.llm.complete(prompt, temperature=0.5)
            return {"llm_analysis": response}
        except Exception as e:
            logger.error(f"LLM市场洞察失败: {e}")
            return None
    
    def _generate_recommendations(
        self,
        opportunities: List[MarketOpportunity],
        risks: List[MarketRisk]
    ) -> List[str]:
        """生成行动建议"""
        recommendations = []
        
        # 基于机会生成建议
        for opp in opportunities[:3]:
            if opp.type == OpportunityType.PRICE_GAP:
                recommendations.append(f"关注跨平台套利: {opp.description}")
            elif opp.type == OpportunityType.UNDERSERVED:
                recommendations.append(f"考虑进入供给不足的市场")
            elif opp.type == OpportunityType.COMPETITOR_WEAKNESS:
                recommendations.append(f"针对弱势竞品制定竞争策略")
        
        # 基于风险生成建议
        for risk in risks:
            if risk.level == RiskLevel.HIGH:
                recommendations.append(f"【紧急】应对{risk.category}风险: {risk.mitigation}")
        
        if not recommendations:
            recommendations.append("市场态势平稳，建议持续监控")
        
        return recommendations
    
    def track_competitor(
        self,
        competitor_name: str,
        platform: str,
        data: Dict
    ):
        """跟踪竞品"""
        key = f"{platform}_{competitor_name}"
        self.competitors[key] = CompetitorInfo(
            name=competitor_name,
            platform=platform,
            market_share=data.get("market_share", 0),
            avg_price=data.get("avg_price", 0),
            rating=data.get("rating", 0),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
        )
        logger.info(f"已跟踪竞品: {competitor_name} @ {platform}")
    
    def get_market_summary(self) -> Dict:
        """获取市场摘要"""
        return {
            "tracked_competitors": len(self.competitors),
            "analysis_history": len(self.market_history),
            "last_updated": datetime.now().isoformat(),
        }


# 简化接口
async def analyze_market_intelligence(
    category: str,
    platform_data: Dict[str, List[Dict]],
    llm_client=None
) -> Dict:
    """简化的市场情报分析接口"""
    agent = MarketIntelligenceAgent(llm_client=llm_client)
    return await agent.analyze_market(category, platform_data, use_llm=bool(llm_client))
