"""
抖音采集Agent - LLM驱动的短视频电商数据采集
支持直播商品、短视频带货、达人分析、爆款追踪
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


class DouyinContentType(Enum):
    """内容类型"""
    LIVE = "直播"
    VIDEO = "短视频"
    PRODUCT = "商品橱窗"
    TOPIC = "话题"


@dataclass
class DouyinProduct:
    """抖音商品数据结构"""
    product_id: str
    title: str
    price: float
    original_price: Optional[float] = None
    sales: int = 0
    monthly_sales: int = 0
    commission_rate: float = 0.0
    commission: float = 0.0
    rating: float = 0.0
    review_count: int = 0
    shop_name: str = ""
    shop_id: str = ""
    category: str = ""
    content_type: str = ""  # 直播/短视频
    influencer_name: str = ""
    influencer_id: str = ""
    influencer_fans: int = 0
    video_id: str = ""
    video_likes: int = 0
    video_comments: int = 0
    video_shares: int = 0
    video_views: int = 0
    live_id: str = ""
    live_viewers: int = 0
    tags: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    url: str = ""
    crawled_at: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class DouyinInfluencer:
    """抖音达人"""
    influencer_id: str
    influencer_name: str
    avatar: str
    fans: int
    following: int
    videos: int
    likes: int
    category: str
    level: int
    commission_rate: float
    avg_views: int
    avg_likes: int
    tags: List[str] = field(default_factory=list)


@dataclass
class DouyinVideo:
    """抖音视频"""
    video_id: str
    title: str
    author_name: str
    author_id: str
    views: int
    likes: int
    comments: int
    shares: int
    duration: int  # 秒
    created_at: str
    products: List[str] = field(default_factory=list)  # 商品ID
    hashtags: List[str] = field(default_factory=list)
    music: str = ""


class DouyinCollectorAgent:
    """LLM驱动的抖音采集Agent"""
    
    def __init__(self, llm_client=None, config: Optional[Dict] = None):
        self.llm = llm_client
        self.config = config or {}
        
        # 配置
        self.max_products = self.config.get("max_products", 50)
        self.timeout = self.config.get("timeout", 30)
        
        # 缓存
        self.product_cache: Dict[str, DouyinProduct] = {}
        self.influencer_cache: Dict[str, DouyinInfluencer] = {}
        self.video_cache: Dict[str, DouyinVideo] = {}
        
        # 统计
        self.stats = {
            "total_collected": 0,
            "influencers_analyzed": 0,
            "videos_analyzed": 0,
        }
    
    async def collect(
        self,
        keywords: List[str],
        content_type: Optional[str] = None,
        use_llm: bool = True
    ) -> List[DouyinProduct]:
        """
        主采集入口
        
        Args:
            keywords: 搜索关键词
            content_type: 内容类型（直播/短视频）
            use_llm: 是否使用LLM
            
        Returns:
            商品列表
        """
        all_products = []
        
        # 1. LLM分析内容策略
        if use_llm and self.llm:
            strategy = await self._analyze_content_strategy(keywords)
            keywords = strategy.get("optimized_keywords", keywords)
            content_type = content_type or strategy.get("recommended_type")
        
        # 2. 并行采集
        tasks = [
            self._search_keyword(kw, content_type)
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
        
        # 4. LLM爆款识别
        if use_llm and self.llm:
            unique_products = await self._identify_trending_with_llm(unique_products)
        
        # 5. 统计
        self.stats["total_collected"] += len(unique_products)
        
        logger.info(f"抖音采集完成: {len(unique_products)} 条商品")
        return unique_products
    
    async def _analyze_content_strategy(
        self,
        keywords: List[str]
    ) -> Dict:
        """LLM分析内容策略"""
        prompt = f"""
作为抖音电商运营专家，请分析以下关键词的内容策略：

关键词: {', '.join(keywords)}

请提供：
1. 推荐内容类型（直播/短视频）
2. 优化后的搜索关键词
3. 建议的话题标签
4. 目标达人特征
5. 最佳发布时间段

