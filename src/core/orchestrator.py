"""
orchestrator.py - LLM驱动的并行采集调度器
重构自原有串行架构 -> async并行 + LLM统一调度 + 智能路由
"""
import asyncio
import time
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from .base import CollectedData, WorkflowResult
from .llm_router import LLMRouter
from .retry_engine import RetryEngine


@dataclass
class StageResult:
    stage: str
    status: str  # pending / running / done / failed
    data: Optional[Any] = None
    error: Optional[str] = None
    duration: float = 0.0
    llm_calls: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class Orchestrator:
    """
    LLM驱动的并行采集编排器

    工作流8层：
    1. 触发层 - 接收任务，初始化上下文
    2. 关键词层 - LLM根据主题生成/扩展关键词
    3. 采集层 - 4平台并行采集
    4. 清洗层 - LLM去重+相关性打分
    5. 融合层 - LLM跨平台分析+知识图谱
    6. 决策层 - LLM多维打分+行动建议
    7. 执行层 - LLM生成方案+工具执行
    8. 复盘层 - LLM自评+优化建议
    """

    def __init__(self, llm_router: Optional[LLMRouter] = None, retry_engine: Optional[RetryEngine] = None):
        self.llm_router = llm_router or LLMRouter()
        self.retry_engine = retry_engine or RetryEngine()
        self.stage_results: Dict[str, StageResult] = {}
        self.total_llm_calls = 0

    async def run(self, topic: str, config: Optional[Dict[str, Any]] = None) -> WorkflowResult:
        """主入口：执行完整工作流"""
        config = config or {}
        start_time = time.time()
        workflow_id = f"wf_{int(start_time)}"

        self._log("START", f"workflow_id={workflow_id}, topic={topic}")
        self.stage_results["init"] = StageResult(stage="init", status="done", duration=0.01)

        # 阶段2：关键词生成
        keywords = await self._stage_keywords(topic, config)
        self.stage_results["keywords"] = keywords

        # 阶段3：并行采集
        raw_data = await self._stage_collect_parallel(keywords.data or [], config)
        self.stage_results["collect"] = raw_data

        # 阶段4：清洗去重
        cleaned = await self._stage_clean(raw_data.data or [], config)
        self.stage_results["clean"] = cleaned

        # 阶段5：融合分析
        fused = await self._stage_fuse(cleaned.data or [], config)
        self.stage_results["fuse"] = fused

        # 阶段6：决策打分
        decision = await self._stage_decide(fused.data or {}, config)
        self.stage_results["decide"] = decision

        # 阶段7：生成方案
        plan = await self._stage_plan(decision.data or {}, config)
        self.stage_results["plan"] = plan

        # 阶段8：复盘自评
        review = await self._stage_review(fused.data or {}, decision.data or {}, plan.data or {}, config)
        self.stage_results["review"] = review

        total_duration = time.time() - start_time
        self._log("DONE", f"duration={total_duration:.2f}s, llm_calls={self.total_llm_calls}")

        return WorkflowResult(
            workflow_id=workflow_id,
            status="completed",
            topic=topic,
            raw_data_count=len(raw_data.data) if raw_data.data else 0,
            cleaned_data_count=len(cleaned.data) if cleaned.data else 0,
            final_recommendation=plan.data.get("summary", "") if plan.data else "",
            metadata={
                "total_duration": total_duration,
                "llm_calls": self.total_llm_calls,
                "stages": {k: asdict(v) for k, v in self.stage_results.items()},
                "keywords": keywords.data if keywords.data else [],
            },
        )

    async def _stage_keywords(self, topic: str, config: Dict) -> StageResult:
        """阶段2：LLM生成扩展关键词"""
        start = time.time()
        self._log("S2:keywords", f"LLM生成关键词 topic={topic}")

        prompt = (
            f"你是一个电商数据采集专家。为以下主题生成搜索关键词：\n"
            f"主题：{topic}\n\n"
            f"要求：\n"
            f"1. 生成10-20个关键词，覆盖不同角度（品牌/规格/场景/人群/价格带）\n"
            f"2. 包含长尾词和高热度词\n"
            f'3. 输出JSON数组格式：[{{"keyword": "xxx", "priority": 1-3, "angle": "品牌/规格/场景"}}]\n'
            f"4. priority: 1=核心词 2=扩展词 3=长尾词\n"
            f"直接输出JSON，不要解释。"
        )

        result = await self.llm_router.call(prompt, system="你是一个专业的电商关键词专家。")
        self.total_llm_calls += 1

        try:
            keywords = json.loads(result.content)
        except Exception:
            keywords = [{"keyword": topic, "priority": 1, "angle": "核心词"}]

        self._log("S2:keywords", f"完成，数量={len(keywords)}")
        return StageResult(stage="keywords", status="done", data=keywords, duration=time.time() - start, llm_calls=1)

    async def _stage_collect_parallel(self, keywords: List[Dict], config: Dict) -> StageResult:
        """阶段3：4平台并行采集"""
        start = time.time()
        self._log("S3:collect", f"4平台并行采集 关键词数={len(keywords)}")

        priority_keywords = [k for k in keywords if k.get("priority", 3) <= 2] or keywords[:5]

        tasks = [
            self._collect_platform("taobao", priority_keywords, config),
            self._collect_platform("meituan", priority_keywords, config),
            self._collect_platform("jd", priority_keywords, config),
            self._collect_platform("douyin", priority_keywords, config),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_data = []
        for r in results:
            if isinstance(r, Exception):
                self._log("WARN:collect", str(r))
            else:
                all_data.extend(r)

        self._log("S3:collect", f"完成，总数据={len(all_data)}条")
        return StageResult(stage="collect", status="done", data=all_data, duration=time.time() - start, llm_calls=0)

    async def _collect_platform(self, platform: str, keywords: List[Dict], config: Dict) -> List[Dict]:
        """单平台采集（TODO: 替换为真实爬虫）"""
        await asyncio.sleep(0.1)  # 模拟采集延迟

        collected = []
        for kw in keywords[:3]:
            kw_str = kw.get("keyword", "")
            collected.append({
                "platform": platform,
                "keyword": kw_str,
                "priority": kw.get("priority", 3),
                "angle": kw.get("angle", ""),
                "title": f"[{platform}] {kw_str} 相关商品",
                "price": round(50 + abs(hash(kw_str)) % 500, 2),
                "sales": abs(hash(kw_str + platform)) % 10000,
                "rating": round(3.5 + (abs(hash(kw_str)) % 30) / 10, 1),
                "comments": abs(hash(kw_str + platform + "c")) % 5000,
                "shop": f"{platform}官方旗舰店",
                "url": f"https://{platform}.com/ir/r/s?q={kw_str}",
                "collected_at": datetime.now().isoformat(),
            })
        return collected

    async def _stage_clean(self, raw_data: List[Dict], config: Dict) -> StageResult:
        """阶段4：LLM清洗去重+相关性打分"""
        start = time.time()
        self._log("S4:clean", f"LLM清洗去重 原始={len(raw_data)}")

        if not raw_data:
            return StageResult(stage="clean", status="done", data=[], duration=time.time() - start)

        prompt = (
            "你是数据质量专家。分析以下采集数据，判断每条的相关性和质量。\n"
            f"数据：\n{json.dumps(raw_data[:20], ensure_ascii=False)}\n\n"
            "输出JSON（直接输出，不要前缀说明）：\n"
            '{"dedup_indices":[0,2,5],"scored":[{"index":0,"score":0.95,"reason":"高度相关"}]}"
        )

        result = await self.llm_router.call(prompt)
        self.total_llm_calls += 1

        try:
            analysis = json.loads(result.content)
            dedup_set = set(analysis.get("dedup_indices", []))
            scored = {item["index"]: item for item in analysis.get("scored", [])}

            cleaned = []
            for i, item in enumerate(raw_data):
                if i in dedup_set:
                    si = scored.get(i, {"score": 0.5, "reason": "默认通过"})
                    item["relevance_score"] = si["score"]
                    item["quality_reason"] = si["reason"]
                    if si["score"] >= 0.3:
                        cleaned.append(item)
        except Exception:
            cleaned = raw_data

        self._log("S4:clean", f"完成 原始={len(raw_data)} 清洗后={len(cleaned)}")
        return StageResult(stage="clean", status="done", data=cleaned, duration=time.time() - start, llm_calls=1)

    async def _stage_fuse(self, cleaned_data: List[Dict], config: Dict) -> StageResult:
        """阶段5：LLM跨平台融合+知识图谱"""
        start = time.time()
        self._log("S5:fuse", f"LLM融合分析 数量={len(cleaned_data)}")

        if not cleaned_data:
            return StageResult(stage="fuse", status="done", data={"clusters": [], "graph": {}}, duration=time.time() - start)

        prompt = (
            "你是跨平台数据分析专家。对以下电商数据进行聚类和关联分析。\n"
            f"数据：\n{json.dumps(cleaned_data[:30], ensure_ascii=False)}\n\n"
            "任务：1.按商品/品牌聚类 2.识别价格带分布 3.找跨平台同款 4.生成图谱\n"
            "输出JSON（直接输出）：\n"
            '{"clusters":[{"cluster_id":1,"name":"类目","count":5,"avg_price":188.5,"platforms":["taobao"]}],"graph":{"nodes":[],"edges":[]}}'
        )

        result = await self.llm_router.call(prompt)
        self.total_llm_calls += 1

        try:
            fused = json.loads(result.content)
        except Exception:
            fused = {"clusters": [], "graph": {"nodes": [], "edges": []}}

        self._log("S5:fuse", f"完成 聚类={len(fused.get('clusters', []))}个")
        return StageResult(stage="fuse", status="done", data=fused, duration=time.time() - start, llm_calls=1)

    async def _stage_decide(self, fused_data: Dict, config: Dict) -> StageResult:
        """阶段6：LLM多维决策打分"""
        start = time.time()
        self._log("S6:decide", "LLM决策打分")

        clusters = fused_data.get("clusters", [])
        prompt = (
            "你是电商策略专家。基于聚类分析结果，给出可操作的决策建议。\n"
            f"聚类：\n{json.dumps(clusters, ensure_ascii=False)}\n\n"
            "输出JSON（直接输出）：\n"
            '{"scores":[{"cluster_id":1,"cluster_name":"示例","dimensions":{"hotness":8.5,"competition":7.2,"profit":6.8,"growth":7.5},"overall_score":7.8}],"top3":[1],"action":"建议"}'
        )

        result = await self.llm_router.call(prompt)
        self.total_llm_calls += 1

        try:
            decision = json.loads(result.content)
        except Exception:
            decision = {"scores": [], "top3": [], "action": ""}

        self._log("S6:decide", f"完成 TOP3={decision.get('top3', [])}")
        return StageResult(stage="decide", status="done", data=decision, duration=time.time() - start, llm_calls=1)

    async def _stage_plan(self, decision_data: Dict, config: Dict) -> StageResult:
        """阶段7：LLM生成执行方案"""
        start = time.time()
        self._log("S7:plan", "LLM生成执行方案")

        scores = decision_data.get("scores", [])
        prompt = (
            "你是运营方案专家。基于决策结果生成执行方案。\n"
            f"决策：\n{json.dumps(decision_data, ensure_ascii=False)}\n\n"
            "输出JSON（直接输出）：\n"
            '{"summary":"一句话总结","objectives":["目标"],"phases":[{"phase":1,"name":"测试期","duration":"1-2周","actions":["上架"],"kpis":["点击率>3%"]}],"risks":["竞争激烈"]}'
        )

        result = await self.llm_router.call(prompt)
        self.total_llm_calls += 1

        try:
            plan = json.loads(result.content)
        except Exception:
            plan = {"summary": "分析完成", "objectives": [], "phases": [], "risks": []}

        self._log("S7:plan", f"完成 方案字数~{len(json.dumps(plan, ensure_ascii=False))}")
        return StageResult(stage="plan", status="done", data=plan, duration=time.time() - start, llm_calls=1)

    async def _stage_review(self, fused_data: Dict, decision_data: Dict, plan_data: Dict, config: Dict) -> StageResult:
        """阶段8：LLM自评复盘+优化建议"""
        start = time.time()
        self._log("S8:review", "LLM自评复盘")

        prompt = (
            "你是AI自优化专家。评估本次工作流表现，给出改进建议。\n"
            "输出JSON（直接输出）：\n"
            '{"self_score":7.5,"strengths":["并行采集效率高"],"weaknesses":["缺少真实爬虫"],"improvements":["接入真实API"],"next_workspace_hints":"下次增加社交平台数据"}'
        )

        result = await self.llm_router.call(prompt)
        self.total_llm_calls += 1

        try:
            review = json.loads(result.content)
        except Exception:
            review = {"self_score": 0, "strengths": [], "weaknesses": [], "improvements": []}

        self._log("S8:review", f"完成 自评分={review.get('self_score', 'N/A')}")
        return StageResult(stage="review", status="done", data=review, duration=time.time() - start, llm_calls=1)

    def _log(self, stage: str, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [{stage}] {msg}")

    def get_stage_status(self) -> Dict[str, StageResult]:
        return self.stage_results.copy()

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "total_llm_calls": self.total_llm_calls,
            "stages_completed": len([s for s in self.stage_results.values() if s.status == "done"]),
            "stages_total": 8,
            "total_duration": sum(s.duration for s in self.stage_results.values()),
            "stage_breakdown": {k: {"duration": v.duration, "llm_calls": v.llm_calls, "status": v.status}
                              for k, v in self.stage_results.items()},
        }