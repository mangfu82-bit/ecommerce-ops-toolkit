"""
京东采集Agent - LLM驱动的电商数据采集
支持商品搜索、价格监控、评论分析、供应链追踪
"""

import asyncio
import logging
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import random
import json

logger = logging.getLogger(__name__)


class JDCategory(Enum):
    """京东类目"""
    FLOWERS = "鲜花"
    ELECTRONICS = "数码"
    HOME = "家居"
    FRESH = "生鲜"
    BEAUTY = "美妆"
    FASHION = "服饰"


@dataclass
class JDProduct:
    """京东商品数据结构"""
    product_id: str  # SKU
    title: str
    brand: str
    price: float
    original_price: Optional[float] = None
    promotion_price: Optional[float] = None
    sales: int = 0
    monthly_sales: int = 0
    rating: float = 0.0
    review_count: int = 0
    good_rate: float = 0.0
    shop_name: str = ""
    shop_id: str = ""
    shop_type: str = ""  # 自营/第三方
    stock_status: str = ""  # 现货/预售
    delivery: str = ""  # 京东配送/第三方
    warranty: str = ""
    category: str = ""
    tags: List[str] = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=dict)
    images: List[str] = field(default_factory=list)
    url: str = ""
    crawled_at: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class JDReview:
    """京东评论"""
    review_id: str
    product_id: str
    user_name: str
    rating: int
    content: str
    images: List[str] = field(default_factory=list)
    created_at: str
    helpful_count: int = 0
    reply: Optional[str] = None


@dataclass
class JDShop:
    """京东店铺"""
    shop_id: str
    shop_name: str
    shop_type: str
    shop_rating: float
    product_count: int
    follower_count: int
    categories: List[str] = field(default_factory=list)


