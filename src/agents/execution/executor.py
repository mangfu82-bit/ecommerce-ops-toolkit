"""
执行Agent - LLM驱动的智能执行引擎
支持多渠道执行、自动化运营、效果追踪、反馈闭环
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import random

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"
    CANCELLED = "cancelled"


class ActionType(Enum):
    """动作类型"""
    PRICE_ADJUST = "price_adjust"       # 调价
    LISTING = "listing"                 # 上架
    DELISTING = "delisting"             # 下架
    PROMOTION = "promotion"             # 促销
    INVENTORY = "inventory"             # 库存调整
    LISTING_OPTIMIZE = "listing_opt"    # 商品优化
    AD_BID = "ad_bid"                   # 广告出价
    FOLLOW = "follow"                   # 关注竞品
    ALERT = "alert"                     # 告警通知


@dataclass
class ExecutionTask:
    """执行任务"""
    task_id: str
    action_type: ActionType
    platform: str
    target_id: str  # 商品ID/店铺ID等
    parameters: Dict[str, Any]
    priority: int = 5  # 1-10, 1最高
    status: ExecutionStatus = ExecutionStatus.PENDING
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    result: Optional[Dict] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    llm_decision: Optional[str] = None
    approval_required: bool = False
    approved_by: Optional[str] = None


@dataclass
class ExecutionReport:
    """执行报告"""
    report_id: str
    period: str
    total_tasks: int
    success_count: int
    failed_count: int
    success_rate: float
    avg_execution_time: float
    actions_breakdown: Dict[str, int]
    platforms_breakdown: Dict[str, int]
    errors: List[str]
    recommendations: List[str]


class ExecutionAgent:
    """LLM驱动的智能执行Agent"""
    
    def __init__(self, llm_client=None, config: Optional[Dict] = None):
        self.llm = llm_client
        self.config = config or {}
        
        # 执行配置
        self.max_concurrent = self.config.get("max_concurrent", 5)
        self.default_timeout = self.config.get("timeout", 60)
        self.auto_retry = self.config.get("auto_retry", True)
        
        # 任务队列
        self.task_queue: List[ExecutionTask] = []
        self.running_tasks: Dict[str, ExecutionTask] = {}
        self.completed_tasks: List[ExecutionTask] = []
        
        # 平台API配置
        self.platform_apis = {
            "taobao": {"enabled": True, "rate_limit": 100},
            "meituan": {"enabled": True, "rate_limit": 50},
            "jd": {"enabled": True, "rate_limit": 80},
            "douyin": {"enabled": True, "rate_limit": 60},
        }
        
        # 统计
        self.stats = {
            "total_executed": 0,
            "success_rate": 0.0,
            "avg_time": 0.0,
        }
    
    async def execute(
        self,
        decisions: List[Dict],
        use_llm: bool = True
    ) -> List[ExecutionTask]:
        """
        执行决策
        
        Args:
            decisions: 决策列表（来自决策层）
            use_llm: 是否使用LLM生成执行方案
            
        Returns:
            执行任务列表
        """
        # 1. 转换决策为任务
        tasks = []
        for decision in decisions:
            task = self._create_task_from_decision(decision)
            if task:
                tasks.append(task)
        
        # 2. LLM优化执行顺序
        if use_llm and self.llm:
            tasks = await self._optimize_execution_order_with_llm(tasks)
        
        # 3. 加入队列
        self.task_queue.extend(tasks)
        
        # 4. 并行执行
        results = await self._execute_parallel(use_llm)
        
        # 5. 更新统计
        self._update_stats(results)
        
        return results
    
    def _create_task_from_decision(self, decision: Dict) -> Optional[ExecutionTask]:
        """从决策创建任务"""
        action_type_str = decision.get("action")
        
        try:
            action_type = ActionType(action_type_str)
        except ValueError:
            logger.warning(f"未知动作类型: {action_type_str}")
            return None
        
        task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}"
        
        return ExecutionTask(
            task_id=task_id,
            action_type=action_type,
            platform=decision.get("platform", "unknown"),
            target_id=decision.get("target_id", ""),
            parameters=decision.get("parameters", {}),
            priority=decision.get("priority", 5),
            approval_required=decision.get("approval_required", False),
            created_at=datetime.now().isoformat(),
        )
    
    async def _optimize_execution_order_with_llm(
        self,
        tasks: List[ExecutionTask]
    ) -> List[ExecutionTask]:
        """LLM优化执行顺序"""
        if len(tasks) < 3:
            return tasks
        
        task_summaries = [
            f"{t.task_id}: {t.action_type.value} on {t.platform} (priority={t.priority})"
            for t in tasks[:10]
        ]
        
        prompt = f"""
作为电商运营执行专家，请优化以下任务的执行顺序：

{chr(10).join(task_summaries)}

