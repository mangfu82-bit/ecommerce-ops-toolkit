"""
工作流编排器
串联4层Agent：采集 → 融合 → 决策 → 执行
支持依赖链和审批队列
"""

import logging
import json
import time
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

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "agent_type": self.agent_type,
            "agent_name": self.agent_name,
            "status": self.status,
            "duration_sec": self.duration_sec,
            "error": self.error,
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

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "trigger": self.trigger,
            "status": self.status,
            "steps": [s.to_dict() for s in self.steps],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_duration": self.total_duration,
            "pending_approvals": self.pending_approvals,
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

    def register_collector(self, name: str, agent):
        self.collectors[name] = agent

    def register_fusion(self, name: str, agent):
        self.fusion_agents[name] = agent

    def register_decision(self, name: str, agent):
        self.decision_agents[name] = agent

    def register_execution(self, name: str, agent):
        self.execution_agents[name] = agent

    def run_full_cycle(self, keywords: List[str] = None, trigger: str = "manual") -> WorkflowRun:
        """执行完整工作流：采集 → 融合 → 决策 → 执行"""
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        run = WorkflowRun(run_id=run_id, trigger=trigger, started_at=datetime.now().isoformat())
        run.status = "running"
        logger.info(f"[编排器] 开始工作流 {run_id}")

        try:
            # 第1层：采集
            collect_outputs = {}
            for name, agent in self.collectors.items():
                step = WorkflowStep(name=f"采集-{name}", agent_type="collector", agent_name=name)
                step.status = "running"
                step.started_at = datetime.now().isoformat()
                try:
                    result = agent.run(keywords)
                    step.output_data = {"total": result.total, "new": result.new_count}
                    step.status = "done"
                    collect_outputs[name] = result
                except Exception as e:
                    step.status = "failed"
                    step.error = str(e)
                    logger.error(f"采集Agent {name} 失败: {e}")
                step.finished_at = datetime.now().isoformat()
                run.steps.append(step)

            # 第2层：融合
            fusion_outputs = {}
            for name, agent in self.fusion_agents.items():
                step = WorkflowStep(name=f"融合-{name}", agent_type="fusion", agent_name=name)
                step.status = "running"
                step.started_at = datetime.now().isoformat()
                try:
                    result = agent.analyze(collect_outputs)
                    step.output_data = {"count": len(result) if isinstance(result, list) else str(result)[:100]}
                    step.status = "done"
                    fusion_outputs[name] = result
                except Exception as e:
                    step.status = "failed"
                    step.error = str(e)
                step.finished_at = datetime.now().isoformat()
                run.steps.append(step)

            # 第3层：决策（有依赖链）
            decision_outputs = {}
            pending_approvals = []

            if "pricing" in self.decision_agents:
                step = WorkflowStep(name="决策-定价", agent_type="decision", agent_name="pricing")
                step.status = "running"
                step.started_at = datetime.now().isoformat()
                try:
                    pricing_results = self._run_pricing_batch(fusion_outputs)
                    step.output_data = {"count": len(pricing_results)}
                    step.status = "done"
                    decision_outputs["pricing"] = pricing_results
                    for pr in pricing_results:
                        if pr.get("needs_approval"):
                            pending_approvals.append({
                                "type": "pricing",
                                "sku_id": pr["sku_id"],
                                "recommended": pr["recommended"],
                            })
                except Exception as e:
                    step.status = "failed"
                    step.error = str(e)
                step.finished_at = datetime.now().isoformat()
                run.steps.append(step)

            if "supply" in self.decision_agents and "pricing" in decision_outputs:
                step = WorkflowStep(name="决策-供应链", agent_type="decision", agent_name="supply")
                step.status = "running"
                step.started_at = datetime.now().isoformat()
                try:
                    supply_results = self._run_supply_batch(decision_outputs["pricing"])
                    step.status = "done"
                    decision_outputs["supply"] = supply_results
                except Exception as e:
                    step.status = "failed"
                    step.error = str(e)
                step.finished_at = datetime.now().isoformat()
                run.steps.append(step)

            if "content" in self.decision_agents and "pricing" in decision_outputs:
                step = WorkflowStep(name="决策-内容", agent_type="decision", agent_name="content")
                step.status = "running"
                step.started_at = datetime.now().isoformat()
                try:
                    content_results = self._run_content_batch(decision_outputs)
                    step.status = "done"
                    decision_outputs["content"] = content_results
                except Exception as e:
                    step.status = "failed"
                    step.error = str(e)
                step.finished_at = datetime.now().isoformat()
                run.steps.append(step)

            # 第4层：执行
            if pending_approvals:
                run.status = "waiting_approval"
                run.pending_approvals = pending_approvals
                logger.info(f"[编排器] 等待审批: {len(pending_approvals)} 项")
            else:
                self._execute_decisions(decision_outputs, run)

            self._save_run(run)

        except Exception as e:
            run.status = "failed"
            logger.error(f"[编排器] 工作流异常: {e}")

        run.finished_at = datetime.now().isoformat()
        run.total_duration = (datetime.fromisoformat(run.finished_at) - datetime.fromisoformat(run.started_at)).total_seconds()
        return run

    def _run_pricing_batch(self, fusion_outputs):
        return []

    def _run_supply_batch(self, pricing_outputs):
        return []

    def _run_content_batch(self, decision_outputs):
        return []

    def _execute_decisions(self, decisions, run):
        for name, agent in self.execution_agents.items():
            step = WorkflowStep(name=f"执行-{name}", agent_type="execution", agent_name=name)
            step.status = "running"
            step.started_at = datetime.now().isoformat()
            try:
                result = agent.execute(decisions)
                step.status = "done"
            except Exception as e:
                step.status = "failed"
                step.error = str(e)
            step.finished_at = datetime.now().isoformat()
            run.steps.append(step)
        if run.status != "waiting_approval":
            run.status = "done"

    def _save_run(self, run):
        run_dir = self.data_dir / "runs"
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / f"{run.run_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(run.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"[编排器] 运行记录已保存: {path}")
