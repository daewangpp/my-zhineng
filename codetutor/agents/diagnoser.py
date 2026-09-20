# -*- coding: utf-8 -*-
"""诊断 Agent:结合 RAG 知识库定位 bug 根因。"""
from codetutor import prompts
from codetutor.agents.base import Agent
from codetutor.tools import knowledge


class Diagnoser(Agent):
    name = "diagnoser"
    title = "诊断 Agent"

    def run(self, ctx):
        # 1) RAG 检索:用代码+报错文本检索相关知识条目
        query = (ctx.error_text or "") + "\n" + ctx.code
        ctx.knowledge_refs = knowledge.search(query, top_k=2)

        # 2) LLM 诊断(知识库内容注入提示词)
        messages = [
            {"role": "system", "content": prompts.DIAGNOSER},
            {"role": "user", "content": prompts.diagnosis_user(
                ctx.code, ctx.error_text, ctx.knowledge_refs)},
        ]
        result = self.llm.chat(messages, max_tokens=600)
        ctx.diagnosis = {
            "error_type": result.get("error_type", "UnknownError"),
            "error_key": result.get("error_key", "unknown"),
            "error_line": result.get("error_line", 0),
            "root_cause": result.get("root_cause", ""),
            "knowledge_tags": result.get("knowledge_tags", []),
            "brief": result.get("brief", ""),
        }
        kb_hint = ("引用知识库:%s" % "、".join(k["title"] for k in ctx.knowledge_refs)
                   if ctx.knowledge_refs else "无知识库命中")
        return "%s(%s)| %s" % (
            ctx.diagnosis["error_type"], kb_hint, ctx.diagnosis["brief"])
