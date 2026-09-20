# -*- coding: utf-8 -*-
"""冒烟测试脚本:验证沙箱/知识库/档案/完整流水线(mock 模式)。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from codetutor.tools import sandbox, knowledge  # noqa: E402
from codetutor.memory import archive  # noqa: E402


def test_sandbox():
    print("== 沙箱测试 ==")
    r1 = sandbox.run_code("print('hello', 1 + 1)")
    print("1. 正常代码:", r1.ok, repr(r1.stdout.strip()))
    r2 = sandbox.run_code("lst = [1, 2]\nprint(lst[5])")
    print("2. 越界代码:", r2.ok, sandbox.extract_error(r2.stderr))
    r3 = sandbox.run_code("import os\nos.system('dir')")
    print("3. 危险拦截:", r3.blocked, r3.block_reason)
    r4 = sandbox.run_code("while True:\n    pass", timeout=3)
    print("4. 死循环超时:", r4.timed_out)
    ok, res, msg = sandbox.verify_fix("lst = [1, 2]\nprint(lst[1])", "IndexError")
    print("5. 修复验证:", ok, msg)
    ok2, _, msg2 = sandbox.verify_fix("lst = [1, 2]\nprint(lst[9])", "IndexError")
    print("6. 无效修复识别:", ok2, msg2)


def test_knowledge():
    print("\n== 知识库检索测试 ==")
    hits = knowledge.search("IndexError list index out of range 列表 索引", top_k=2)
    for h in hits:
        print(" 命中:", h["id"], h["title"])
    hits2 = knowledge.search("可变默认参数 函数多次调用数据累积", top_k=1)
    for h in hits2:
        print(" 命中:", h["id"], h["title"])


def test_archive():
    print("\n== 档案测试 ==")
    mid = archive.add_mistake("IndexError", "index_error", ["列表", "索引"],
                              "print(lst[5])", "print(lst[1])", "索引越界", True)
    print(" 归档 id:", mid)
    print(" 统计:", archive.get_stats())


if __name__ == "__main__":
    test_sandbox()
    test_knowledge()
    test_archive()
