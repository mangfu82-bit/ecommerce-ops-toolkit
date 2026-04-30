"""
工作流编排器
串联4层Agent：采集 → 融合 → 决策 → 执行
支持依赖链和审批队列
"""

import logging
import json
import time
import random
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class WorkflowStep:
    """工作流单步"""
    name: str
    agent_type: str       # collector / fusion / decision / execution
    agent_name: str
    status: str = "pending"  # pending / running / done / failed / waiting_approval
    input_data: dict = field(default_factory=dict)
    output_data: dict = field(default_factory=dict)
    started_at: str = ""
    finished_at: str = ""
    duration_sec: float = 0
    error: str = ""
    retry_count: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "agent_type": self.agent_type,
            "agent_name": self.agent_name,
            "status": self.status,
            "duration_sec": round(self.duration_sec, 2),
            "error": self.error,
            "retry_count": self.retry_count,
        }


@dataclass
class WorkflowRun:
    """一次完整的工作流执行"""
    run_id: str
    trigger: str          # manual / scheduled / event
    steps: List[WorkflowStep] = field(default_factory=list)
    status: str = "pending"  # pending / running / done / failed / waiting_approval
    started_at: str = ""
    finished_at: str = ""
    total_duration: float = 0
    pending_approvals: List[dict] = field(default_factory=list)
    success_count: int = 0
    failed_count: int = 0

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "trigger": self.trigger,
            "status": self.status,
            "steps": [s.to_dict() for s in self.steps],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_duration": round(self.total_duration, 2),
            "pending_approvals": self.pending_approvals,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
        }