以JSON格式返回。
"""
        
        try:
            response = await self.llm.complete(prompt, temperature=0.6)
            
            if '{' in response:
                json_str = response[response.index('{'):response.rindex('}')+1]
                return json.loads(json_str)
            
            return {"optimized_keywords": keywords}
            
        except Exception as e:
            logger.error(f"LLM策略分析失败: {e}")
            return {"optimized_keywords": keywords}
    
    async def _search_keyword(
        self,
        keyword: str,
        content_type: Optional[str]
    ) -> List[DouyinProduct]:
        """搜索单个关键词"""
        products = []
        
        try:
            await asyncio.sleep(random.uniform(0.3, 1.0))
            
            # 随机生成直播或短视频商品
            count = random.randint(5, 12)
            
            for i in range(count):
                ct = content_type or random.choice(["直播", "短视频"])
                product = self._generate_mock_product(keyword, ct, i)
                products.append(product)
            
            logger.debug(f"关键词 '{keyword}' 采集到 {len(products)} 条")
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
        
        return products
    
    def _generate_mock_product(
        self,
        keyword: str,
        content_type: str,
        index: int
    ) -> DouyinProduct:
        """生成模拟商品数据"""
        product_id = f"dy_{hashlib.md5(f'{keyword}{index}'.encode()).hexdigest()[:10]}"
        
        # 价格
        base_price = random.uniform(20, 300)
        price = round(base_price * random.uniform(0.7, 1.0), 2)
        original_price = round(base_price * random.uniform(1.2, 1.5), 2)
        
        # 销量
        sales = random.randint(100, 50000)
        monthly_sales = random.randint(500, 10000)
        
        # 佣金
        commission_rate = round(random.uniform(5, 30), 1)
        commission = round(price * commission_rate / 100, 2)
        
        # 达人
        influencer_names = [
            "花艺小课堂", "鲜花日记", "花间时光",
            "花卉知识局", "花语心愿", "花艺达人"
        ]
        influencer_name = random.choice(influencer_names)
        influencer_id = f"dy_user_{hashlib.md5(influencer_name.encode()).hexdigest()[:8]}"
        influencer_fans = random.randint(10000, 5000000)
        
        # 视频/直播数据
        video_id = f"dy_video_{hashlib.md5(f'{product_id}'.encode()).hexdigest()[:12]}"
        live_id = f"dy_live_{hashlib.md5(f'{product_id}'.encode()).hexdigest()[:12]}" if content_type == "直播" else ""
        
        return DouyinProduct(
            product_id=product_id,
            title=f"{keyword} {random.choice(['爆款', '热销', '推荐'])} - 抖音{content_type}带货",
            price=price,
            original_price=original_price,
            sales=sales,
            monthly_sales=monthly_sales,
            commission_rate=commission_rate,
            commission=commission,
            rating=round(random.uniform(4.2, 5.0), 1),
            review_count=random.randint(50, 5000),
            shop_name=random.choice(["抖音小店", "品牌旗舰店", "优选好物"]),
            shop_id=f"dy_shop_{random.randint(10000, 99999)}",
            category=keyword,
            content_type=content_type,
            influencer_name=influencer_name,
            influencer_id=influencer_id,
            influencer_fans=influencer_fans,
            video_id=video_id,
            video_likes=random.randint(1000, 500000),
            video_comments=random.randint(100, 50000),
            video_shares=random.randint(100, 20000),
            video_views=random.randint(10000, 5000000),
            live_id=live_id,
            live_viewers=random.randint(1000, 100000) if live_id else 0,
            tags=[keyword, "抖音热推", content_type][:3],
            images=[f"https://p3.douyinpic.com/{product_id}_{j}.jpeg" for j in range(1, 4)],
            url=f"https://haohuo.jinritemai.com/product/detail?id={product_id}",
            crawled_at=datetime.now().isoformat(),
        )
    
    def _deduplicate(self, products: List[DouyinProduct]) -> List[DouyinProduct]:
        """去重"""
        seen = set()
        unique = []
        
        for p in products:
            if p.product_id not in seen:
                seen.add(p.product_id)
                unique.append(p)
        
        return unique
    
    async def _identify_trending_with_llm(
        self,
        products: List[DouyinProduct]
    ) -> List[DouyinProduct]:
        """LLM识别爆款"""
        if len(products) < 5:
            return products
        
        summaries = [
            f"{p.product_id}: {p.title[:25]} ¥{p.price} 销量{p.sales} {p.content_type}"
            for p in products[:20]
        ]
        
        prompt = f"""
