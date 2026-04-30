"""
美团闪购采集Agent - LLM驱动的本地生活服务数据采集
支持鲜花闪购、配送区域、商家分析、订单监控
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


class MeituanCategory(Enum):
    """美团闪购类目"""
    FLOWERS = "鲜花"
    FRUIT = "水果"
    CAKE = "蛋糕"
    FRESH = "生鲜"
    PHARMACY = "药品"
    SUPERMARKET = "超市"


@dataclass
class MeituanProduct:
    """美团闪购商品数据结构"""
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
    brand: str = ""
    category: str = ""
    delivery_time: str = ""  # 配送时间
    delivery_fee: float = 0.0
    min_order: float = 0.0
    service_area: List[str] = field(default_factory=list)  # 配送区域
    tags: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    url: str = ""
    crawled_at: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class MeituanShop:
    """美团商家信息"""
    shop_id: str
    shop_name: str
    shop_rating: float
    shop_type: str  # 品牌店/个体店
    product_count: int
    monthly_orders: int
    avg_delivery_time: int  # 分钟
    service_radius: float  # 公里
    service_areas: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    open_hours: str = ""
    phone: str = ""
    address: str = ""


@dataclass
class DeliveryZone:
    """配送区域"""
    zone_id: str
    zone_name: str
    center_lat: float
    center_lng: float
    radius: float  # 公里
    population: int
    avg_income: float
    competitor_count: int


class MeituanFlashCollectorAgent:
    """LLM驱动的美团闪购采集Agent"""
    
    def __init__(self, llm_client=None, config: Optional[Dict] = None):
        self.llm = llm_client
        self.config = config or {}
        
        # 采集配置
        self.max_products = self.config.get("max_products", 50)
        self.timeout = self.config.get("timeout", 30)
        self.target_city = self.config.get("city", "上海")
        
        # 缓存
        self.product_cache: Dict[str, MeituanProduct] = {}
        self.shop_cache: Dict[str, MeituanShop] = {}
        self.zone_cache: Dict[str, DeliveryZone] = {}
        
        # 统计
        self.stats = {
            "total_collected": 0,
            "shops_analyzed": 0,
            "zones_mapped": 0,
        }
    
    async def collect(
        self,
        keywords: List[str],
        city: Optional[str] = None,
        category: Optional[str] = None,
        use_llm: bool = True
    ) -> List[MeituanProduct]:
        """
        主采集入口
        
        Args:
            keywords: 搜索关键词
            city: 城市
            category: 类目
            use_llm: 是否使用LLM
            
        Returns:
            商品列表
        """
        city = city or self.target_city
        all_products = []
        
        # 1. LLM分析搜索意图
        if use_llm and self.llm:
            search_intent = await self._analyze_search_intent(keywords, city)
            keywords = search_intent.get("expanded_keywords", keywords)
        
        # 2. 并行采集
        tasks = [
            self._search_keyword(kw, city, category)
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
        
        # 4. LLM质量筛选
        if use_llm and self.llm:
            unique_products = await self._quality_filter_with_llm(unique_products)
        
        # 5. 更新统计
        self.stats["total_collected"] += len(unique_products)
        
        logger.info(f"美团闪购采集完成: {len(unique_products)} 条商品")
        return unique_products
    
    async def _analyze_search_intent(
        self,
        keywords: List[str],
        city: str
    ) -> Dict:
        """LLM分析搜索意图"""
        prompt = f"""
作为本地生活服务专家，请分析以下搜索需求：

关键词: {', '.join(keywords)}
城市: {city}

请分析：
1. 用户真实需求（节日送礼/日常消费/商务用途）
2. 推荐搜索词扩展（同义词、场景词）
3. 价格区间建议
4. 配送时效要求

