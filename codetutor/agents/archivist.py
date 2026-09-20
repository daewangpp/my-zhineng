# -*- coding: utf-8 -*-
"""档案 Agent:将本次 debug 写入个人 Bug 档案,生成艾宾浩斯复习计划。"""
from codetutor.agents.base import Agent
from codetutor.memory import archive


class Archivist(Agent):
    name = "archivist"
    title = "档案 Agent"

    def __init__(self, llm=None):
        super().__init__(llm)  # 归档无需 LLM,纯规则执行

    def run(self, ctx):
        ctx.archive_id = archive.add_mistake(
            error_type=ctx.diagnosis.get("error_type", "Unknown"),
            error_key=ctx.diagnosis.get("error_key", "unknown"),
            knowledge_tags=ctx.diagnosis.get("knowledge_tags", []),
            code_snapshot=ctx.code,
            fixed_code=ctx.fix.get("fixed_code", ""),
            root_cause=ctx.diagnosis.get("root_cause", ""),
            verified=ctx.fix.get("verified", False),
            language=ctx.language,
            user_id=ctx.user_id,
        )
        return "已归档(档案编号 #%d),已按艾宾浩斯曲线排入复习计划" % ctx.archive_id
