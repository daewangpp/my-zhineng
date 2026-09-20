# -*- coding: utf-8 -*-
"""修复 Agent:生成修复代码,并在沙箱中真实执行验证。

核心机制 —— 可验证修复(Verified Fix):
生成修复 → 沙箱执行 → 验证原报错消除;
失败则把沙箱报错反馈给模型重试,最多 FIX_MAX_ATTEMPTS 次。
"""
import json

import config
from codetutor import prompts
from codetutor.agents.base import Agent
from codetutor.tools import sandbox


class Fixer(Agent):
    name = "fixer"
    title = "修复 Agent(沙箱验证)"

    def run(self, ctx):
        original_error = ctx.diagnosis.get("error_type")

        # 诊断为 NoError(代码本身正确):不修改代码,原样验证
        if original_error == "NoError":
            verified, sand, verify_message = sandbox.verify_fix(ctx.code)
            ctx.fix = {
                "fixed_code": ctx.code,
                "change_summary": "代码本身正确,无需修改",
                "verified": verified,
                "verify_message": verify_message,
                "attempts": 0,
                "sandbox_stdout": sand.stdout,
            }
            return "代码本身正确,原样保留"

        prev_error = None
        fixed_code = ctx.code
        verified = False
        verify_message = "未验证"
        last_stdout = ""
        attempts = 0

        for attempt in range(1, config.FIX_MAX_ATTEMPTS + 1):
            attempts = attempt
            messages = [
                {"role": "system", "content": prompts.FIXER},
                {"role": "user", "content": prompts.fix_user(
                    ctx.code, json.dumps(ctx.diagnosis, ensure_ascii=False),
                    prev_error=prev_error)},
            ]
            result = self.llm.chat(messages, max_tokens=1500)
            fixed_code = result.get("fixed_code", ctx.code)
            summary = result.get("change_summary", "")
            # 模型可能把 expected_stdout 返回为 list,统一规整为字符串
            expected_stdout = result.get("expected_stdout")
            if isinstance(expected_stdout, list):
                expected_stdout = "\n".join(str(x) for x in expected_stdout)
            elif expected_stdout is not None:
                expected_stdout = str(expected_stdout)

            # 沙箱双轨验证:不报错 + (有断言时)输出与预期一致
            verified, sand, verify_message = sandbox.verify_fix(
                fixed_code, original_error_type=original_error,
                expected_stdout=expected_stdout)
            last_stdout = sand.stdout
            if verified:
                break
            # 把失败详情(含输出差异)反馈给模型重试
            prev_error = verify_message + "\n" + (sand.stderr or "")

        ctx.fix = {
            "fixed_code": fixed_code,
            "change_summary": summary if attempts else "",
            "verified": verified,
            "verify_message": verify_message,
            "attempts": attempts,
            "sandbox_stdout": last_stdout,
        }
        # 步骤摘要不暴露验证结论,仅展示修复动作本身
        out_brief = ("| 运行输出: %s" % last_stdout.strip().splitlines()[-1]
                     if last_stdout.strip() else "")
        return "修复方案已生成(尝试 %d 次)%s" % (attempts, out_brief)