以JSON格式返回。
"""
        
        try:
            response = await self.llm.complete(prompt, temperature=0.5)
            
            # 解析JSON
            if '{' in response:
                json_str = response[response.index('{'):response.rindex('}')+1]
                return json.loads(json_str)
            
            return {"expanded_keywords": keywords}
            
        except Exception as e:
            logger.error(f"LLM意图分析失败: {e}")
            return {"expanded_keywords": keywords}
    
    async def _search_keyword(
        self,
        keyword: str,
        city: str,
        category: Optional[str]
    ) -> List[MeituanProduct]:
        """搜索单个关键词"""
        products = []
        
        try:
            # 模拟采集延迟
            await asyncio.sleep(random.uniform(0.3, 1.0))
            
            # 生成模拟数据
            for i in range(random.randint(5, 12)):
                product = self._generate_mock_product(keyword, city, category, i)
                products.append(product)
            
            logger.debug(f"关键词 '{keyword}' 在 {city} 采集到 {len(products)} 条")
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
        
        return products
    
    def _generate_mock_product(
        self,
        keyword: str,
        city: str,
        category: Optional[str],
        index: int
    ) -> MeituanProduct:
        """生成模拟商品数据"""
        product_id = f"mt_{hashlib.md5(f'{keyword}{city}{index}'.encode()).hexdigest()[:12]}"
        
        # 价格
        base_price = random.uniform(30, 300)
        price = round(base_price * random.uniform(0.8, 1.0), 2)
        original_price = round(base_price * random.uniform(1.1, 1.4), 2)
        
        # 销量
        sales = random.randint(20, 5000)
        monthly_sales = random.randint(100, 2000)
        
        # 配送
        delivery_time = f"{random.randint(20, 60)}分钟"
        delivery_fee = round(random.uniform(0, 8), 2)
        min_order = round(random.uniform(0, 50), 2)
        
        # 配送区域
        districts = ["朝阳区", "海淀区", "东城区", "西城区", "丰台区"]
        service_area = random.sample(districts, k=random.randint(2, 5))
        
        # 店铺
        shop_names = [
            "花语鲜花速递", "鲜花坊旗舰店", "花之恋配送中心",
            "花仙子鲜花店", "浪漫花屋", "花艺轩"
        ]
        shop_name = random.choice(shop_names)
        shop_id = f"mt_shop_{hashlib.md5(shop_name.encode()).hexdigest()[:8]}"
        
        return MeituanProduct(
            product_id=product_id,
            title=f"{keyword} {category or '鲜花'} - {city}同城配送",
            price=price,
            original_price=original_price if random.random() > 0.4 else None,
            sales=sales,
            monthly_sales=monthly_sales,
            rating=round(random.uniform(4.2, 5.0), 1),
            review_count=random.randint(50, 3000),
            shop_name=shop_name,
            shop_id=shop_id,
            shop_rating=round(random.uniform(4.3, 5.0), 1),
            brand=random.choice(["自营", "品牌", "个体"]),
            category=category or "鲜花",
            delivery_time=delivery_time,
            delivery_fee=delivery_fee,
            min_order=min_order,
            service_area=service_area,
            tags=[keyword, "闪购", "同城配送"][:3],
            images=[f"https://img.meituan.net/{product_id}_{j}.jpg" for j in range(1, 4)],
            url=f"https://i.meituan.com/awp/h5/product/{product_id}",
            crawled_at=datetime.now().isoformat(),
        )
    
    def _deduplicate(self, products: List[MeituanProduct]) -> List[MeituanProduct]:
        """去重"""
        seen = set()
        unique = []
        
        for p in products:
            if p.product_id not in seen:
                seen.add(p.product_id)
                unique.append(p)
        
        return unique
    
    async def _quality_filter_with_llm(
        self,
        products: List[MeituanProduct]
    ) -> List[MeituanProduct]:
        """LLM质量筛选"""
        if len(products) < 5:
            return products
        
        # 批量筛选
        summaries = [
            f"{p.product_id}: {p.title[:25]} ¥{p.price} {p.delivery_time}"
            for p in products[:20]
        ]
        
        prompt = f"""
作为美团闪购运营专家，请筛选以下商品：

{chr(10).join(summaries)}

要求：
1. 保留配送时效合理的商品（≤60分钟）
2. 去除价格异常商品
3. 保留评分≥4.0的商品

