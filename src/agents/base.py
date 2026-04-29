"""
数据采集Agent基类
各平台采集Agent继承此基类，实现具体抓取逻辑
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class CollectedData:
    """采集到的结构化数据"""
    platform: str
    data_type: str        # ranking / pricing / inventory / review / promotion
    sku_id: str = ""
    title: str = ""
    value: str = ""
    extra: dict = None

    def to_dict(self):
        d = asdict(self)
        return d


class BaseCollector(ABC):
    """采集Agent基类"""

    platform: str = "unknown"

    def __init__(self, max_retries: int = 3, delay: float = 2.0):
        self.max_retries = max_retries
        self.delay = delay

    @abstractmethod
    def collect(self, keywords: List[str] = None) -> List[CollectedData]:
        """执行数据采集，返回结构化数据列表"""
        pass

    @abstractmethod
    def check_access(self) -> bool:
        """检查是否能正常访问目标平台"""
        pass

    def log_result(self, count: int):
        logger.info(f"[{self.platform}] 采集完成，共 {count} 条数据")
