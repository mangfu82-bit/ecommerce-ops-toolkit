"""
Human-in-the-loop审批队列
决策Agent输出先到这里，运营确认后才执行
"""

import json
import logging
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ApprovalQueue:
    """审批队列管理"""

    def __init__(self, queue_path: str = "data/approval_queue.json"):
        self.queue_path = queue_path
        self.queue: List[Dict] = []
        self._load()

    def _load(self):
        p = Path(self.queue_path)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                self.queue = json.load(f)

    def _save(self):
        Path(self.queue_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.queue_path, "w", encoding="utf-8") as f:
            json.dump(self.queue, f, ensure_ascii=False, indent=2)

    def submit(self, decision: Dict) -> str:
        """提交决策到审批队列"""
        decision_id = f"D-{len(self.queue)+1:04d}"
        decision["id"] = decision_id
        decision["status"] = "pending"
        self.queue.append(decision)
        self._save()
        logger.info(f"[ApprovalQueue] 新决策 {decision_id}: {decision.get('action')}")
        return decision_id

    def approve(self, decision_id: str, approver: str = "operator") -> bool:
        for d in self.queue:
            if d["id"] == decision_id:
                d["status"] = "approved"
                d["approved_by"] = approver
                self._save()
                logger.info(f"[ApprovalQueue] {decision_id} 已审批")
                return True
        return False

    def reject(self, decision_id: str, reason: str = "") -> bool:
        for d in self.queue:
            if d["id"] == decision_id:
                d["status"] = "rejected"
                d["reject_reason"] = reason
                self._save()
                return True
        return False

    def get_pending(self) -> List[Dict]:
        return [d for d in self.queue if d["status"] == "pending"]