返回保留的product_id列表，每行一个。
"""
        
        try:
            response = await self.llm.complete(prompt, temperature=0.3)
            valid_ids = set()
            
            for line in response.strip().split('\n'):
                pid = line.strip()
                if pid.startswith('mt_'):
                    valid_ids.add(pid)
            
            if valid_ids:
                return [p for p in products if p.product_id in valid_ids]
            return products
            
        except Exception as e:
            logger.error(f"LLM筛选失败: {e}")
            return products
    
    async def analyze_shop(
        self,
        shop_id: str,
        use_llm: bool = True
    ) -> Optional[MeituanShop]:
        """分析商家"""
        if shop_id in self.shop_cache:
            return self.shop_cache[shop_id]
        
        # 模拟采集
        await asyncio.sleep(random.uniform(0.3, 0.8))
        
        shop = MeituanShop(
            shop_id=shop_id,
            shop_name=f"商家_{shop_id}",
            shop_rating=round(random.uniform(4.3, 5.0), 1),
            shop_type=random.choice(["品牌店", "个体店", "连锁店"]),
            product_count=random.randint(30, 200),
            monthly_orders=random.randint(500, 10000),
            avg_delivery_time=random.randint(25, 50),
            service_radius=round(random.uniform(3.0, 10.0), 1),
            service_areas=random.sample(["朝阳区", "海淀区", "东城区"], k=random.randint(2, 3)),
            categories=random.sample(["鲜花", "水果", "蛋糕"], k=2),
            open_hours="08:00-22:00",
            phone="400-xxx-xxxx",
            address=f"北京市{random.choice(['朝阳', '海淀', '东城'])}区xxx街道",
        )
        
        self.shop_cache[shop_id] = shop
        self.stats["shops_analyzed"] += 1
        
        return shop
    
    async def map_delivery_zones(
        self,
        city: str
    ) -> List[DeliveryZone]:
        """绘制配送区域地图"""
        zones = []
        
        # 模拟生成配送区域
        district_names = ["朝阳区", "海淀区", "东城区", "西城区", "丰台区", "石景山区"]
        
        for name in district_names:
            zone = DeliveryZone(
                zone_id=f"zone_{hashlib.md5(f'{city}{name}'.encode()).hexdigest()[:8]}",
                zone_name=f"{city}{name}",
                center_lat=39.9 + random.uniform(-0.1, 0.1),
                center_lng=116.4 + random.uniform(-0.1, 0.1),
                radius=round(random.uniform(3.0, 8.0), 1),
                population=random.randint(50000, 500000),
                avg_income=round(random.uniform(8000, 20000), 0),
                competitor_count=random.randint(5, 50),
            )
            zones.append(zone)
        
        self.stats["zones_mapped"] = len(zones)
        
        logger.info(f"绘制配送区域: {city} {len(zones)} 个区域")
        return zones
    
    async def monitor_competition(
        self,
        category: str,
        city: str
    ) -> Dict[str, Any]:
        """竞品监控"""
        # 采集该类目商品
        products = await self.collect([category], city, category, use_llm=False)
        
        if not products:
            return {"error": "无数据"}
        
        # 统计分析
        shops = {}
        for p in products:
            if p.shop_id not in shops:
                shops[p.shop_id] = {
                    "shop_name": p.shop_name,
                    "product_count": 0,
                    "total_sales": 0,
                    "avg_price": 0,
                    "prices": [],
                }
            shops[p.shop_id]["product_count"] += 1
            shops[p.shop_id]["total_sales"] += p.sales
            shops[p.shop_id]["prices"].append(p.price)
        
        # 计算平均价格
        for shop in shops.values():
            shop["avg_price"] = round(sum(shop["prices"]) / len(shop["prices"]), 2)
            del shop["prices"]
        
        return {
            "category": category,
            "city": city,
            "total_products": len(products),
            "total_shops": len(shops),
            "top_shops": sorted(
                shops.items(),
                key=lambda x: x[1]["total_sales"],
                reverse=True
            )[:5],
            "market_avg_price": round(sum(p.price for p in products) / len(products), 2),
        }
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            "cached_products": len(self.product_cache),
            "cached_shops": len(self.shop_cache),
        }


# 简化接口
async def collect_meituan(
    keywords: List[str],
    city: Optional[str] = None,
    category: Optional[str] = None,
    llm_client=None
) -> List[Dict]:
    """简化的美团闪购采集接口"""
    agent = MeituanFlashCollectorAgent(llm_client=llm_client)
    products = await agent.collect(keywords, city, category, use_llm=bool(llm_client))
    return [p.to_dict() for p in products]