考虑因素：
1. 优先级（priority越小越优先）
2. 平台负载均衡
3. 依赖关系（如库存调整应在促销前）
4. 风险控制（高风险操作延迟执行）

返回优化后的task_id执行顺序，每行一个。
"""
        
        try:
            response = await self.llm.complete(prompt, temperature=0.3)
            
            # 解析顺序
            ordered_ids = []
            for line in response.strip().split('\n'):
                tid = line.strip()
                if tid.startswith('task_'):
                    ordered_ids.append(tid)
            
            # 重排任务
            if ordered_ids:
                task_map = {t.task_id: t for t in tasks}
                ordered_tasks = [task_map[tid] for tid in ordered_ids if tid in task_map]
                # 添加未在响应中的任务
                remaining = [t for t in tasks if t.task_id not in ordered_ids]
                return ordered_tasks + remaining
            
            return tasks
            
        except Exception as e:
            logger.error(f"LLM执行优化失败: {e}")
            return tasks
    
    async def _execute_parallel(
        self,
        use_llm: bool
    ) -> List[ExecutionTask]:
        """并行执行任务"""
        results = []
        
        while self.task_queue:
            # 取出一批任务
            batch = []
            while len(batch) < self.max_concurrent and self.task_queue:
                batch.append(self.task_queue.pop(0))
            
            if not batch:
                break
            
            # 并行执行
            tasks = [
                self._execute_single_task(task, use_llm)
                for task in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for task, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    task.status = ExecutionStatus.FAILED
                    task.error = str(result)
                
                self.completed_tasks.append(task)
                results.append(task)
        
        return results
    
    async def _execute_single_task(
        self,
        task: ExecutionTask,
        use_llm: bool
    ) -> ExecutionTask:
        """执行单个任务"""
        task.status = ExecutionStatus.RUNNING
        task.started_at = datetime.now().isoformat()
        
        self.running_tasks[task.task_id] = task
        
        try:
            # LLM生成执行方案
            if use_llm and self.llm:
                task.llm_decision = await self._get_llm_execution_plan(task)
            
            # 模拟执行
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            # 根据动作类型执行
            if task.action_type == ActionType.PRICE_ADJUST:
                result = await self._execute_price_adjust(task)
            elif task.action_type == ActionType.PROMOTION:
                result = await self._execute_promotion(task)
            elif task.action_type == ActionType.LISTING_OPTIMIZE:
                result = await self._execute_listing_optimize(task)
            else:
                result = await self._execute_generic(task)
            
            task.result = result
            task.status = ExecutionStatus.SUCCESS
            task.completed_at = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"任务执行失败 {task.task_id}: {e}")
            
            task.error = str(e)
            task.retry_count += 1
            
            if task.retry_count < task.max_retries and self.auto_retry:
                task.status = ExecutionStatus.RETRY
                self.task_queue.insert(0, task)  # 重新加入队列
            else:
                task.status = ExecutionStatus.FAILED
                task.completed_at = datetime.now().isoformat()
        
        finally:
            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]
        
        return task
    
    async def _get_llm_execution_plan(
        self,
        task: ExecutionTask
    ) -> str:
        """LLM生成执行方案"""
        prompt = f"""
作为电商运营执行专家，请为以下任务生成详细执行方案：

任务ID: {task.task_id}
动作类型: {task.action_type.value}
平台: {task.platform}
目标ID: {task.target_id}
参数: {json.dumps(task.parameters, ensure_ascii=False)}

请提供：
1. 具体执行步骤
2. 预期结果
3. 风险点
4. 回滚方案

