"""workflow_engine.py - workflow state machine + stage routing engine"""
import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class WorkflowStage(Enum):
    """8 workflow stages"""
    TRIGGER = "trigger"
    COLLECTION = "collection"
    CLEANING = "cleaning"
    FUSION = "fusion"
    DECISION = "decision"
    EXECUTION = "execution"
    APPROVAL = "approval"
    REVIEW = "review"


class StageStatus(Enum):
    """Stage execution status"""
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageResult:
    """Result of a single stage execution"""
    stage: WorkflowStage
    status: StageStatus
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


@dataclass
class WorkflowContext:
    """Shared context passed through all workflow stages"""
    run_id: str
    keywords: List[str]
    stage_results: Dict[WorkflowStage, StageResult] = field(default_factory=dict)
    shared_data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_result(self, stage: WorkflowStage) -> Optional[StageResult]:
        return self.stage_results.get(stage)

    def set_result(self, result: StageResult):
        self.stage_results[result.stage] = result

    def is_completed(self, stage: WorkflowStage) -> bool:
        r = self.get_result(stage)
        return r is not None and r.status == StageStatus.DONE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "keywords": self.keywords,
            "stages": {k.value: v.to_dict() for k, v in self.stage_results.items()},
            "shared_data": self.shared_data,
            "errors": self.errors,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


class WorkflowEngine:
    """State machine workflow engine - routes and manages 8-stage workflow execution"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.stage_order = [
            WorkflowStage.TRIGGER,
            WorkflowStage.COLLECTION,
            WorkflowStage.CLEANING,
            WorkflowStage.FUSION,
            WorkflowStage.DECISION,
            WorkflowStage.EXECUTION,
            WorkflowStage.APPROVAL,
            WorkflowStage.REVIEW,
        ]
        self._stage_handlers: Dict[WorkflowStage, callable] = {}
        logger.info(f"WorkflowEngine initialized, {len(self.stage_order)} stages")

    def register_handler(self, stage: WorkflowStage, handler: callable):
        """Register handler for a specific stage"""
        self._stage_handlers[stage] = handler
        logger.info(f"Registered handler for stage: {stage.value}")

    async def execute_stage(
        self, context: WorkflowContext, stage: WorkflowStage
    ) -> StageResult:
        """Execute a single stage"""
        started = datetime.now()
        result = StageResult(stage=stage, status=StageStatus.RUNNING, started_at=started)

        handler = self._stage_handlers.get(stage)
        if not handler:
            result.status = StageStatus.SKIPPED
            result.metadata["reason"] = f"No handler registered for {stage.value}"
            logger.warning(f"No handler for {stage.value}, skipping")
        else:
            try:
                if asyncio.iscoroutinefunction(handler):
                    output = await handler(context)
                else:
                    output = handler(context)
                result.status = StageStatus.DONE
                result.output = output
                context.set_result(result)
                logger.info(f"Stage {stage.value} completed")
            except Exception as e:
                result.status = StageStatus.FAILED
                result.error = str(e)
                result.output = {}
                context.errors.append(str(e))
                logger.error(f"Stage {stage.value} failed: {e}")

        result.finished_at = datetime.now()
        result.duration_ms = (result.finished_at - started).total_seconds() * 1000
        return result

    async def run(self, context: WorkflowContext) -> WorkflowContext:
        """Run all 8 stages sequentially"""
        logger.info(f"Starting workflow run: {context.run_id}")
        context.metadata["started_at"] = datetime.now().isoformat()

        for stage in self.stage_order:
            # Check dependency: only run if dependencies are met
            if stage == WorkflowStage.COLLECTION:
                # TRIGGER must be done
                if not context.is_completed(WorkflowStage.TRIGGER):
                    logger.warning("TRIGGER not completed, skipping COLLECTION")
                    continue
            elif stage == WorkflowStage.CLEANING:
                if not context.is_completed(WorkflowStage.COLLECTION):
                    continue
            elif stage == WorkflowStage.FUSION:
                if not context.is_completed(WorkflowStage.CLEANING):
                    continue
            elif stage == WorkflowStage.DECISION:
                if not context.is_completed(WorkflowStage.FUSION):
                    continue
            elif stage == WorkflowStage.EXECUTION:
                if not context.is_completed(WorkflowStage.DECISION):
                    continue
            elif stage == WorkflowStage.APPROVAL:
                if not context.is_completed(WorkflowStage.EXECUTION):
                    continue

            await self.execute_stage(context, stage)

            # Stop on critical failure
            stage_result = context.get_result(stage)
            if stage_result and stage_result.status == StageStatus.FAILED:
                if stage.value in ["COLLECTION", "FUSION", "DECISION"]:
                    logger.error(f"Critical stage {stage.value} failed, stopping workflow")
                    break

        context.metadata["finished_at"] = datetime.now().isoformat()
        logger.info(f"Workflow run {context.run_id} completed")
        return context

    def get_status(self, context: WorkflowContext) -> Dict[str, Any]:
        """Get workflow status summary"""
        completed = sum(
            1 for r in context.stage_results.values()
            if r.status == StageStatus.DONE
        )
        total = len(self.stage_order)
        return {
            "run_id": context.run_id,
            "progress": f"{completed}/{total}",
            "percentage": int(completed / total * 100),
            "stages": {
                stage.value: context.stage_results[stage].status.value
                if stage in context.stage_results else "pending"
                for stage in self.stage_order
            },
        }