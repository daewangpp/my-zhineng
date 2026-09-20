# -*- coding: utf-8 -*-
"""Orchestrator 多智能体编排器。

主流水线:Diagnoser → (Fixer ∥ Explainer 并行) → Archivist
- 诊断先行(后续依赖其结论);
- 修复与讲解**并行**(讲解只依赖诊断+原代码,与修复解耦),缩短总耗时;
- 出题(Quizzer)按需生成,不阻塞主流程。
任一环节异常被捕获并记录到 steps,保证系统整体可降级、可演示。
"""
import threading
import time
import traceback

from codetutor.agents.base import PipelineContext
from codetutor.agents.diagnoser import Diagnoser
from codetutor.agents.fixer import Fixer
from codetutor.agents.explainer import Explainer
from codetutor.agents.quizzer import Quizzer
from codetutor.agents.archivist import Archivist
from codetutor.llm import get_llm
from codetutor.memory import archive


class Orchestrator:
    """多智能体流水线编排器。"""

    def __init__(self, llm=None):
        if llm is None:
            llm, mock_mode = get_llm()
            self.mock_mode = mock_mode
        else:
            self.mock_mode = False
        self.llm = llm
        self.diagnoser = Diagnoser(llm)
        self.fixer = Fixer(llm)
        self.explainer = Explainer(llm)
        self.archivist = Archivist(llm)
        self.quizzer = Quizzer(llm)

    @staticmethod
    def _safe_run(agent, ctx):
        """单环节失败不拖垮整体:捕获异常并记录步骤日志。"""
        try:
            agent._timed_run(ctx)
        except Exception as e:  # noqa: BLE001
            ctx.steps.append({
                "agent": agent.name, "title": agent.title,
                "status": "error",
                "detail": "环节异常: %s" % e,
                "elapsed": 0,
            })
            # 注意:后台无 stderr 句柄时 print_exc 会抛 OSError(Errno 22),必须防御
            try:
                traceback.print_exc()
            except Exception:  # noqa: BLE001
                pass

    def analyze(self, code, error_text="", language="python", user_id=0):
        """执行主流水线:诊断 → (修复∥讲解并行) → 归档。"""
        ctx = PipelineContext(code=code, error_text=error_text,
                              language=language, user_id=user_id,
                              mock_mode=self.mock_mode)
        # 1) 诊断(后续环节的输入)
        self._safe_run(self.diagnoser, ctx)
        # 2) 修复与讲解并行(讲解已解耦,不依赖修复结果)
        t_fix = threading.Thread(target=self._safe_run, args=(self.fixer, ctx))
        t_exp = threading.Thread(target=self._safe_run, args=(self.explainer, ctx))
        t_fix.start(); t_exp.start()
        t_fix.join(); t_exp.join()
        # 3) 归档
        self._safe_run(self.archivist, ctx)
        return ctx.to_dict()

    def quiz(self, archive_id):
        """按需生成举一反三练习:从档案恢复上下文,单独调用出题 Agent。"""
        record = archive.get_mistake(archive_id)
        if not record:
            return {"error": "档案不存在"}
        ctx = PipelineContext(
            code=record["code_snapshot"], language=record["language"],
            mock_mode=self.mock_mode,
            diagnosis={
                "error_type": record["error_type"],
                "error_key": record["error_key"],
                "root_cause": record["root_cause"],
                "knowledge_tags": record["knowledge_tags"],
            },
        )
        try:
            self.quizzer._timed_run(ctx)
        except Exception as e:  # noqa: BLE001
            return {"error": "出题失败: %s" % e, "questions": []}
        return {"questions": ctx.quiz, "steps": ctx.steps}

    # ---- 记忆与复习入口 ----

    @staticmethod
    def stats():
        return archive.get_stats()

    @staticmethod
    def review_list():
        return archive.get_due_reviews()

    @staticmethod
    def review_done(mistake_id, passed):
        return archive.mark_reviewed(mistake_id, passed)

    @staticmethod
    def history(limit=50):
        return archive.list_mistakes(limit)


if __name__ == "__main__":
    # 冒烟测试:一个经典的可变默认参数 bug
    demo_code = (
        "def add_item(item, box=[]):\n"
        "    box.append(item)\n"
        "    return box\n"
        "\n"
        "print(add_item(1))\n"
        "print(add_item(2))\n"
    )
    orch = Orchestrator()
    result = orch.analyze(demo_code, "第二次调用应该返回 [2],为什么返回了 [1, 2]?")
    print("诊断:", result["diagnosis"])
    print("修复验证:", result["fix"].get("verified"), result["fix"].get("verify_message"))
    print("步骤数:", len(result["steps"]))
