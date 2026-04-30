"""
淘宝采集Agent - LLM驱动的智能商品数据采集
支持关键词搜索、店铺分析、价格监控、销量追踪
"""

import asyncio
import logging
import re
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import random

logger = logging.getLogger(__name__)


class TaobaoCategory(Enum):
    """淘宝类目"""
    FLOWERS = "鲜花"
    FLASH_SALE = "闪购"
    FRESH = "生鲜"
    HOME = "家居"
    DIGITAL = "数码"


@dataclass
class TaobaoProduct:
    """淘宝商品数据结构"""
    product_id: str
    title: str
    price: float
    original_price: Optional[float] = None
    sales: int = 0
    monthly_sales: int = 0
    rating: float = 0.0
    review_count: int = 0
    shop_name: str = ""
    shop_id: str = ""
    shop_rating: float = 0.0
    shop_level: str = ""
    location: str = ""
    shipping: str = ""
    tags: List[str] = field(default_factory=list)
    category: str = ""
    keywords: List[str] = field(default_factory=list)
    url: str = ""
    images: List[str] = field(default_factory=list)
    crawled_at: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ShopInfo:
    """店铺信息"""
    shop_id: str
    shop_name: str
    shop_rating: float
    shop_level: str
    product_count: int
    follower_count: int
    created_date: Optional[str] = None
    categories: List[str] = field(default_factory=list)
    top_products: List[str] = field(default_factory=list)


