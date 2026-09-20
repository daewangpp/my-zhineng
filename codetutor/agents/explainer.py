# -*- coding: utf-8 -*-
"""讲解 Agent:三段式教学讲解(考点定位/错因分析/原理解读)。"""
import json

from codetutor import prompts
from codetutor.agents.base import Agent


class Explainer(Agent):
    name = "explainer"
    title = "讲解 Agent"

    def run(self, ctx):
        # 讲解只依赖诊断与原代码,与修复解耦 → 支持与修复并行执行
        messages = [
            {"role": "system", "content": prompts.EXPLAINER},
            {"role": "user", "content": prompts.explain_user(
                ctx.code, json.dumps(ctx.diagnosis, ensure_ascii=False))},
        ]
        result = self.llm.chat(messages, max_tokens=800)
        ctx.explanation = {
            "concept": self._clean(result.get("concept", ""), "考点定位"),
            "why_common": self._clean(result.get("why_common", ""), "错因分析"),
            "principle": self._clean(result.get("principle", ""), "原理解读"),
        }
        return "三段式讲解已生成(考点/错因/原理)"

    @staticmethod
    def _clean(text, label):
        """剥掉模型可能在 value 开头重复输出的字段名前缀(兼容冒号/加粗/空格变体)。"""
        import re
        text = (text or "").strip()
        pattern = r"^[*_\s]*" + re.escape(label) + r"[*_\s]*[:：]?[*_\s]*"
        return re.sub(pattern, "", text).strip()