class Orchestrator:
    """工作流编排器"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.data_dir = Path(self.config.get("data_dir", "data"))
        self.collectors = {}
        self.fusion_agents = {}
        self.decision_agents = {}
        self.execution_agents = {}
        self.max_retries = self.config.get("max_retries", 2)
        self.step_timeout = self.config.get("step_timeout", 30)
        logger.info(f"[编排器] 初始化完成，数据目录: {self.data_dir}")

    def register_collector(self, name: str, agent):
        self.collectors[name] = agent
        logger.info(f"[编排器] 注册采集Agent: {name}")

    def register_fusion(self, name: str, agent):
        self.fusion_agents[name] = agent
        logger.info(f"[编排器] 注册融合Agent: {name}")

    def register_decision(self, name: str, agent):
        self.decision_agents[name] = agent
        logger.info(f"[编排器] 注册决策Agent: {name}")

    def register_execution(self, name: str, agent):
        self.execution_agents[name] = agent
        logger.info(f"[编排器] 注册执行Agent: {name}")

    def run_full_cycle(self, keywords: List[str] = None, trigger: str = "manual") -> WorkflowRun:
        """执行完整工作流：采集 → 融合 → 决策 → 执行"""
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        run = WorkflowRun(run_id=run_id, trigger=trigger, started_at=datetime.now().isoformat())
        run.status = "running"
        logger.info(f"[编排器] ========== 开始工作流 {run_id} ==========")
        logger.info(f"[编排器] 关键词: {keywords or '默认配置'}")
        logger.info(f"[编排器] 触发方式: {trigger}")

        try:
            # 第1层：采集
            collect_outputs = {}
            logger.info(f"[编排器] [第1层] 开始采集，共 {len(self.collectors)} 个Agent")
            for name, agent in self.collectors.items():
                step = WorkflowStep(name=f"采集-{name}", agent_type="collector", agent_name=name)
                step.status = "running"
                step.started_at = datetime.now().isoformat()
                logger.info(f"[编排器] 执行 {step.name}...")
                success = False
                for attempt in range(self.max_retries + 1):
                    try:
                        if attempt > 0:
                            step.retry_count += 1
                            logger.warning(f"[编排器] {step.name} 第 {attempt} 次重试...")
                            time.sleep(2 ** attempt)  # 指数退避
                        result = agent.run(keywords)
                        step.output_data = {"total": result.total, "new": result.new_count}
                        step.status = "done"
                        run.success_count += 1
                        success = True
                        logger.info(f"[编排器] {step.name} 完成: 总数 {result.total}, 新增 {result.new_count}")
                        break
                    except Exception as e:
                        step.error = str(e)
                        logger.error(f"[编排器] {step.name} 失败 (尝试 {attempt + 1}/{self.max_retries + 1}): {e}")
                        if attempt == self.max_retries:
                            step.status = "failed"
                            run.failed_count += 1
                            logger.error(f"[编排器] {step.name} 最终失败")
                step.finished_at = datetime.now().isoformat()
                step.duration_sec = (datetime.fromisoformat(step.finished_at) - datetime.fromisoformat(step.started_at)).total_seconds()
                run.steps.append(step)
                if success:
                    collect_outputs[name] = result

            # 第2层：融合
            fusion_outputs = {}
            logger.info(f"[编排器] [第2层] 开始融合，共 {len(self.fusion_agents)} 个Agent")
            for name, agent in self.fusion_agents.items():
                step = WorkflowStep(name=f"融合-{name}", agent_type="fusion", agent_name=name)
                step.status = "running"
                step.started_at = datetime.now().isoformat()
                logger.info(f"[编排器] 执行 {step.name}...")
                try:
                    result = agent.analyze(collect_outputs)
                    count = len(result) if isinstance(result, list) else 0
                    step.output_data = {"count": count, "preview": str(result)[:200]}
                    step.status = "done"
                    run.success_count += 1
                    fusion_outputs[name] = result
                    logger.info(f"[编排器] {step.name} 完成: 处理 {count} 条数据")
                except Exception as e:
                    step.status = "failed"
                    step.error = str(e)
                    run.failed_count += 1
                    logger.error(f"[编排器] {step.name} 失败: {e}")
                step.finished_at = datetime.now().isoformat()
                step.duration_sec = (datetime.fromisoformat(step.finished_at) - datetime.fromisoformat(step.started_at)).total_seconds()
                run.steps.append(step)

            # 第3层：决策（有依赖链）
            decision_outputs = {}
            pending_approvals = []
            logger.info(f"[编排器] [第3层] 开始决策，共 {len(self.decision_agents)} 个Agent")

            if "pricing" in self.decision_agents:
                step = WorkflowStep(name="决策-定价", agent_type="decision", agent_name="pricing")
                step.status = "running"
                step.started_at = datetime.now().isoformat()
                logger.info(f"[编排器] 执行 {step.name}...")
                try:
                    pricing_results = self._run_pricing_batch(fusion_outputs)
                    step.output_data = {"count": len(pricing_results), "sample": pricing_results[0] if pricing_results else {}}
                    step.status = "done"
                    run.success_count += 1
                    decision_outputs["pricing"] = pricing_results
                    approvals = [pr for pr in pricing_results if pr.get("needs_approval")]
                    pending_approvals.extend([{
                        "type": "pricing",
                        "sku_id": pr["sku_id"],
                        "product": pr.get("product", ""),
                        "current_price": pr.get("current_price", 0),
                        "recommended": pr["recommended"],
                        "reason": pr.get("reason", ""),
                    } for pr in approvals])
                    logger.info(f"[编排器] {step.name} 完成: {len(pricing_results)} 个SKU，需审批 {len(approvals)} 个")
                except Exception as e:
                    step.status = "failed"
                    step.error = str(e)
                    run.failed_count += 1
                    logger.error(f"[编排器] {step.name} 失败: {e}")
                step.finished_at = datetime.now().isoformat()
                step.duration_sec = (datetime.fromisoformat(step.finished_at) - datetime.fromisoformat(step.started_at)).total_seconds()
                run.steps.append(step)

            if "supply" in self.decision_agents and "pricing" in decision_outputs:
                step = WorkflowStep(name="决策-供应链", agent_type="decision", agent_name="supply")
                step.status = "running"
                step.started_at = datetime.now().isoformat()
                logger.info(f"[编排器] 执行 {step.name}...")
                try:
                    supply_results = self._run_supply_batch(decision_outputs["pricing"])
                    step.output_data = {"count": len(supply_results)}
                    step.status = "done"
                    run.success_count += 1
                    decision_outputs["supply"] = supply_results
                    logger.info(f"[编排器] {step.name} 完成: {len(supply_results)} 条建议")
                except Exception as e:
                    step.status = "failed"
                    step.error = str(e)
                    run.failed_count += 1
                    logger.error(f"[编排器] {step.name} 失败: {e}")
                step.finished_at = datetime.now().isoformat()
                step.duration_sec = (datetime.fromisoformat(step.finished_at) - datetime.fromisoformat(step.started_at)).total_seconds()
                run.steps.append(step)

            if "content" in self.decision_agents and "pricing" in decision_outputs:
                step = WorkflowStep(name="决策-内容", agent_type="decision", agent_name="content")
                step.status = "running"
                step.started_at = datetime.now().isoformat()
                logger.info(f"[编排器] 执行 {step.name}...")
                try:
                    content_results = self._run_content_batch(decision_outputs)
                    step.output_data = {"count": len(content_results)}
                    step.status = "done"
                    run.success_count += 1
                    decision_outputs["content"] = content_results
                    logger.info(f"[编排器] {step.name} 完成: 生成 {len(content_results)} 条内容")
                except Exception as e:
                    step.status = "failed"
                    step.error = str(e)
                    run.failed_count += 1
                    logger.error(f"[编排器] {step.name} 失败: {e}")
                step.finished_at = datetime.now().isoformat()
                step.duration_sec = (datetime.fromisoformat(step.finished_at) - datetime.fromisoformat(step.started_at)).total_seconds()
                run.steps.append(step)

            # 第4层：执行
            if pending_approvals:
                run.status = "waiting_approval"
                run.pending_approvals = pending_approvals
                logger.warning(f"[编排器] [第4层] 等待审批: {len(pending_approvals)} 项")
                logger.warning(f"[编排器] 审批项示例: {pending_approvals[0] if pending_approvals else '无'}")
            else:
                logger.info(f"[编排器] [第4层] 无需审批，开始执行")
                self._execute_decisions(decision_outputs, run)

            self._save_run(run)
            logger.info(f"[编排器] 工作流 {run_id} 完成: 成功 {run.success_count}, 失败 {run.failed_count}")

        except Exception as e:
            run.status = "failed"
            run.failed_count += 1
            logger.error(f"[编排器] 工作流异常: {e}", exc_info=True)

        run.finished_at = datetime.now().isoformat()
        run.total_duration = (datetime.fromisoformat(run.finished_at) - datetime.fromisoformat(run.started_at)).total_seconds()
        logger.info(f"[编排器] ========== 工作流结束 {run_id} ==========")
        logger.info(f"[编排器] 总耗时: {run.total_duration:.2f}秒")
        return run

    def _run_pricing_batch(self, fusion_outputs):
        """模拟定价决策输出"""
        logger.debug("[定价] 模拟生成定价建议...")
        results = []
        skus = [
            {"sku_id": "TH-ROSE-001", "product": "红玫瑰（19枝）", "current_price": 68.0},
            {"sku_id": "TH-ROSE-002", "product": "红玫瑰（33枝）", "current_price": 128.0},
            {"sku_id": "TH-LILY-001", "product": "百合花束", "current_price": 88.0},
            {"sku_id": "TH-SUNFLOWER-001", "product": "向日葵束", "current_price": 58.0},
            {"sku_id": "TH-MIX-001", "product": "混搭花束", "current_price": 78.0},
        ]
        for sku in skus:
            change = random.uniform(-0.15, 0.20)
            recommended = round(sku["current_price"] * (1 + change), 2)
            results.append({
                "sku_id": sku["sku_id"],
                "product": sku["product"],
                "current_price": sku["current_price"],
                "recommended": recommended,
                "change_pct": round(change * 100, 1),
                "reason": random.choice(["竞品调价", "节日需求上升", "库存充足", "天气影响供应"]),
                "needs_approval": abs(change) > 0.10,
            })
        return results

    def _run_supply_batch(self, pricing_outputs):
        """模拟供应链决策输出"""
        logger.debug("[供应链] 模拟生成供应链建议...")
        return [{"sku_id": p["sku_id"], "action": "补货" if p["change_pct"] > 5 else "维持", "qty": random.randint(50, 200)} for p in pricing_outputs]

    def _run_content_batch(self, decision_outputs):
        """模拟内容决策输出"""
        logger.debug("[内容] 模拟生成内容建议...")
        return [{"type": "标题", "content": f"【限时特惠】{p['product']}仅需{p['recommended']}元起", "sku_id": p["sku_id"]} for p in decision_outputs.get("pricing", [])]

    def _execute_decisions(self, decisions, run):
        """执行决策结果"""
        logger.info(f"[编排器] 开始执行，共 {len(self.execution_agents)} 个执行Agent")
        for name, agent in self.execution_agents.items():
            step = WorkflowStep(name=f"执行-{name}", agent_type="execution", agent_name=name)
            step.status = "running"
            step.started_at = datetime.now().isoformat()
            logger.info(f"[编排器] 执行 {step.name}...")
            try:
                result = agent.execute(decisions)
                step.output_data = {"result": "ok", "detail": str(result)[:100]}
                step.status = "done"
                run.success_count += 1
                logger.info(f"[编排器] {step.name} 完成")
            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                run.failed_count += 1
                logger.error(f"[编排器] {step.name} 失败: {e}")
            step.finished_at = datetime.now().isoformat()
            step.duration_sec = (datetime.fromisoformat(step.finished_at) - datetime.fromisoformat(step.started_at)).total_seconds()
            run.steps.append(step)
        if run.status != "waiting_approval":
            run.status = "done"

    def _save_run(self, run):
        """保存运行记录"""
        run_dir = self.data_dir / "runs"
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / f"{run.run_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(run.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"[编排器] 运行记录已保存: {path}")

    def run_demo(self) -> dict:
        """运行演示：模拟一次完整工作流，生成运行记录"""
        logger.info("[编排器] 开始演示运行...")
        # 模拟关键词
        keywords = ["鲜花价格", "玫瑰今日价", "美团闪购鲜花", "淘宝鲜花"]
        # 模拟采集输出
        mock_collect = type("Result", (), {"total": 24, "new_count": 18})()
        # 直接调用保存逻辑，生成演示运行记录
        run_id = f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        demo_run = WorkflowRun(run_id=run_id, trigger="demo")
        demo_run.started_at = datetime.now().isoformat()
        demo_run.steps = [
            WorkflowStep(name="采集-淘宝", agent_type="collector", agent_name="taobao", status="done", output_data={"total": 8, "new": 6}, started_at=demo_run.started_at, finished_at=demo_run.started_at, duration_sec=1.23),
            WorkflowStep(name="采集-美团", agent_type="collector", agent_name="meituan", status="done", output_data={"total": 7, "new": 5}, started_at=demo_run.started_at, finished_at=demo_run.started_at, duration_sec=0.98),
            WorkflowStep(name="采集-京东", agent_type="collector", agent_name="jd", status="done", output_data={"total": 5, "new": 4}, started_at=demo_run.started_at, finished_at=demo_run.started_at, duration_sec=1.45),
            WorkflowStep(name="采集-抖音", agent_type="collector", agent_name="douyin", status="done", output_data={"total": 4, "new": 3}, started_at=demo_run.started_at, finished_at=demo_run.started_at, duration_sec=2.10),
            WorkflowStep(name="融合-市场情报", agent_type="fusion", agent_name="market_intel", status="done", output_data={"count": 24}, started_at=demo_run.started_at, finished_at=demo_run.started_at, duration_sec=3.20),
            WorkflowStep(name="融合-关联分析", agent_type="fusion", agent_name="correlator", status="done", output_data={"count": 12}, started_at=demo_run.started_at, finished_at=demo_run.started_at, duration_sec=1.80),
            WorkflowStep(name="决策-定价", agent_type="decision", agent_name="pricing", status="done", output_data={"count": 5}, started_at=demo_run.started_at, finished_at=demo_run.started_at, duration_sec=0.50),
            WorkflowStep(name="决策-供应链", agent_type="decision", agent_name="supply", status="done", output_data={"count": 5}, started_at=demo_run.started_at, finished_at=demo_run.started_at, duration_sec=0.30),
            WorkflowStep(name="决策-内容", agent_type="decision", agent_name="content", status="done", output_data={"count": 5}, started_at=demo_run.started_at, finished_at=demo_run.started_at, duration_sec=0.40),
            WorkflowStep(name="执行-executor", agent_type="execution", agent_name="executor", status="done", output_data={"result": "ok"}, started_at=demo_run.started_at, finished_at=demo_run.started_at, duration_sec=0.20),
        ]
        demo_run.success_count = 10
        demo_run.failed_count = 0
        demo_run.status = "done"
        demo_run.finished_at = datetime.now().isoformat()
        demo_run.total_duration = 12.16
        self._save_run(demo_run)
        logger.info(f"[编排器] 演示运行完成，记录已保存: run_id={run_id}")
        return demo_run.to_dict()
