"""
llm_router.py - LLM统一路由层
支持多模型切换、fallback、重试、成本统计
"""
import asyncio
import time
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import os


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int
    duration: float
    cost: float
    success: bool
    error: Optional[str] = None


@dataclass
class ModelConfig:
    name: str
    provider: str
    api_key_env: str
    base_url: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    cost_per_1k_tokens: float = 0.01
    priority: int = 1  # 1=首选 2=备选 3=兜底


class LLMRouter:
    """
    LLM统一路由层
    
    功能：
    1. 多模型配置管理
    2. 自动fallback（主模型失败→备选→兜底）
    3. 智能重试（指数退避）
    4. 成本统计与预算控制
    5. 请求日志与审计
    """
    
    DEFAULT_MODELS = [
        ModelConfig(
            name="gpt-4o-mini",
            provider="openai",
            api_key_env="OPENAI_API_KEY",
            max_tokens=4096,
            temperature=0.7,
            cost_per_1k_tokens=0.00015,
            priority=1,
        ),
        ModelConfig(
            name="deepseek-chat",
            provider="deepseek",
            api_key_env="DEEPSEEK_API_KEY",
            base_url="https://api.deepseek.com/v1",
            max_tokens=4096,
            temperature=0.7,
            cost_per_1k_tokens=0.0001,
            priority=2,
        ),
        ModelConfig(
            name="gpt-3.5-turbo",
            provider="openai",
            api_key_env="OPENAI_API_KEY",
            max_tokens=4096,
            temperature=0.7,
            cost_per_1k_tokens=0.0005,
            priority=3,
        ),
    ]
    
    def __init__(self, models: Optional[List[ModelConfig]] = None, max_retries: int = 3):
        self.models = sorted(models or self.DEFAULT_MODELS, key=lambda m: m.priority)
        self.max_retries = max_retries
        self.call_history: List[Dict[str, Any]] = []
        self.total_cost = 0.0
        self.total_tokens = 0
        self.total_calls = 0
        self.failed_calls = 0
        
    async def call(
        self,
        prompt: str,
        system: Optional[str] = None,
        model_override: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        统一调用入口，自动fallback和重试
        
        Args:
            prompt: 用户提示词
            system: 系统提示词
            model_override: 强制使用指定模型
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            LLMResponse: 统一响应对象
        """
        start_time = time.time()
        
        # 确定使用的模型列表
        if model_override:
            models_to_try = [m for m in self.models if m.name == model_override]
            if not models_to_try:
                models_to_try = [self.models[0]]
        else:
            models_to_try = self.models
            
        # 尝试调用模型（带fallback）
        last_error = None
        for model in models_to_try:
            for attempt in range(self.max_retries):
                try:
                    response = await self._call_single_model(
                        model=model,
                        prompt=prompt,
                        system=system,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    
                    if response.success:
                        self._record_call(response, model, prompt, start_time)
                        return response
                        
                except Exception as e:
                    last_error = str(e)
                    await asyncio.sleep(2 ** attempt * 0.5)  # 指数退避
                    
        # 所有模型都失败
        self.failed_calls += 1
        return LLMResponse(
            content="",
            model="none",
            tokens_used=0,
            duration=time.time() - start_time,
            cost=0.0,
            success=False,
            error=f"All models failed. Last error: {last_error}",
        )
        
    async def _call_single_model(
        self,
        model: ModelConfig,
        prompt: str,
        system: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int],
    ) -> LLMResponse:
        """调用单个模型（实际API调用）"""
        start_time = time.time()
        
        # 获取API密钥
        api_key = os.getenv(model.api_key_env)
        if not api_key:
            raise ValueError(f"API key not found: {model.api_key_env}")
            
        # 构建请求
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model.name,
            "messages": messages,
            "temperature": temperature or model.temperature,
            "max_tokens": max_tokens or model.max_tokens,
        }
        
        # 选择base_url
        base_url = model.base_url or "https://api.openai.com/v1"
        url = f"{base_url}/chat/completions"
        
        # 发起HTTP请求（这里用模拟数据，实际需要httpx/aiohttp）
        # 实际项目中应该替换为真实的HTTP客户端调用
        try:
            # 模拟API调用
            await asyncio.sleep(0.5)  # 模拟网络延迟
            
            # 模拟响应（实际应从API获取）
            mock_content = self._generate_mock_response(prompt)
            mock_tokens = len(prompt.split()) + len(mock_content.split())
            
            duration = time.time() - start_time
            cost = (mock_tokens / 1000) * model.cost_per_1k_tokens
            
            return LLMResponse(
                content=mock_content,
                model=model.name,
                tokens_used=mock_tokens,
                duration=duration,
                cost=cost,
                success=True,
            )
            
        except Exception as e:
            raise RuntimeError(f"Model {model.name} failed: {e}")
            
    def _generate_mock_response(self, prompt: str) -> str:
        """生成模拟响应（用于测试）"""
        if "关键词" in prompt or "keyword" in prompt.lower():
            return '[{"keyword": "鲜花速递", "priority": 1, "angle": "核心词"}, {"keyword": "同城鲜花配送", "priority": 2, "angle": "场景词"}, {"keyword": "生日鲜花预订", "priority": 2, "angle": "场景词"}]'
        elif "聚类" in prompt or "cluster" in prompt.lower():
            return '{"clusters":[{"cluster_id":1,"name":"礼品鲜花","count":15,"avg_price":188.5,"platforms":["taobao","jd"]}],"graph":{"nodes":[],"edges":[]}}'
        elif "决策" in prompt or "decision" in prompt.lower():
            return '{"scores":[{"cluster_id":1,"cluster_name":"礼品鲜花","dimensions":{"hotness":8.5,"competition":7.2,"profit":6.8},"overall_score":7.5}],"top3":[1],"action":"建议主攻礼品鲜花市场"}'
        elif "方案" in prompt or "plan" in prompt.lower():
            return '{"summary":"建议聚焦礼品鲜花，主打同城配送","objectives":["提升转化率","降低CPC"],"phases":[{"phase":1,"name":"测试期","duration":"1-2周","actions":["上架5款测试款"],"kpis":["点击率>3%"]}],"risks":["竞争激烈"]}'
        elif "自评" in prompt or "review" in prompt.lower():
            return '{"self_score":8.0,"strengths":["并行采集效率高"],"weaknesses":["缺少真实爬虫"],"improvements":["接入真实API"]}'
        else:
            return '{"status":"ok","data":[]}'
            
    def _record_call(self, response: LLMResponse, model: ModelConfig, prompt: str, start_time: float):
        """记录调用日志"""
        self.total_calls += 1
        self.total_cost += response.cost
        self.total_tokens += response.tokens_used
        
        self.call_history.append({
            "timestamp": datetime.now().isoformat(),
            "model": model.name,
            "provider": model.provider,
            "tokens": response.tokens_used,
            "cost": response.cost,
            "duration": response.duration,
            "prompt_length": len(prompt),
            "success": response.success,
        })
        
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_calls": self.total_calls,
            "failed_calls": self.failed_calls,
            "success_rate": (self.total_calls - self.failed_calls) / max(self.total_calls, 1),
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "avg_cost_per_call": self.total_cost / max(self.total_calls, 1),
            "avg_tokens_per_call": self.total_tokens / max(self.total_calls, 1),
            "models_available": [m.name for m in self.models],
        }
        
    def get_recent_calls(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的调用记录"""
        return self.call_history[-limit:]
        
    def reset_stats(self):
        """重置统计信息"""
        self.call_history.clear()
        self.total_cost = 0.0
        self.total_tokens = 0
        self.total_calls = 0
        self.failed_calls = 0
