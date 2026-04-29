"""
数据采集Agent基类
各平台采集Agent继承该基类，实现具体抓取逻辑
"""

import logging
import time
import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CollectedData:
    """采集到的结构化数据"""
    platform: str
    data_type: str        # ranking / pricing / inventory / review / promotion
    sku_id: str = ""
    title: str = ""
    value: str = ""
    url: str = ""
    collected_at: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.collected_at:
            self.collected_at = datetime.now().isoformat()

    @property
    def fingerprint(self) -> str:
        """数据指纹，用于去重"""
        raw = f"{self.platform}:{self.data_type}:{self.sku_id}:{self.value}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["fingerprint"] = self.fingerprint
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class CollectResult:
    """单次采集结果"""
    agent: str
    platform: str
    total: int
    new_count: int        # 去重后新增数量
    duplicate_count: int  # 重复数量
    elapsed_sec: float
    errors: List[str] = field(default_factory=list)
    data: List[CollectedData] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"[{self.agent}] {self.platform} 采集完成: "
            f"总数={self.total}, 新增={self.new_count}, "
            f"重复={self.duplicate_count}, 耗时={self.elapsed_sec:.1f}s"
        )


class BaseCollector(ABC):
    """采集Agent基类"""

    platform: str = "unknown"

    def __init__(self, max_retries: int = 3, delay: float = 2.0, timeout: int = 30):
        self.max_retries = max_retries
        self.delay = delay
        self.timeout = timeout
        self._seen_fingerprints: set = set()

    @abstractmethod
    def collect(self, keywords: List[str] = None) -> List[CollectedData]:
        """执行数据采集，返回结构化数据列表"""
        pass

    @abstractmethod
    def check_access(self) -> bool:
        """检查是否能正常访问目标平台"""
        pass

    def deduplicate(self, data: List[CollectedData]) -> List[CollectedData]:
        """基于指纹去重"""
        unique = []
        for item in data:
            fp = item.fingerprint
            if fp not in self._seen_fingerprints:
                self._seen_fingerprints.add(fp)
                unique.append(item)
        return unique

    def run(self, keywords: List[str] = None) -> CollectResult:
        """带重试和统计的采集入口"""
        start = time.time()
        errors = []

        for attempt in range(1, self.max_retries + 1):
            try:
                raw_data = self.collect(keywords)
                unique_data = self.deduplicate(raw_data)
                elapsed = time.time() - start

                result = CollectResult(
                    agent=self.__class__.__name__,
                    platform=self.platform,
                    total=len(raw_data),
                    new_count=len(unique_data),
                    duplicate_count=len(raw_data) - len(unique_data),
                    elapsed_sec=round(elapsed, 2),
                    errors=errors,
                    data=unique_data,
                )
                logger.info(result.summary())
                return result

            except Exception as e:
                errors.append(f"第{attempt}次重试失败: {str(e)}")
                logger.warning(f"[{self.platform}] 第{attempt}次采集失败: {e}")
                if attempt < self.max_retries:
                    time.sleep(self.delay * attempt)

        elapsed = time.time() - start
        return CollectResult(
            agent=self.__class__.__name__,
            platform=self.platform,
            total=0, new_count=0, duplicate_count=0,
            elapsed_sec=round(elapsed, 2),
            errors=errors,
        )

    def log_result(self, count: int):
        logger.info(f"[{self.platform}] 采集完成，共 {count} 条数据")
