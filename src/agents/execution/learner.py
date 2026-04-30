"""learner.py - LLM-powered self-learning and feedback loop"""
import json, logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
logger = logging.getLogger(__name__)

@dataclass
class LearningRecord:
    """Single learning event"""
    decision_id: str
    decision_type: str
    context: Dict[str, Any]
    recommended_action: Dict[str, Any]
    actual_result: Optional[Dict[str, Any]]
    outcome: str  # success / failure / pending
    feedback: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "decision_type": self.decision_type,
            "context": self.context,
            "recommended_action": self.recommended_action,
            "actual_result": self.actual_result,
            "outcome": self.outcome,
            "feedback": self.feedback,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

class Learner:
    """Self-learning engine - learns from decision outcomes, updates strategy"""

    def __init__(self, db_path: str = "data/learner_db.jsonl"):
        self.db_path = db_path
        self.records: List[LearningRecord] = []
        self._strategy_weights: Dict[str, float] = {
            "price_boost_on_holiday": 1.2,
            "stock_up_before_promotion": 1.3,
            "content_refresh_weekly": 1.1,
            "competitor_follow_pricing": 0.9,
        }
        self._load()

    def _load(self):
        """Load historical records"""
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        d = json.loads(line)
                        self.records.append(LearningRecord(**d))
            logger.info(f"Learner loaded {len(self.records)} historical records")
        except FileNotFoundError:
            logger.info("No learner DB found, starting fresh")

    def record_decision(self, decision: Dict[str, Any], result: Optional[Dict[str, Any]] = None):
        """Record a decision + its outcome"""
        rec = LearningRecord(
            decision_id=decision.get("decision_id", ""),
            decision_type=decision.get("action", decision.get("type", "unknown")),
            context=decision.get("context", {}),
            recommended_action=decision,
            actual_result=result,
            outcome="pending",
        )
        self.records.append(rec)
        self._save(rec)

    def submit_feedback(self, decision_id: str, feedback: str, actual_result: Dict[str, Any]):
        """Submit human feedback for a decision"""
        for rec in self.records:
            if rec.decision_id == decision_id:
                rec.feedback = feedback
                rec.actual_result = actual_result
                rec.outcome = self._evaluate_outcome(actual_result)
                self._adjust_weights(rec)
                self._save(rec)
                logger.info(f"Feedback submitted for {decision_id}: {rec.outcome}")
                return True
        logger.warning(f"Decision {decision_id} not found")
        return False

    def _evaluate_outcome(self, result: Dict[str, Any]) -> str:
        """Evaluate outcome: success / failure"""
        if not result:
            return "pending"
        score = result.get("score", result.get("outcome_score", 0))
        if score >= 7:
            return "success"
        elif score <= 3:
            return "failure"
        return "pending"

    def _adjust_weights(self, rec: LearningRecord):
        """Adjust strategy weights based on outcome"""
        action = rec.decision_type
        if rec.outcome == "success":
            if action in self._strategy_weights:
                self._strategy_weights[action] = min(2.0, self._strategy_weights[action] * 1.05)
                logger.info(f"Weight increased for {action}: {self._strategy_weights[action]:.2f}")
        elif rec.outcome == "failure":
            if action in self._strategy_weights:
                self._strategy_weights[action] = max(0.3, self._strategy_weights[action] * 0.9)
                logger.warning(f"Weight decreased for {action}: {self._strategy_weights[action]:.2f}")

    def get_recommendation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get strategy recommendation based on learned patterns"""
        recent = [r for r in self.records[-20:] if r.outcome != "pending"]
        success_rate = 0
        if recent:
            successes = sum(1 for r in recent if r.outcome == "success")
            success_rate = successes / len(recent)

        best_actions = sorted(
            self._strategy_weights.items(), key=lambda x: x[1], reverse=True
        )
        return {
            "context": context,
            "recommended_action": best_actions[0][0] if best_actions else "no_data",
            "confidence": round(success_rate, 2),
            "learned_patterns": len(recent),
            "top_strategies": best_actions[:3],
            "timestamp": datetime.now().isoformat(),
        }

    def _save(self, rec: LearningRecord):
        """Append to DB"""
        try:
            with open(self.db_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to save learner record: {e}")