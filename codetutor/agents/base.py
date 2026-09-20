# -*- coding: utf-8 -*-
"""Agent 基类与流水线上下文。

PipelineContext 在 5 个 Agent 之间传递,携带全部中间状态;
steps 字段记录每个 Agent 的执行日志,用于前端展示"多智能体协作过程"。
"""
import time
from dataclasses import dataclass, field


@dataclass
class PipelineContext:
    code: str
    error_text: str = ""
    language: str = "python"
    user_id: int = 0
    knowledge_refs: list = field(default_factory=list)
    diagnosis: dict = field(default_factory=dict)
    fix: dict = field(default_factory=dict)
    explanation: dict = field(default_factory=dict)
    quiz: list = field(default_factory=list)
    archive_id: int = None
    steps: list = field(default_factory=list)
    mock_mode: bool = False

    def to_dict(self):
        return {
            "diagnosis": self.diagnosis,
            "fix": self.fix,
            "explanation": self.explanation,
            "quiz": self.quiz,
            "archive_id": self.archive_id,
            "steps": self.steps,
            "knowledge_refs": [
                {"id": k.get("id"), "title": k.get("title")}
                for k in self.knowledge_refs
            ],
            "mock_mode": self.mock_mode,
        }


class Agent:
    """所有专业 Agent 的基类。"""

    name = "base"
    title = "基础智能体"

    def __init__(self, llm):
        self.llm = llm

    def run(self, ctx: PipelineContext):  # pragma: no cover - 抽象方法
        raise NotImplementedError

    def _timed_run(self, ctx: PipelineContext):
        start = time.time()
        detail = self.run(ctx)
        elapsed = round(time.time() - start, 2)
        ctx.steps.append({
            "agent": self.name,
            "title": self.title,
            "status": "done",
            "detail": detail or "",
            "elapsed": elapsed,
        })
        return ctx
