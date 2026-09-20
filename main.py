# -*- coding: utf-8 -*-
"""CodeTutor 命令行入口。

用法:
  py main.py                      交互式模式
  py main.py --demo               运行内置演示用例
  py main.py --file bug.py [-e "报错描述"]
  py main.py --stats              查看我的学情档案
  py main.py --review             查看今日到期复习
  py main.py --review-done ID 1   复习打卡(1=通过 0=未通过)
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from codetutor.orchestrator import Orchestrator

DEMO_CODE = (
    "def add_item(item, box=[]):\n"
    "    box.append(item)\n"
    "    return box\n"
    "\n"
    "print(add_item(1))\n"
    "print(add_item(2))\n"
)
DEMO_ERROR = "第二次调用 add_item(2) 我期望返回 [2],实际却返回了 [1, 2],为什么?"


def print_result(r):
    print("\n" + "=" * 60)
    print("多智能体协作过程:")
    for s in r["steps"]:
        icon = "√" if s["status"] == "done" else "×"
        print("  [%s] %s (%.2fs)\n      %s" % (icon, s["title"], s["elapsed"], s["detail"]))
    d = r["diagnosis"]
    print("\n" + "=" * 60)
    print("【诊断】%s (第 %s 行)" % (d.get("error_type"), d.get("error_line")))
    print("  根因: %s" % d.get("root_cause"))
    print("  知识点: %s" % "、".join(d.get("knowledge_tags", [])))
    f = r["fix"]
    print("\n【修复】")
    print("  改动: %s" % f.get("change_summary"))
    print("  修复代码:\n" + "\n".join("    " + l for l in f.get("fixed_code", "").splitlines()))
    if f.get("sandbox_stdout"):
        print("  运行结果:\n" + "\n".join("    " + l for l in f["sandbox_stdout"].splitlines()))
    e = r["explanation"]
    print("\n【讲解】")
    print("  考点定位: %s" % e.get("concept"))
    print("  错因分析: %s" % e.get("why_common"))
    print("  原理解读: %s" % e.get("principle"))
    print("\n【归档】档案编号 #%s,已加入艾宾浩斯复习计划" % r.get("archive_id"))


def print_quiz(questions):
    print("\n【举一反三 · 变式练习】")
    for i, q in enumerate(questions, 1):
        print("  %d. [%s] %s" % (i, q.get("type"), q.get("title")))
        print("     题目: %s" % q.get("question"))
        print("     答案: %s" % q.get("answer"))


def main():
    parser = argparse.ArgumentParser(description="CodeTutor - 程序员的 AI 错题搭子")
    parser.add_argument("--demo", action="store_true", help="运行内置演示")
    parser.add_argument("--file", help="待诊断的代码文件")
    parser.add_argument("-e", "--error", default="", help="报错信息/问题描述")
    parser.add_argument("--stats", action="store_true", help="查看学情档案")
    parser.add_argument("--review", action="store_true", help="查看今日复习")
    parser.add_argument("--review-done", nargs=2, metavar=("ID", "PASSED"),
                        help="复习打卡:ID 与 是否通过(1/0)")
    args = parser.parse_args()

    orch = Orchestrator()

    if args.stats:
        print(json.dumps(orch.stats(), ensure_ascii=False, indent=2))
        return
    if args.review:
        items = orch.review_list()
        if not items:
            print("今天没有到期的复习任务。")
        for it in items:
            print("#%s [%s] 知识点:%s | 根因:%s" % (
                it["id"], it["error_type"], it["knowledge_tags"], it["root_cause"][:50]))
        return
    if args.review_done:
        mid, passed = int(args.review_done[0]), args.review_done[1] == "1"
        print(orch.review_done(mid, passed))
        return

    if args.demo:
        result = orch.analyze(DEMO_CODE, DEMO_ERROR)
        print_result(result)
        print("\n[demo 模式:自动生成举一反三练习]")
        print_quiz(orch.quiz(result["archive_id"]).get("questions", []))
        return

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            code = f.read()
        result = orch.analyze(code, args.error)
        print_result(result)
        if input("\n是否生成举一反三练习?(y/N):").strip().lower() == "y":
            print_quiz(orch.quiz(result["archive_id"]).get("questions", []))
        return

    # 交互式
    print("CodeTutor 交互模式(输入 END 结束代码输入)")
    print("请粘贴你的问题代码,输入 END 结束:")
    lines = []
    while True:
        line = sys.stdin.readline()
        if not line or line.strip() == "END":
            break
        lines.append(line)
    code = "".join(lines)
    error = input("请粘贴报错信息或描述你的问题(可留空):").strip()
    result = orch.analyze(code, error)
    print_result(result)
    if input("\n是否生成举一反三练习?(y/N):").strip().lower() == "y":
        print_quiz(orch.quiz(result["archive_id"]).get("questions", []))


if __name__ == "__main__":
    main()