作为抖音电商数据分析师，请识别以下商品中的潜在爆款：

{chr(10).join(summaries)}

爆款特征：
1. 销量增长快
2. 互动率高（点赞/评论/分享）
3. 达人粉丝量适中
4. 价格有竞争力
5. 内容类型匹配

返回具有爆款潜力的product_id列表，每行一个。
"""
        
        try:
            response = await self.llm.complete(prompt, temperature=0.4)
            
            trending_ids = set()
            for line in response.strip().split('\n'):
                pid = line.strip()
                if pid.startswith('dy_'):
                    trending_ids.add(pid)
            
            if trending_ids:
                return [p for p in products if p.product_id in trending_ids]
            return products
            
        except Exception as e:
            logger.error(f"LLM爆款识别失败: {e}")
            return products
    
    async def analyze_influencer(
        self,
        influencer_id: str,
        use_llm: bool = True
    ) -> Optional[DouyinInfluencer]:
        """分析达人"""
        if influencer_id in self.influencer_cache:
            return self.influencer_cache[influencer_id]
        
        await asyncio.sleep(random.uniform(0.2, 0.5))
        
        influencer = DouyinInfluencer(
            influencer_id=influencer_id,
            influencer_name=f"达人_{influencer_id}",
            avatar=f"https://p3.douyinpic.com/avatar/{influencer_id}.jpg",
            fans=random.randint(10000, 5000000),
            following=random.randint(100, 1000),
            videos=random.randint(50, 500),
            likes=random.randint(100000, 50000000),
            category=random.choice(["鲜花", "生活", "美食", "美妆"]),
            level=random.randint(1, 10),
            commission_rate=round(random.uniform(5, 25), 1),
            avg_views=random.randint(10000, 1000000),
            avg_likes=random.randint(1000, 100000),
            tags=random.sample(["专业", "种草", "测评", "直播"], k=2),
        )
        
        self.influencer_cache[influencer_id] = influencer
        self.stats["influencers_analyzed"] += 1
        
        return influencer
    
    async def track_hashtag(
        self,
        hashtag: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """追踪话题"""
        trend_data = {
            "hashtag": hashtag,
            "period": f"最近{days}天",
            "total_videos": random.randint(100, 10000),
            "total_views": random.randint(1000000, 100000000),
            "avg_engagement": round(random.uniform(5, 15), 1),
            "top_products": [],
        }
        
        # 模拟热门商品
        for i in range(5):
            trend_data["top_products"].append({
                "product_id": f"dy_{hashlib.md5(f'{hashtag}{i}'.encode()).hexdigest()[:10]}",
                "sales": random.randint(1000, 50000),
                "trend": random.choice(["上升", "稳定", "下降"]),
            })
        
        return trend_data
    
    async def get_live_realtime(
        self,
        live_id: str
    ) -> Dict[str, Any]:
        """获取直播实时数据"""
        return {
            "live_id": live_id,
            "viewers": random.randint(1000, 100000),
            "likes": random.randint(10000, 500000),
            "comments": random.randint(1000, 50000),
            "products_shown": random.randint(5, 20),
            "conversion_rate": round(random.uniform(1, 10), 2),
            "gmv": round(random.uniform(10000, 500000), 2),
            "timestamp": datetime.now().isoformat(),
        }
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            "cached_products": len(self.product_cache),
            "cached_influencers": len(self.influencer_cache),
        }


# 简化接口
async def collect_douyin(
    keywords: List[str],
    content_type: Optional[str] = None,
    llm_client=None
) -> List[Dict]:
    """简化的抖音采集接口"""
    agent = DouyinCollectorAgent(llm_client=llm_client)
    products = await agent.collect(keywords, content_type, use_llm=bool(llm_client))
    return [p.to_dict() for p in products]