以简洁文本格式返回。
"""
        
        try:
            return await self.llm.complete(prompt, temperature=0.4)
        except Exception as e:
            logger.error(f"LLM方案生成失败: {e}")
            return ""
    
    async def _execute_price_adjust(self, task: ExecutionTask) -> Dict:
        """执行调价"""
        new_price = task.parameters.get("new_price", 0)
        reason = task.parameters.get("reason", "")
        
        # 模拟API调用
        await asyncio.sleep(random.uniform(0.3, 0.8))
        
        return {
            "action": "price_adjusted",
            "product_id": task.target_id,
            "old_price": new_price * random.uniform(1.1, 1.3),
            "new_price": new_price,
            "reason": reason,
            "effective_time": datetime.now().isoformat(),
        }
    
    async def _execute_promotion(self, task: ExecutionTask) -> Dict:
        """执行促销"""
        promo_type = task.parameters.get("type", "discount")
        discount = task.parameters.get("discount", 10)
        
        await asyncio.sleep(random.uniform(0.3, 0.8))
        
        return {
            "action": "promotion_created",
            "product_id": task.target_id,
            "promo_type": promo_type,
            "discount": discount,
            "start_time": datetime.now().isoformat(),
            "end_time": (datetime.now() + timedelta(days=7)).isoformat(),
        }
    
    async def _execute_listing_optimize(self, task: ExecutionTask) -> Dict:
        """执行商品优化"""
        await asyncio.sleep(random.uniform(0.5, 1.0))
        
        return {
            "action": "listing_optimized",
            "product_id": task.target_id,
            "changes": [
                "标题已优化",
                "主图已更新",
                "详情页已完善",
            ],
        }
    
    async def _execute_generic(self, task: ExecutionTask) -> Dict:
        """通用执行"""
        await asyncio.sleep(random.uniform(0.2, 0.5))
        
        return {
            "action": task.action_type.value,
            "target": task.target_id,
            "status": "completed",
        }
    
    async def create_manual_task(
        self,
        action_type: str,
        platform: str,
        target_id: str,
        parameters: Dict,
        approval_required: bool = False
    ) -> ExecutionTask:
        """手动创建任务"""
        task = ExecutionTask(
            task_id=f"manual_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            action_type=ActionType(action_type),
            platform=platform,
            target_id=target_id,
            parameters=parameters,
            approval_required=approval_required,
            created_at=datetime.now().isoformat(),
        )
        
        self.task_queue.append(task)
        return task
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        # 从队列移除
        self.task_queue = [t for t in self.task_queue if t.task_id != task_id]
        
        # 取消运行中的任务
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.status = ExecutionStatus.CANCELLED
            del self.running_tasks[task_id]
            return True
        
        return False
    
    async def generate_report(
        self,
        period: str = "today",
        use_llm: bool = True
    ) -> ExecutionReport:
        """生成执行报告"""
        # 筛选时间段任务
        if period == "today":
            start_time = datetime.now().replace(hour=0, minute=0, second=0)
        elif period == "week":
            start_time = datetime.now() - timedelta(days=7)
        else:
            start_time = datetime.now() - timedelta(days=30)
        
        relevant_tasks = [
            t for t in self.completed_tasks
            if datetime.fromisoformat(t.completed_at) >= start_time
        ]
        
        # 统计
        total_tasks = len(relevant_tasks)
        success_count = sum(1 for t in relevant_tasks if t.status == ExecutionStatus.SUCCESS)
        failed_count = total_tasks - success_count
        
        # 动作分布
        actions_breakdown = {}
        for t in relevant_tasks:
            action = t.action_type.value
            actions_breakdown[action] = actions_breakdown.get(action, 0) + 1
        
        # 平台分布
        platforms_breakdown = {}
        for t in relevant_tasks:
            platforms_breakdown[t.platform] = platforms_breakdown.get(t.platform, 0) + 1
        
        # 错误列表
        errors = [t.error for t in relevant_tasks if t.error][:10]
        
        # LLM生成建议
        recommendations = []
        if use_llm and self.llm:
            recommendations = await self._get_llm_recommendations(
                total_tasks, success_count, errors
            )
        
        return ExecutionReport(
            report_id=f"report_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            period=period,
            total_tasks=total_tasks,
            success_count=success_count,
            failed_count=failed_count,
            success_rate=success_count / total_tasks if total_tasks > 0 else 0,
            avg_execution_time=0.0,
            actions_breakdown=actions_breakdown,
            platforms_breakdown=platforms_breakdown,
            errors=errors,
            recommendations=recommendations,
        )
    
    async def _get_llm_recommendations(
        self,
        total: int,
        success: int,
        errors: List[str]
    ) -> List[str]:
        """LLM生成优化建议"""
        prompt = f"""
基于以下执行数据，请提供优化建议：

总任务数: {total}
成功数: {success}
成功率: {success/total*100 if total > 0 else 0:.1f}%
主要错误: {', '.join(errors[:5]) if errors else '无'}

请提供3-5条具体可执行的优化建议。
"""
        
        try:
            response = await self.llm.complete(prompt, temperature=0.5)
            
            recommendations = []
            for line in response.strip().split('\n'):
                if line.strip() and len(line) > 5:
                    recommendations.append(line.strip())
            
            return recommendations[:5]
            
        except Exception as e:
            logger.error(f"LLM建议生成失败: {e}")
            return ["增加重试次数", "优化API调用频率", "加强异常处理"]
    
    def _update_stats(self, tasks: List[ExecutionTask]):
        """更新统计"""
        if not tasks:
            return
        
        self.stats["total_executed"] += len(tasks)
        
        success = sum(1 for t in tasks if t.status == ExecutionStatus.SUCCESS)
        self.stats["success_rate"] = success / len(tasks)
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            "pending_tasks": len(self.task_queue),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
        }


# 简化接口
async def execute_decisions(
    decisions: List[Dict],
    llm_client=None
) -> List[Dict]:
    """简化的执行接口"""
    agent = ExecutionAgent(llm_client=llm_client)
    tasks = await agent.execute(decisions, use_llm=bool(llm_client))
    return [
        {
            "task_id": t.task_id,
            "status": t.status.value,
            "result": t.result,
        }
        for t in tasks
    ]
