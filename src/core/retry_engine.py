"""
retry_engine.py - 智能重试引擎
支持指数退避、失败原因分析、自适应重试策略
"""
import asyncio
import time
import random
from typing import Callable, Optional, Any, Dict, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class RetryReason(Enum):
    NETWORK_ERROR = "network_error"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    SERVER_ERROR = "server_error"
    INVALID_RESPONSE = "invalid_response"
    UNKNOWN = "unknown"


@dataclass
class RetryRecord:
    attempt: int
    reason: RetryReason
    delay: float
    success: bool
    error: Optional[str] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class RetryResult:
    success: bool
    attempts: int
    total_duration: float
    records: List[RetryRecord]
    final_result: Any = None
    final_error: Optional[str] = None


class RetryEngine:
    """
    智能重试引擎
    
    功能：
    1. 指数退避 + 随机抖动
    2. 失败原因自动识别
    3. 自适应重试策略（根据错误类型调整参数）
    4. 重试日志与统计
    5. 最大重试次数保护
    """
    
    # 默认配置
    DEFAULT_CONFIG = {
        "max_retries": 3,
        "base_delay": 1.0,  # 秒
        "max_delay": 30.0,
        "jitter": 0.1,  # 随机抖动比例
        "exponential_base": 2.0,
        "retry_on": [
            RetryReason.NETWORK_ERROR,
            RetryReason.RATE_LIMIT,
            RetryReason.TIMEOUT,
            RetryReason.SERVER_ERROR,
        ],
    }
    
    # 错误类型到重试原因的映射
    ERROR_PATTERNS = {
        "connection": RetryReason.NETWORK_ERROR,
        "timeout": RetryReason.TIMEOUT,
        "429": RetryReason.RATE_LIMIT,
        "rate limit": RetryReason.RATE_LIMIT,
        "500": RetryReason.SERVER_ERROR,
        "502": RetryReason.SERVER_ERROR,
        "503": RetryReason.SERVER_ERROR,
        "504": RetryReason.SERVER_ERROR,
        "invalid": RetryReason.INVALID_RESPONSE,
        "json": RetryReason.INVALID_RESPONSE,
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.retry_history: List[RetryRecord] = []
        self.stats = {
            "total_retries": 0,
            "successful_retries": 0,
            "failed_retries": 0,
            "avg_attempts": 0.0,
        }
        
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs,
    ) -> RetryResult:
        """
        带智能重试的函数执行
        
        Args:
            func: 要执行的异步函数
            *args, **kwargs: 函数参数
            
        Returns:
            RetryResult: 重试结果
        """
        start_time = time.time()
        records = []
        last_error = None
        
        for attempt in range(self.config["max_retries"] + 1):
            try:
                # 执行函数
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = await asyncio.get_event_loop().run_in_executor(None, func, *args, **kwargs)
                
                # 成功
                record = RetryRecord(
                    attempt=attempt,
                    reason=RetryReason.UNKNOWN,
                    delay=0,
                    success=True,
                )
                records.append(record)
                self._update_stats(records, True)
                
                return RetryResult(
                    success=True,
                    attempts=attempt + 1,
                    total_duration=time.time() - start_time,
                    records=records,
                    final_result=result,
                )
                
            except Exception as e:
                last_error = str(e)
                reason = self._classify_error(e)
                
                # 判断是否应该重试
                should_retry = (
                    reason in self.config["retry_on"]
                    and attempt < self.config["max_retries"]
                )
                
                # 计算延迟
                delay = self._calculate_delay(attempt) if should_retry else 0
                
                # 记录
                record = RetryRecord(
                    attempt=attempt,
                    reason=reason,
                    delay=delay,
                    success=False,
                    error=last_error,
                )
                records.append(record)
                
                if should_retry:
                    await asyncio.sleep(delay)
                else:
                    break
                    
        # 所有重试都失败
        self._update_stats(records, False)
        return RetryResult(
            success=False,
            attempts=len(records),
            total_duration=time.time() - start_time,
            records=records,
            final_error=last_error,
        )
        
    def _classify_error(self, error: Exception) -> RetryReason:
        """根据错误信息分类"""
        error_str = str(error).lower()
        
        for pattern, reason in self.ERROR_PATTERNS.items():
            if pattern in error_str:
                return reason
                
        return RetryReason.UNKNOWN
        
    def _calculate_delay(self, attempt: int) -> float:
        """
        计算重试延迟（指数退避 + 随机抖动）
        
        公式：base_delay * (exponential_base ^ attempt) * (1 + jitter * random)
        """
        base = self.config["base_delay"]
        exp_base = self.config["exponential_base"]
        max_delay = self.config["max_delay"]
        jitter = self.config["jitter"]
        
        # 指数退避
        delay = base * (exp_base ** attempt)
        
        # 限制最大延迟
        delay = min(delay, max_delay)
        
        # 添加随机抖动
        jitter_amount = delay * jitter * (random.random() * 2 - 1)
        delay = max(0, delay + jitter_amount)
        
        return delay
        
    def _update_stats(self, records: List[RetryRecord], success: bool):
        """更新统计信息"""
        self.retry_history.extend(records)
        self.stats["total_retries"] += 1
        
        if success:
            self.stats["successful_retries"] += 1
        else:
            self.stats["failed_retries"] += 1
            
        # 更新平均尝试次数
        total = self.stats["total_retries"]
        current_avg = self.stats["avg_attempts"]
        new_attempts = len(records)
        self.stats["avg_attempts"] = (current_avg * (total - 1) + new_attempts) / total
        
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successful_retries"] / max(self.stats["total_retries"], 1)
            ),
            "recent_retries": [
                {
                    "attempt": r.attempt,
                    "reason": r.reason.value,
                    "delay": r.delay,
                    "success": r.success,
                    "error": r.error,
                    "timestamp": r.timestamp,
                }
                for r in self.retry_history[-10:]
            ],
        }
        
    def reset_stats(self):
        """重置统计"""
        self.retry_history.clear()
        self.stats = {
            "total_retries": 0,
            "successful_retries": 0,
            "failed_retries": 0,
            "avg_attempts": 0.0,
        }
        
    def configure(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if key in self.config:
                self.config[key] = value


# 便捷函数
async def retry_async(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    **kwargs,
) -> Any:
    """
    便捷的重试包装器
    
    用法：
        result = await retry_async(
            my_async_function,
            max_retries=5,
            base_delay=2.0,
        )
    """
    engine = RetryEngine({
        "max_retries": max_retries,
        "base_delay": base_delay,
    })
    
    result = await engine.execute_with_retry(func, **kwargs)
    
    if not result.success:
        raise Exception(f"Retry failed after {result.attempts} attempts: {result.final_error}")
        
    return result.final_result