class TaobaoCollectorAgent:
    """LLM驱动的淘宝采集Agent"""
    
    def __init__(self, llm_client=None, config: Optional[Dict] = None):
        self.llm = llm_client
        self.config = config or {}
        
        # 采集配置
        self.max_products = self.config.get("max_products", 50)
        self.timeout = self.config.get("timeout", 30)
        self.retry_count = self.config.get("retry_count", 3)
        
        # 反爬策略
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101",
        ]
        
        # 缓存
        self.product_cache: Dict[str, TaobaoProduct] = {}
        self.shop_cache: Dict[str, ShopInfo] = {}
        
        # 统计
        self.stats = {
            "total_collected": 0,
            "success_rate": 0.0,
            "avg_response_time": 0.0,
        }
    
    async def collect(
        self,
        keywords: List[str],
        category: Optional[str] = None,
        use_llm: bool = True
    ) -> List[TaobaoProduct]:
        """
        主采集入口
        
        Args:
            keywords: 搜索关键词列表
            category: 商品类目
            use_llm: 是否使用LLM增强
            
        Returns:
            商品列表
        """
        all_products = []
        
        # 1. LLM扩展关键词
        if use_llm and self.llm:
            keywords = await self._expand_keywords_with_llm(keywords, category)
        
        # 2. 并行采集各关键词结果
        tasks = [
            self._search_keyword(kw, category)
            for kw in keywords[:10]  # 限制并发数
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_products.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"采集失败: {result}")
        
        # 3. 去重
        unique_products = self._deduplicate(all_products)
        
        # 4. LLM数据清洗
        if use_llm and self.llm:
            unique_products = await self._clean_with_llm(unique_products)
        
        # 5. 更新统计
        self.stats["total_collected"] += len(unique_products)
        
        logger.info(f"淘宝采集完成: {len(unique_products)} 条商品")
        return unique_products
    
    async def _expand_keywords_with_llm(
        self,
        keywords: List[str],
        category: Optional[str]
    ) -> List[str]:
        """使用LLM扩展关键词"""
        prompt = f"""
作为淘宝SEO专家，请扩展以下关键词：

原始关键词: {', '.join(keywords)}
类目: {category or '通用'}

要求：
1. 添加同义词（如"鲜花"→"花束"、"花卉"）
2. 添加长尾词（如"鲜花速递"、"同城送花"）
3. 添加场景词（如"生日"、"表白"、"开业"）
4. 去除无关词
5. 最多返回15个关键词

直接返回关键词列表，每行一个。
"""
        
        try:
            response = await self.llm.complete(prompt, temperature=0.7)
            
            # 解析响应
            expanded = []
            for line in response.strip().split('\n'):
                kw = line.strip()
                if kw and len(kw) < 20:
                    expanded.append(kw)
            
            # 合并去重
            all_kw = list(set(keywords + expanded))
            return all_kw[:15]
            
        except Exception as e:
            logger.error(f"LLM关键词扩展失败: {e}")
            return keywords
    
    async def _search_keyword(
        self,
        keyword: str,
        category: Optional[str]
    ) -> List[TaobaoProduct]:
        """搜索单个关键词"""
        # 模拟采集（实际应调用爬虫/API）
        products = []
        
        try:
            # 模拟延迟
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # 模拟数据
            for i in range(random.randint(5, 15)):
                product = self._generate_mock_product(keyword, category, i)
                products.append(product)
            
            logger.debug(f"关键词 '{keyword}' 采集到 {len(products)} 条")
            
        except Exception as e:
            logger.error(f"搜索关键词 '{keyword}' 失败: {e}")
        
        return products
    
    def _generate_mock_product(
        self,
        keyword: str,
        category: Optional[str],
        index: int
    ) -> TaobaoProduct:
        """生成模拟商品数据"""
        product_id = f"tb_{hashlib.md5(f'{keyword}{index}'.encode()).hexdigest()[:12]}"
        
        # 价格波动
        base_price = random.uniform(50, 500)
        price = round(base_price * random.uniform(0.7, 1.0), 2)
        original_price = round(base_price * random.uniform(1.0, 1.5), 2)
        
        # 销量
        sales = random.randint(10, 10000)
        monthly_sales = random.randint(50, 5000)
        
        # 评分
        rating = round(random.uniform(4.0, 5.0), 1)
        review_count = random.randint(10, 5000)
        
        # 店铺
        shop_names = [
            "花间小铺", "鲜花速递专营店", "花之语旗舰店",
            "春暖花开鲜花店", "花仙子花艺", "玫瑰恋人鲜花"
        ]
        shop_name = random.choice(shop_names)
        shop_id = f"shop_{hashlib.md5(shop_name.encode()).hexdigest()[:8]}"
        
        return TaobaoProduct(
            product_id=product_id,
            title=f"{keyword} 商品 {index+1} - 高品质热销",
            price=price,
            original_price=original_price if random.random() > 0.3 else None,
            sales=sales,
            monthly_sales=monthly_sales,
            rating=rating,
            review_count=review_count,
            shop_name=shop_name,
            shop_id=shop_id,
            shop_rating=round(random.uniform(4.5, 5.0), 1),
            shop_level=random.choice(["皇冠", "钻石", "金牌"]),
            location=random.choice(["上海", "北京", "广州", "深圳", "杭州"]),
            shipping="包邮" if random.random() > 0.3 else "运费10元",
            tags=[keyword, category or "鲜花"][:3],
            category=category or "鲜花",
            keywords=[keyword],
            url=f"https://item.taobao.com/item.htm?id={product_id}",
            images=[f"https://img.alicdn.com/{product_id}_{j}.jpg" for j in range(1, 4)],
            crawled_at=datetime.now().isoformat(),
        )
    
    def _deduplicate(self, products: List[TaobaoProduct]) -> List[TaobaoProduct]:
        """去重"""
        seen = set()
        unique = []
        
        for p in products:
            if p.product_id not in seen:
                seen.add(p.product_id)
                unique.append(p)
        
        return unique
    
    async def _clean_with_llm(
        self,
        products: List[TaobaoProduct]
    ) -> List[TaobaoProduct]:
        """使用LLM清洗数据"""
        if not products or len(products) < 5:
            return products
        
        # 批量清洗
        batch_size = 20
        cleaned = []
        
        for i in range(0, len(products), batch_size):
            batch = products[i:i+batch_size]
            
            # 提取关键信息
            product_summaries = [
                f"{p.product_id}: {p.title[:30]} (¥{p.price}, 销量{p.sales})"
                for p in batch
            ]
            
            prompt = f"""
作为数据清洗专家，请筛选以下商品：

{chr(10).join(product_summaries)}

要求：
1. 去除标题明显的广告/刷单商品
2. 保留价格合理的商品
3. 返回保留的product_id列表，每行一个

只返回ID，不要解释。
"""
            
            try:
                response = await self.llm.complete(prompt, temperature=0.3)
                valid_ids = set()
                
                for line in response.strip().split('\n'):
                    pid = line.strip()
                    if pid.startswith('tb_'):
                        valid_ids.add(pid)
                
                # 保留有效商品
                cleaned.extend([p for p in batch if p.product_id in valid_ids or not valid_ids])
                
            except Exception as e:
                logger.error(f"LLM清洗失败: {e}")
                cleaned.extend(batch)
        
        return cleaned
    
    async def get_shop_info(self, shop_id: str) -> Optional[ShopInfo]:
        """获取店铺信息"""
        if shop_id in self.shop_cache:
            return self.shop_cache[shop_id]
        
        # 模拟采集
        await asyncio.sleep(random.uniform(0.5, 1.0))
        
        shop_info = ShopInfo(
            shop_id=shop_id,
            shop_name=f"店铺_{shop_id}",
            shop_rating=round(random.uniform(4.5, 5.0), 1),
            shop_level=random.choice(["皇冠", "钻石", "金牌"]),
            product_count=random.randint(50, 500),
            follower_count=random.randint(1000, 50000),
        )
        
        self.shop_cache[shop_id] = shop_info
        return shop_info
    
    async def monitor_price(
        self,
        product_ids: List[str],
        interval_hours: int = 6
    ) -> Dict[str, List[Dict]]:
        """价格监控"""
        price_history = {}
        
        for pid in product_ids:
            # 模拟历史价格
            history = []
            base_price = random.uniform(50, 300)
            
            for i in range(7):
                date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                price = base_price * random.uniform(0.85, 1.15)
                history.append({
                    "date": date,
                    "price": round(price, 2),
                })
            
            price_history[pid] = history
        
        return price_history
    
    async def analyze_trend(
        self,
        keyword: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """趋势分析"""
        # 模拟采集多天数据
        trend_data = {
            "keyword": keyword,
            "period": f"最近{days}天",
            "avg_price": 0.0,
            "price_change": 0.0,
            "sales_trend": "stable",
            "competition": "medium",
        }
        
        # 模拟计算
        products = await self.collect([keyword], use_llm=False)
        
        if products:
            prices = [p.price for p in products]
            trend_data["avg_price"] = round(sum(prices) / len(prices), 2)
            trend_data["price_change"] = round(random.uniform(-10, 15), 1)
            trend_data["sales_trend"] = random.choice(["上升", "稳定", "下降"])
            trend_data["competition"] = random.choice(["低", "中", "高"])
        
        return trend_data
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            "cached_products": len(self.product_cache),
            "cached_shops": len(self.shop_cache),
        }


# 简化接口
async def collect_taobao(
    keywords: List[str],
    category: Optional[str] = None,
    llm_client=None
) -> List[Dict]:
    """简化的淘宝采集接口"""
    agent = TaobaoCollectorAgent(llm_client=llm_client)
    products = await agent.collect(keywords, category, use_llm=bool(llm_client))
    return [p.to_dict() for p in products]
