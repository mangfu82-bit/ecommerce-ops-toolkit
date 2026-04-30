"""
跨平台关联分析Agent - LLM驱动的深度数据融合
发现不同平台之间的数据关联模式、价格差异、销量对比
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class CorrelationType(Enum):
    """关联类型"""
    PRICE_ARBITRAGE = "price_arbitrage"      # 价格套利
    CROSS_PLATFORM_MATCH = "cross_platform"   # 跨平台匹配
    SEASONAL_PATTERN = "seasonal_pattern"     # 季节性模式
    TREND_CORRELATION = "trend_correlation"   # 趋势关联
    COMPETITOR_MAPPING = "competitor_mapping" # 竞品映射


class CorrelationStrength(Enum):
    """关联强度"""
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"


@dataclass
class CorrelationResult:
    """关联分析结果"""
    correlation_id: str
    correlation_type: CorrelationType
    strength: CorrelationStrength
    platforms: List[str]
    items: List[Dict]
    insight: str
    action_required: bool
    action_suggestion: str
    confidence: float
    metadata: Dict = field(default_factory=dict)


@dataclass
class PriceDiscrepancy:
    """价格差异"""
    product_name: str
    platform_a: str
    price_a: float
    platform_b: str
    price_b: float
    price_diff: float
    diff_percentage: float
    opportunity_score: float


@dataclass
class SalesTrend:
    """销量趋势"""
    platform: str
    product: str
    trend_direction: str  # up/down/stable
    growth_rate: float
    forecast: float
    confidence: float


class CorrelationAgent:
    """LLM驱动的跨平台关联分析Agent"""
    
    def __init__(self, llm_client=None, config: Optional[Dict] = None):
        self.llm = llm_client
        self.config = config or {}
        
        # 价格套利阈值
        self.arbitrage_threshold = 0.15  # 15%价差视为套利机会
        
        # 关联历史
        self.correlation_history: List[CorrelationResult] = []
    
    async def analyze_cross_platform(
        self,
        platform_data: Dict[str, List[Dict]],
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        跨平台综合分析
        
        Args:
            platform_data: 各平台数据 {"taobao": [...], "jd": [...], ...}
            use_llm: 是否使用LLM增强
            
        Returns:
            关联分析报告
        """
        correlations = []
        
        # 1. 价格套利分析
        price_correlations = await self._analyze_price_arbitrage(platform_data)
        correlations.extend(price_correlations)
        
        # 2. 跨平台商品匹配
        match_correlations = self._analyze_cross_platform_matches(platform_data)
        correlations.extend(match_correlations)
        
        # 3. 趋势关联分析
        trend_correlations = self._analyze_trend_correlations(platform_data)
        correlations.extend(trend_correlations)
        
        # 4. LLM深度洞察
        llm_insights = None
        if use_llm and self.llm:
            llm_insights = await self._get_llm_insights(platform_data, correlations)
        
        # 5. 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_correlations": len(correlations),
            "by_type": self._group_by_type(correlations),
            "high_priority": [
                {
                    "type": c.correlation_type.value,
                    "platforms": c.platforms,
                    "insight": c.insight,
                    "action": c.action_suggestion,
                }
                for c in correlations
                if c.action_required
            ],
            "correlations": [self._result_to_dict(c) for c in correlations],
            "llm_insights": llm_insights,
        }
        
        self.correlation_history.extend(correlations)
        
        return report
    
    async def _analyze_price_arbitrage(
        self,
        platform_data: Dict[str, List[Dict]]
    ) -> List[CorrelationResult]:
        """分析价格套利机会"""
        results = []
        
        # 提取所有平台的价格数据
        all_prices = defaultdict(list)
        for platform, items in platform_data.items():
            for item in items:
                name = item.get("title", item.get("name", ""))
                price = item.get("price", 0)
                if name and price > 0:
                    all_prices[name[:30]].append({
                        "platform": platform,
                        "price": float(price),
                        "item": item,
                    })
        
        # 查找价差
        for name, price_list in all_prices.items():
            if len(price_list) < 2:
                continue
            
            platforms = [p["platform"] for p in price_list]
            if len(set(platforms)) < 2:
                continue  # 需要跨平台
            
            prices = [p["price"] for p in price_list]
            min_price = min(prices)
            max_price = max(prices)
            
            if min_price == 0:
                continue
            
            diff_ratio = (max_price - min_price) / min_price
            
            if diff_ratio >= self.arbitrage_threshold:
                # 找到套利机会
                min_item = min(price_list, key=lambda x: x["price"])
                max_item = max(price_list, key=lambda x: x["price"])
                
                insight = (
                    f"发现价格套利机会：{name} 在 {max_item['platform']} "
                    f"售价 {max_item['price']} 元，而 {min_item['platform']} "
                    f"仅需 {min_item['price']} 元，差价 {diff_ratio*100:.1f}%"
                )
                
                results.append(CorrelationResult(
                    correlation_id=f"arb_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(name) % 10000}",
                    correlation_type=CorrelationType.PRICE_ARBITRAGE,
                    strength=CorrelationStrength.STRONG if diff_ratio > 0.25 else CorrelationStrength.MEDIUM,
                    platforms=[min_item["platform"], max_item["platform"]],
                    items=[min_item["item"], max_item["item"]],
                    insight=insight,
                    action_required=True,
                    action_suggestion=f"建议从{min_item['platform']}采购，在{max_item['platform']}销售",
                    confidence=0.85,
                    metadata={
                        "price_diff": max_price - min_price,
                        "diff_percentage": diff_ratio,
                    },
                ))
        
        return results
    
    def _analyze_cross_platform_matches(
        self,
        platform_data: Dict[str, List[Dict]]
    ) -> List[CorrelationResult]:
        """分析跨平台商品匹配"""
        results = []
        
        # 按关键词分组
        by_keyword = defaultdict(list)
        for platform, items in platform_data.items():
            for item in items:
                title = item.get("title", item.get("name", ""))
                # 提取关键词
                keywords = self._extract_keywords(title)
                for kw in keywords:
                    by_keyword[kw].append({
                        "platform": platform,
                        "item": item,
                    })
        
        # 找出跨平台匹配
        for keyword, items in by_keyword.items():
            platforms = set(i["platform"] for i in items)
            if len(platforms) >= 2:
                results.append(CorrelationResult(
                    correlation_id=f"match_{hash(keyword) % 10000}",
                    correlation_type=CorrelationType.CROSS_PLATFORM_MATCH,
                    strength=CorrelationStrength.MEDIUM,
                    platforms=list(platforms),
                    items=[i["item"] for i in items[:5]],
                    insight=f"关键词 '{keyword}' 在 {len(platforms)} 个平台有相关商品",
                    action_required=False,
                    action_suggestion="可对比各平台价格和销量数据",
                    confidence=0.75,
                    metadata={"keyword": keyword, "item_count": len(items)},
                ))
        
        return results[:10]  # 限制返回数量
    
    def _analyze_trend_correlations(
        self,
        platform_data: Dict[str, List[Dict]]
    ) -> List[CorrelationResult]:
        """分析趋势关联"""
        results = []
        
        # 按平台统计
        for platform, items in platform_data.items():
            sales_values = []
            for item in items:
                sales = item.get("sales", item.get("monthly_sales", 0))
                if sales:
                    sales_values.append(float(sales))
            
            if len(sales_values) >= 3:
                avg_sales = statistics.mean(sales_values)
                std_sales = statistics.stdev(sales_values) if len(sales_values) > 1 else 0
                
                # 简单的趋势判断
                if std_sales > avg_sales * 0.5:
                    insight = f"{platform} 平台销量波动较大，可能存在季节性或促销影响"
                    strength = CorrelationStrength.MEDIUM
                else:
                    insight = f"{platform} 平台销量稳定，平均 {avg_sales:.0f} 件/月"
                    strength = CorrelationStrength.WEAK
                
                results.append(CorrelationResult(
                    correlation_id=f"trend_{platform}",
                    correlation_type=CorrelationType.TREND_CORRELATION,
                    strength=strength,
                    platforms=[platform],
                    items=[],
                    insight=insight,
                    action_required=False,
                    action_suggestion="建议深入分析销量变化原因",
                    confidence=0.65,
                    metadata={"avg_sales": avg_sales, "std_sales": std_sales},
                ))
        
        return results
    
    async def _get_llm_insights(
        self,
        platform_data: Dict[str, List[Dict]],
        correlations: List[CorrelationResult]
    ) -> Optional[Dict]:
        """使用LLM获取深度洞察"""
        if not self.llm:
            return None
        
        # 构建摘要
        summary_lines = []
        for platform, items in platform_data.items():
            summary_lines.append(f"- {platform}: {len(items)} 条数据")
        
        correlation_summary = []
        for c in correlations[:5]:
            correlation_summary.append(f"- {c.correlation_type.value}: {c.insight}")
        
        prompt = f"""
作为电商数据分析专家，请分析以下跨平台数据：

平台数据概览:
{chr(10).join(summary_lines)}

已发现的关联:
{chr(10).join(correlation_summary) if correlation_summary else '暂无'}

请提供：
1. 整体市场洞察
2. 潜在机会识别
3. 风险提示
4. 行动建议

以JSON格式返回。
"""
        
        try:
            response = await self.llm.complete(prompt, temperature=0.5)
            return {"llm_analysis": response}
        except Exception as e:
            logger.error(f"LLM关联分析失败: {e}")
            return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        # 简化实现：按空格和常见分隔符切分
        keywords = []
        
        # 移除标点
        import re
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
        
        # 分词（简化）
        words = text.split()
        
        # 过滤短词
        keywords = [w for w in words if len(w) >= 2]
        
        return keywords[:5]
    
    def _group_by_type(
        self,
        correlations: List[CorrelationResult]
    ) -> Dict[str, int]:
        """按类型分组统计"""
        groups = defaultdict(int)
        for c in correlations:
            groups[c.correlation_type.value] += 1
        return dict(groups)
    
    def _result_to_dict(self, result: CorrelationResult) -> Dict:
        """转换结果为字典"""
        return {
            "correlation_id": result.correlation_id,
            "type": result.correlation_type.value,
            "strength": result.strength.value,
            "platforms": result.platforms,
            "insight": result.insight,
            "action_required": result.action_required,
            "action_suggestion": result.action_suggestion,
            "confidence": result.confidence,
        }
    
    async def find_price_discrepancies(
        self,
        platform_data: Dict[str, List[Dict]]
    ) -> List[PriceDiscrepancy]:
        """查找价格差异"""
        discrepancies = []
        
        # 提取价格
        by_product = defaultdict(list)
        for platform, items in platform_data.items():
            for item in items:
                name = item.get("title", item.get("name", ""))[:30]
                price = item.get("price", 0)
                if name and price > 0:
                    by_product[name].append({
                        "platform": platform,
                        "price": float(price),
                    })
        
        # 比较价差
        for name, prices in by_product.items():
            if len(prices) < 2:
                continue
            
            platforms = [p["platform"] for p in prices]
            if len(set(platforms)) < 2:
                continue
            
            price_values = [p["price"] for p in prices]
            min_idx = price_values.index(min(price_values))
            max_idx = price_values.index(max(price_values))
            
            min_p = prices[min_idx]
            max_p = prices[max_idx]
            
            diff = max_p["price"] - min_p["price"]
            diff_pct = diff / min_p["price"] if min_p["price"] > 0 else 0
            
            opportunity_score = min(diff_pct / self.arbitrage_threshold, 1.0)
            
            discrepancies.append(PriceDiscrepancy(
                product_name=name,
                platform_a=min_p["platform"],
                price_a=min_p["price"],
                platform_b=max_p["platform"],
                price_b=max_p["price"],
                price_diff=diff,
                diff_percentage=diff_pct,
                opportunity_score=opportunity_score,
            ))
        
        # 按机会得分排序
        discrepancies.sort(key=lambda x: x.opportunity_score, reverse=True)
        
        return discrepancies[:20]
    
    def get_correlation_history(
        self,
        limit: int = 50
    ) -> List[Dict]:
        """获取关联历史"""
        return [
            self._result_to_dict(c)
            for c in self.correlation_history[-limit:]
        ]


# 简化接口
async def analyze_correlations(
    platform_data: Dict[str, List[Dict]],
    llm_client=None
) -> Dict:
    """简化的关联分析接口"""
    agent = CorrelationAgent(llm_client=llm_client)
    return await agent.analyze_cross_platform(platform_data, use_llm=bool(llm_client))
