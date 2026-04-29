"""
内容Agent
生成商品标题、详情页文案、活动话术
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class ContentAgent:
    """商品内容生成"""

    def generate_title(self, product_info: Dict) -> str:
        """生成商品标题"""
        name = product_info.get("name", "")
        occasion = product_info.get("occasion", "")
        style = product_info.get("style", "")

        parts = [p for p in [name, occasion, style] if p]
        title = " ".join(parts) if parts else "新品鲜花"
        return title[:30]

    def generate_detail_copy(self, product_info: Dict) -> Dict:
        """生成详情页文案"""
        name = product_info.get("name", "鲜花")
        highlights = product_info.get("highlights", ["新鲜直送", "当日达"])

        copy = {
            "headline": f"{name} — 闪购专享",
            "bullets": [f"✓ {h}" for h in highlights],
            "closing": "限时优惠，售完即止",
        }

        logger.info(f"[ContentAgent] 生成文案: {copy['headline']}")
        return copy

    def generate_promo_copy(self, product_info: Dict, promo_type: str = "flash_sale") -> str:
        """生成促销话术"""
        name = product_info.get("name", "鲜花")
        templates = {
            "flash_sale": f"⚡ {name}闪购价，手慢无！",
            "new_arrival": f"🆕 {name}新品上线，首单立减！",
            "seasonal": f"🌸 {name}当季限定，错过等一年！",
        }
        return templates.get(promo_type, templates["flash_sale"])
