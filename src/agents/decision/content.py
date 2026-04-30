"""
内容决策Agent - LLM驱动的智能内容生成与优化
标题优化、描述生成、关键词推荐、A/B测试建议
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """内容类型"""
    PRODUCT_TITLE = "product_title"
    PRODUCT_DESC = "product_desc"
    AD_COPY = "ad_copy"
    SOCIAL_POST = "social_post"
    SEO_KEYWORDS = "seo_keywords"
    PROMOTION_TEXT = "promotion_text"


class ContentQuality(Enum):
    """内容质量等级"""
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"


class Platform(Enum):
    """平台枚举"""
    TAOBAO = "taobao"
    JD = "jd"
    MEITUAN = "meituan"
    DOUYIN = "douyin"
    WECHAT = "wechat"


@dataclass
class ContentAnalysis:
    """内容分析结果"""
    content: str
    content_type: ContentType
    quality_score: float
    quality_level: ContentQuality
    issues: List[str]
    suggestions: List[str]
    keyword_coverage: Dict[str, float]
    readability_score: float
    platform_compliance: Dict[str, bool]


@dataclass
class ABTestVariant:
    """A/B测试变体"""
    variant_id: str
    content: str
    predicted_ctr: float
    predicted_conversion: float
    tags: List[str]
    created_at: datetime = field(default_factory=datetime.now)


class ContentAgent:
    """LLM驱动的内容决策Agent"""
    
    def __init__(self, llm_client=None, config: Optional[Dict] = None):
        self.llm = llm_client
        self.config = config or {}
        
        self.platform_rules = {
            Platform.TAOBAO: {
                "max_title_length": 60,
                "max_desc_length": 500,
                "forbidden_words": ["第一", "最好", "顶级"],
                "required_elements": ["品牌", "品类", "卖点"],
            },
            Platform.JD: {
                "max_title_length": 50,
                "max_desc_length": 400,
                "forbidden_words": ["第一", "最"],
                "required_elements": ["品牌", "型号"],
            },
            Platform.MEITUAN: {
                "max_title_length": 40,
                "max_desc_length": 200,
                "forbidden_words": [],
                "required_elements": ["品类"],
            },
            Platform.DOUYIN: {
                "max_title_length": 30,
                "max_desc_length": 150,
                "forbidden_words": [],
                "required_elements": [],
            },
        }
        
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, ContentTemplate]:
        """加载内容模板"""
        return {
            "product_title_basic": ContentTemplate(
                template_id="product_title_basic",
                name="基础商品标题模板",
                content_type=ContentType.PRODUCT_TITLE,
                platform=Platform.TAOBAO,
                template="{brand} {category} {feature} {benefit}",
                variables=["brand", "category", "feature", "benefit"],
                examples=["花仙子 鲜花速递 当日达 浪漫告白"],
            ),
            "promotion_urgent": ContentTemplate(
                template_id="promotion_urgent",
                name="紧急促销文案",
                content_type=ContentType.PROMOTION_TEXT,
                platform=Platform.MEITUAN,
                template="限时{discount}折 | {product}仅需{price}元 | {urgency}",
                variables=["discount", "product", "price", "urgency"],
                examples=["限时8折 | 玫瑰花束仅需99元 | 仅剩3小时"],
            ),
        }
    
    async def optimize_title(
        self,
        original_title: str,
        platform: Platform,
        keywords: Optional[List[str]] = None,
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        优化商品标题
        
        Args:
            original_title: 原始标题
            platform: 目标平台
            keywords: 目标关键词列表
            use_llm: 是否使用LLM增强
            
        Returns:
            优化后的标题及分析
        """
        rules = self.platform_rules.get(platform, {})
        max_length = rules.get("max_title_length", 60)
        
        # 1. 基础优化
        issues = []
        suggestions = []
        
        # 检查长度
        if len(original_title) > max_length:
            issues.append(f"标题过长({len(original_title)}字)，超出平台限制({max_length}字)")
            suggestions.append(f"建议精简至{max_length}字以内")
        
        # 检查违禁词
        forbidden = rules.get("forbidden_words", [])
        found_forbidden = [w for w in forbidden if w in original_title]
        if found_forbidden:
            issues.append(f"包含违禁词: {', '.join(found_forbidden)}")
            suggestions.append("移除违禁词以避免违规")
        
        # 检查必需元素
        required = rules.get("required_elements", [])
        missing_required = [e for e in required if e not in original_title]
        if missing_required:
            issues.append(f"缺少推荐元素: {', '.join(missing_required)}")
        
        # 2. 关键词覆盖分析
        keyword_coverage = {}
        if keywords:
            for kw in keywords:
                coverage = 1.0 if kw in original_title else 0.0
                keyword_coverage[kw] = coverage
            
            missing_keywords = [kw for kw in keywords if kw not in original_title]
            if missing_keywords:
                suggestions.append(f"建议添加关键词: {', '.join(missing_keywords)}")
        
        # 3. 生成优化标题
        optimized_title = original_title
        optimized_variants = []
        
        if use_llm and self.llm:
            llm_result = await self._llm_optimize_title(
                original_title, platform, keywords
            )
            if llm_result:
                optimized_title = llm_result.get("optimized_title", original_title)
                optimized_variants = llm_result.get("variants", [])
                suggestions.extend(llm_result.get("suggestions", []))
        
        # 4. 质量评分
        quality_score = self._calculate_title_quality(
            optimized_title, platform, keywords
        )
        
        if quality_score >= 0.85:
            quality_level = ContentQuality.EXCELLENT
        elif quality_score >= 0.70:
            quality_level = ContentQuality.GOOD
        elif quality_score >= 0.50:
            quality_level = ContentQuality.AVERAGE
        else:
            quality_level = ContentQuality.POOR
        
        return {
            "original_title": original_title,
            "optimized_title": optimized_title,
            "quality_score": round(quality_score, 2),
            "quality_level": quality_level.value,
            "platform": platform.value,
            "issues": issues,
            "suggestions": suggestions,
            "keyword_coverage": keyword_coverage,
            "variants": optimized_variants,
            "timestamp": datetime.now().isoformat(),
        }
    
    async def _llm_optimize_title(
        self,
        title: str,
        platform: Platform,
        keywords: Optional[List[str]]
    ) -> Optional[Dict]:
        """使用LLM优化标题"""
        if not self.llm:
            return None
        
        prompt = f"""
作为电商标题优化专家，请优化以下商品标题：

原始标题: {title}
目标平台: {platform.value}
目标关键词: {', '.join(keywords) if keywords else '无'}

平台规则:
- 最大长度: {self.platform_rules.get(platform, {}).get('max_title_length', 60)}字
- 违禁词: {self.platform_rules.get(platform, {}).get('forbidden_words', [])}

请提供：
1. 优化后的标题
2. 2-3个备选标题
3. 优化理由

以JSON格式返回。
"""
        
        try:
            response = await self.llm.complete(prompt, temperature=0.5)
            return {"llm_response": response}
        except Exception as e:
            logger.error(f"LLM标题优化失败: {e}")
            return None
    
    def _calculate_title_quality(
        self,
        title: str,
        platform: Platform,
        keywords: Optional[List[str]]
    ) -> float:
        """计算标题质量得分"""
        score = 0.5  # 基础分
        
        # 长度合适 +0.2
        max_len = self.platform_rules.get(platform, {}).get("max_title_length", 60)
        if len(title) <= max_len and len(title) >= max_len * 0.5:
            score += 0.2
        
        # 包含关键词 +0.2
        if keywords:
            coverage = sum(1 for kw in keywords if kw in title) / len(keywords)
            score += coverage * 0.2
        
        # 无违禁词 +0.1
        forbidden = self.platform_rules.get(platform, {}).get("forbidden_words", [])
        if not any(w in title for w in forbidden):
            score += 0.1
        
        return min(score, 1.0)
    
    async def generate_description(
        self,
        product_info: Dict[str, Any],
        platform: Platform,
        style: str = "professional",
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        生成商品描述
        
        Args:
            product_info: 商品信息字典
            platform: 目标平台
            style: 风格 (professional/casual/promotional)
            use_llm: 是否使用LLM
            
        Returns:
            生成的描述及元信息
        """
        max_length = self.platform_rules.get(platform, {}).get("max_desc_length", 500)
        
        # 构建基础描述
        parts = []
        
        if product_info.get("brand"):
            parts.append(f"品牌：{product_info['brand']}")
        
        if product_info.get("features"):
            parts.append("产品特点：")
            for feature in product_info["features"][:3]:
                parts.append(f"• {feature}")
        
        if product_info.get("specifications"):
            parts.append("规格参数：")
            for key, value in list(product_info["specifications"].items())[:5]:
                parts.append(f"{key}: {value}")
        
        basic_description = "\n".join(parts)
        
        # LLM增强
        enhanced_description = basic_description
        if use_llm and self.llm:
            llm_desc = await self._llm_generate_description(
                product_info, platform, style
            )
            if llm_desc:
                enhanced_description = llm_desc
        
        # 截断到平台限制
        if len(enhanced_description) > max_length:
            enhanced_description = enhanced_description[:max_length-3] + "..."
        
        return {
            "description": enhanced_description,
            "platform": platform.value,
            "style": style,
            "length": len(enhanced_description),
            "max_length": max_length,
            "timestamp": datetime.now().isoformat(),
        }
    
    async def _llm_generate_description(
        self,
        product_info: Dict,
        platform: Platform,
        style: str
    ) -> Optional[str]:
        """使用LLM生成描述"""
        if not self.llm:
            return None
        
        prompt = f"""
为以下商品生成一段{style}风格的描述：

商品信息: {product_info}
目标平台: {platform.value}
最大长度: {self.platform_rules.get(platform, {}).get('max_desc_length', 500)}字

要求：
- 突出产品卖点
- 语言{style}
- 符合平台规范
"""
        
        try:
            response = await self.llm.complete(prompt, temperature=0.7)
            return response.strip()
        except Exception as e:
            logger.error(f"LLM描述生成失败: {e}")
            return None
    
    async def suggest_keywords(
        self,
        product_name: str,
        category: str,
        platform: Platform,
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        推荐关键词
        
        Args:
            product_name: 商品名称
            category: 商品类目
            platform: 目标平台
            use_llm: 是否使用LLM
            
        Returns:
            关键词推荐列表
        """
        # 基础关键词
        base_keywords = [
            product_name,
            category,
            f"{category}推荐",
            f"{product_name}优惠",
        ]
        
        # LLM扩展关键词
        extended_keywords = []
        if use_llm and self.llm:
            extended = await self._llm_suggest_keywords(product_name, category, platform)
            if extended:
                extended_keywords = extended
        
        all_keywords = base_keywords + extended_keywords
        
        # 去重
        unique_keywords = list(dict.fromkeys(all_keywords))
        
        return {
            "product_name": product_name,
            "category": category,
            "platform": platform.value,
            "keywords": unique_keywords[:10],
            "base_keywords": base_keywords,
            "extended_keywords": extended_keywords,
            "count": len(unique_keywords[:10]),
            "timestamp": datetime.now().isoformat(),
        }
    
    async def _llm_suggest_keywords(
        self,
        product_name: str,
        category: str,
        platform: Platform
    ) -> List[str]:
        """使用LLM推荐关键词"""
        if not self.llm:
            return []
        
        prompt = f"""
为以下商品推荐10个高搜索量、低竞争的关键词：

商品名称: {product_name}
商品类目: {category}
目标平台: {platform.value}

要求：
- 符合平台搜索习惯
- 包含长尾关键词
- 避免过于泛泛的词

以JSON数组格式返回关键词列表。
"""
        
        try:
            response = await self.llm.complete(prompt, temperature=0.5)
            # 简化解析
            return []
        except Exception as e:
            logger.error(f"LLM关键词推荐失败: {e}")
            return []
    
    async def generate_ab_test_variants(
        self,
        content: str,
        content_type: ContentType,
        platform: Platform,
        num_variants: int = 3,
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        生成A/B测试变体
        
        Args:
            content: 原始内容
            content_type: 内容类型
            platform: 平台
            num_variants: 变体数量
            use_llm: 是否使用LLM
            
        Returns:
            A/B测试变体列表
        """
        variants = []
        
        # 变体A: 原始内容（对照组）
        variants.append(ABTestVariant(
            variant_id="control",
            content=content,
            predicted_ctr=0.5,
            predicted_conversion=0.02,
            tags=["control"],
        ))
        
        # 生成其他变体
        for i in range(1, num_variants):
            variant_content = content
            if use_llm and self.llm:
                llm_variant = await self._llm_create_variant(
                    content, content_type, platform, i
                )
                if llm_variant:
                    variant_content = llm_variant
            
            variants.append(ABTestVariant(
                variant_id=f"variant_{i}",
                content=variant_content,
                predicted_ctr=0.5 + (i * 0.02),
                predicted_conversion=0.02 + (i * 0.005),
                tags=[f"variant_{i}"],
            ))
        
        return {
            "original_content": content,
            "content_type": content_type.value,
            "platform": platform.value,
            "variants": [
                {
                    "variant_id": v.variant_id,
                    "content": v.content,
                    "predicted_ctr": v.predicted_ctr,
                    "predicted_conversion": v.predicted_conversion,
                    "tags": v.tags,
                }
                for v in variants
            ],
            "recommendation": "建议同时测试所有变体，收集至少1000次曝光后分析结果",
            "timestamp": datetime.now().isoformat(),
        }
    
    async def _llm_create_variant(
        self,
        content: str,
        content_type: ContentType,
        platform: Platform,
        variant_num: int
    ) -> Optional[str]:
        """使用LLM创建变体"""
        if not self.llm:
            return None
        
        strategies = [
            "更强调情感诉求",
            "更强调功能卖点",
            "更简洁直接",
        ]
        
        strategy = strategies[variant_num % len(strategies)]
        
        prompt = f"""
请基于以下内容创建一个变体版本：

原始内容: {content}
内容类型: {content_type.value}
平台: {platform.value}
优化方向: {strategy}

保持核心信息不变，调整表达方式。
"""
        
        try:
            response = await self.llm.complete(prompt, temperature=0.7)
            return response.strip()
        except Exception as e:
            logger.error(f"LLM变体生成失败: {e}")
            return None
    
    def analyze_content(
        self,
        content: str,
        content_type: ContentType,
        platform: Platform
    ) -> ContentAnalysis:
        """分析内容质量"""
        issues = []
        suggestions = []
        
        # 平台规范检查
        rules = self.platform_rules.get(platform, {})
        
        max_len_key = f"max_{content_type.value}_length"
        max_len = rules.get(max_len_key, 500)
        
        if len(content) > max_len:
            issues.append(f"内容超出平台限制({len(content)}/{max_len})")
        
        # 违禁词检查
        forbidden = rules.get("forbidden_words", [])
        found = [w for w in forbidden if w in content]
        if found:
            issues.append(f"包含违禁词: {', '.join(found)}")
        
        # 质量评分
        quality_score = 0.7
        if not issues:
            quality_score = 0.9
        elif len(issues) > 2:
            quality_score = 0.5
        
        if quality_score >= 0.85:
            quality_level = ContentQuality.EXCELLENT
        elif quality_score >= 0.70:
            quality_level = ContentQuality.GOOD
        elif quality_score >= 0.50:
            quality_level = ContentQuality.AVERAGE
        else:
            quality_level = ContentQuality.POOR
        
        return ContentAnalysis(
            content=content,
            content_type=content_type,
            quality_score=quality_score,
            quality_level=quality_level,
            issues=issues,
            suggestions=suggestions,
            keyword_coverage={},
            readability_score=0.8,
            platform_compliance={},
        )


# 简化接口
async def optimize_product_content(
    title: str,
    platform: str,
    keywords: Optional[List[str]] = None,
    llm_client=None
) -> Dict:
    """简化的内容优化接口"""
    agent = ContentAgent(llm_client=llm_client)
    platform_enum = Platform(platform)
    return await agent.optimize_title(title, platform_enum, keywords, use_llm=bool(llm_client))