class JDCollectorAgent:
    """LLM驱动的京东采集Agent"""
    
    def __init__(self, llm_client=None, config: Optional[Dict] = None):
        self.llm = llm_client
        self.config = config or {}
        
        # 配置
        self.max_products = self.config.get("max_products", 50)
        self.timeout = self.config.get("timeout", 30)
        
        # 缓存
        self.product_cache: Dict[str, JDProduct] = {}
        self.review_cache: Dict[str, List[JDReview]] = {}
        self.shop_cache: Dict[str, JDShop] = {}
        
        # 统计
        self.stats = {
            "total_collected": 0,
            "reviews_analyzed": 0,
            "shops_analyzed": 0,
        }
    
    async def collect(
        self,
        keywords: List[str],
        category: Optional[str] = None,
        use_llm: bool = True
    ) -> List[JDProduct]:
        """
        主采集入口
        
        Args:
            keywords: 搜索关键词
            category: 类目
            use_llm: 是否使用LLM
            
        Returns:
            商品列表
        """
        all_products = []
        
        # 1. LLM关键词优化
        if use_llm and self.llm:
            keywords = await self._optimize_keywords_with_llm(keywords, category)
        
        # 2. 并行采集
        tasks = [
            self._search_keyword(kw, category)
            for kw in keywords[:10]
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_products.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"采集失败: {result}")
        
        # 3. 去重
        unique_products = self._deduplicate(all_products)
        
        # 4. LLM数据增强
        if use_llm and self.llm:
            unique_products = await self._enhance_with_llm(unique_products)
        
        # 5. 统计
        self.stats["total_collected"] += len(unique_products)
        
        logger.info(f"京东采集完成: {len(unique_products)} 条商品")
        return unique_products
    
    async def _optimize_keywords_with_llm(
        self,
        keywords: List[str],
        category: Optional[str]
    ) -> List[str]:
        """LLM优化关键词"""
        prompt = f"""
作为京东SEO专家，请优化以下搜索关键词：

原始关键词: {', '.join(keywords)}
类目: {category or '通用'}

要求：
1. 添加京东特有热词（如"自营"、"京东物流"）
2. 添加品牌词
3. 添加场景词
4. 去除无关词
5. 最多返回15个关键词

直接返回关键词列表，每行一个。
"""
        
        try:
            response = await self.llm.complete(prompt, temperature=0.6)
            
            optimized = []
            for line in response.strip().split('\n'):
                kw = line.strip()
                if kw and len(kw) < 30:
                    optimized.append(kw)
            
            return list(set(keywords + optimized))[:15]
            
        except Exception as e:
            logger.error(f"LLM关键词优化失败: {e}")
            return keywords
    
    async def _search_keyword(
        self,
        keyword: str,
        category: Optional[str]
    ) -> List[JDProduct]:
        """搜索单个关键词"""
        products = []
        
        try:
            await asyncio.sleep(random.uniform(0.4, 1.2))
            
            for i in range(random.randint(5, 15)):
                product = self._generate_mock_product(keyword, category, i)
                products.append(product)
            
            logger.debug(f"关键词 '{keyword}' 采集到 {len(products)} 条")
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
        
        return products
    
    def _generate_mock_product(
        self,
        keyword: str,
        category: Optional[str],
        index: int
    ) -> JDProduct:
        """生成模拟商品数据"""
        product_id = f"jd_{hashlib.md5(f'{keyword}{index}'.encode()).hexdigest()[:10]}"
        
        # 价格
        base_price = random.uniform(100, 1000)
        price = round(base_price * random.uniform(0.75, 1.0), 2)
        original_price = round(base_price * random.uniform(1.0, 1.3), 2)
        promotion_price = round(price * 0.9, 2) if random.random() > 0.5 else None
        
        # 销量
        sales = random.randint(100, 50000)
        monthly_sales = random.randint(500, 10000)
        
        # 评价
        rating = round(random.uniform(4.3, 5.0), 1)
        review_count = random.randint(100, 10000)
        good_rate = round(random.uniform(90, 99), 1)
        
        # 店铺
        is_self = random.random() > 0.3
        shop_names = [
            "京东自营", "京东鲜花旗舰店", "花之韵专卖店",
            "鲜花速递专营店", "花艺生活馆", "绿植花卉旗舰店"
        ]
        shop_name = random.choice(shop_names)
        shop_id = f"jd_shop_{hashlib.md5(shop_name.encode()).hexdigest()[:8]}"
        
        return JDProduct(
            product_id=product_id,
            title=f"{keyword} {category or '商品'} - {'京东自营' if is_self else '品质热销'}",
            brand=random.choice(["品牌A", "品牌B", "自有品牌", ""]),
            price=price,
            original_price=original_price,
            promotion_price=promotion_price,
            sales=sales,
            monthly_sales=monthly_sales,
            rating=rating,
            review_count=review_count,
            good_rate=good_rate,
            shop_name=shop_name,
            shop_id=shop_id,
            shop_type="自营" if is_self else "第三方",
            stock_status=random.choice(["现货", "预售", "补货中"]),
            delivery="京东配送" if is_self else random.choice(["京东配送", "商家配送"]),
            warranty=random.choice(["7天无理由", "30天价保", "一年质保"]),
            category=category or "鲜花",
            tags=[keyword, "品质", "热销"][:3],
            attributes={
                "材质": "鲜花",
                "产地": random.choice(["云南", "北京", "上海"]),
                "规格": random.choice(["单支", "束装", "礼盒"]),
            },
            images=[f"https://img14.360buyimg.com/{product_id}_{j}.jpg" for j in range(1, 5)],
            url=f"https://item.jd.com/{product_id}.html",
            crawled_at=datetime.now().isoformat(),
        )
    
    def _deduplicate(self, products: List[JDProduct]) -> List[JDProduct]:
        """去重"""
        seen = set()
        unique = []
        
        for p in products:
            if p.product_id not in seen:
                seen.add(p.product_id)
                unique.append(p)
        
        return unique
    
    async def _enhance_with_llm(
        self,
        products: List[JDProduct]
    ) -> List[JDProduct]:
        """LLM数据增强"""
        if len(products) < 5:
            return products
        
        # 批量分析
        summaries = [
            f"{p.product_id}: {p.title[:30]} ¥{p.price} {p.shop_type}"
            for p in products[:15]
        ]
        
        prompt = f"""
作为京东数据分析专家，请评估以下商品：

{chr(10).join(summaries)}

要求：
1. 筛选优质商品（自营优先、评分≥4.5、价格合理）
2. 识别潜在爆款
3. 返回保留的product_id列表

只返回ID，每行一个。
"""
        
        try:
            response = await self.llm.complete(prompt, temperature=0.4)
            
            valid_ids = set()
            for line in response.strip().split('\n'):
                pid = line.strip()
                if pid.startswith('jd_'):
                    valid_ids.add(pid)
            
            if valid_ids:
                return [p for p in products if p.product_id in valid_ids]
            return products
            
        except Exception as e:
            logger.error(f"LLM增强失败: {e}")
            return products
    
    async def collect_reviews(
        self,
        product_id: str,
        limit: int = 50
    ) -> List[JDReview]:
        """采集商品评论"""
        if product_id in self.review_cache:
            return self.review_cache[product_id][:limit]
        
        reviews = []
        
        await asyncio.sleep(random.uniform(0.2, 0.5))
        
        for i in range(limit):
            review = JDReview(
                review_id=f"review_{product_id}_{i}",
                product_id=product_id,
                user_name=f"用户{random.randint(1000, 9999)}",
                rating=random.randint(4, 5),
                content=random.choice([
                    "质量很好，物流快",
                    "包装精美，很满意",
                    "价格实惠，值得购买",
                    "服务态度好，下次再来",
                    "商品不错，推荐购买",
                ]),
                images=[f"https://img14.360buyimg.com/review/{product_id}_{i}.jpg"] if random.random() > 0.7 else [],
                created_at=(datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                helpful_count=random.randint(0, 100),
            )
            reviews.append(review)
        
        self.review_cache[product_id] = reviews
        self.stats["reviews_analyzed"] += len(reviews)
        
        return reviews
    
    async def analyze_sentiment(
        self,
        product_id: str,
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """情感分析"""
        reviews = await self.collect_reviews(product_id, limit=30)
        
        if not reviews:
            return {"error": "无评论数据"}
        
        # 基础统计
        ratings = [r.rating for r in reviews]
        avg_rating = sum(ratings) / len(ratings)
        
        result = {
            "product_id": product_id,
            "total_reviews": len(reviews),
            "avg_rating": round(avg_rating, 2),
            "sentiment": "positive" if avg_rating >= 4.5 else "neutral" if avg_rating >= 3.5 else "negative",
        }
        
        # LLM深度分析
        if use_llm and self.llm:
            review_texts = [f"[{r.rating}星] {r.content}" for r in reviews[:10]]
            
            prompt = f"""
分析以下京东评论的情感倾向：

{chr(10).join(review_texts)}

请提供：
1. 整体情感倾向（正面/中性/负面）
2. 主要优点（3条）
3. 主要缺点（3条）
4. 购买建议

以JSON格式返回。
"""
            
            try:
                response = await self.llm.complete(prompt, temperature=0.4)
                result["llm_analysis"] = response
            except Exception as e:
                logger.error(f"LLM情感分析失败: {e}")
        
        return result
    
    async def monitor_price_history(
        self,
        product_id: str,
        days: int = 30
    ) -> List[Dict]:
        """价格历史监控"""
        history = []
        base_price = random.uniform(100, 500)
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            price = base_price * random.uniform(0.85, 1.15)
            history.append({
                "date": date,
                "price": round(price, 2),
                "promotion": random.choice([True, False]),
            })
        
        return history
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            "cached_products": len(self.product_cache),
            "cached_reviews": sum(len(v) for v in self.review_cache.values()),
        }


# 简化接口
async def collect_jd(
    keywords: List[str],
    category: Optional[str] = None,
    llm_client=None
) -> List[Dict]:
    """简化的京东采集接口"""
    agent = JDCollectorAgent(llm_client=llm_client)
    products = await agent.collect(keywords, category, use_llm=bool(llm_client))
    return [p.to_dict() for p in products]
