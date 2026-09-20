# -*- coding: utf-8 -*-
"""出题 Agent:基于本次错因生成递进式变式练习。"""
import json

from codetutor import prompts
from codetutor.agents.base import Agent


class Quizzer(Agent):
    name = "quizzer"
    title = "出题 Agent"

    def run(self, ctx):
        messages = [
            {"role": "system", "content": prompts.QUIZZER},
            {"role": "user", "content": prompts.quiz_user(
                json.dumps(ctx.diagnosis, ensure_ascii=False),
                ctx.diagnosis.get("knowledge_tags", []))},
        ]
        result = self.llm.chat(messages, max_tokens=2000)
        questions = result.get("questions", [])
        ctx.quiz = questions[:3]  # 最多 3 道
        return "生成 %d 道变式练习(巩固/迁移/挑战)" % len(ctx.quiz)
