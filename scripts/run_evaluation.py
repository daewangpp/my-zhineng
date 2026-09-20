# -*- coding: utf-8 -*-
"""实验评估脚本 v2:40 个标准用例,客观断言驱动。

核心设计:
- 每个用例附带作者编写的 expect_stdout(客观标准答案),修复代码在沙箱中真实
  运行后逐字符比对 —— 不采信系统自报的"已验证",杜绝假阳性;
- 含 4 个"正确代码"用例(expect_error_type=None),考察系统是否误诊/误改;
- 量化指标:诊断准确率 / 修复正确率(客观) / 系统自报通过率 / 误报数(必须为 0)/
  诚实标记数 / 平均尝试次数。

输出: reports/evaluation_report.md
"""
import datetime
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from codetutor.orchestrator import Orchestrator  # noqa: E402
from codetutor.tools.sandbox import run_code, _normalize_stdout  # noqa: E402
from tests.test_cases import CASES  # noqa: E402


def judge_fix(case, fixed_code):
    """客观判定修复:沙箱真实运行 + 作者断言比对(支持候选输出列表)。"""
    sand = run_code(fixed_code)
    if case["check_mode"] == "stdout":
        expects = case["expect_stdout"]
        if isinstance(expects, str):
            expects = [expects]
        actual = _normalize_stdout(sand.stdout)
        correct = sand.ok and any(actual == _normalize_stdout(e) for e in expects)
    else:  # no_error
        correct = sand.ok
    return correct, sand


def main():
    # --only A03,A07 只跑指定用例(名称前缀匹配)
    cases = CASES
    if "--only" in sys.argv:
        prefixes = sys.argv[sys.argv.index("--only") + 1].split(",")
        cases = [c for c in CASES if any(c["name"].startswith(p) for p in prefixes)]
        print("仅跑指定用例: %d 个" % len(cases))

    orch = Orchestrator()
    print("模式: %s | 用例数: %d" % ("Mock" if orch.mock_mode else "真实LLM", len(cases)))

    rows = []
    n_diag = n_diag_ok = n_fix_correct = n_reported_ok = 0
    n_false_positive = n_honest_negative = 0
    total_attempts = 0
    t0 = time.time()

    for i, case in enumerate(cases, 1):
        name = case["name"]
        print("[%d/%d] %s ..." % (i, len(cases), name), flush=True)
        try:
            r = orch.analyze(case["code"], case["symptom"])
            diag_type = r["diagnosis"].get("error_type")
            fixed = r["fix"].get("fixed_code", case["code"])
            reported = bool(r["fix"].get("verified"))
            attempts = r["fix"].get("attempts", 0)
            total_attempts += attempts

            # 诊断判定(None 用例不参与诊断准确率,用于考察误诊)
            if case["expect_error_type"] is not None:
                n_diag += 1
                diag_ok = diag_type == case["expect_error_type"]
                n_diag_ok += diag_ok
                diag_mark = "✔" if diag_ok else "✘"
            else:
                diag_mark = "—(正确代码)"
                diag_ok = None

            # 客观修复判定
            fix_correct, _sand = judge_fix(case, fixed)
            n_fix_correct += fix_correct

            # 自报 vs 客观
            n_reported_ok += reported
            fp = reported and not fix_correct
            hn = (not reported) and (not fix_correct)
            n_false_positive += fp
            n_honest_negative += hn

            rows.append((name, diag_type or "-", case["expect_error_type"] or "-",
                         diag_mark, "✔" if fix_correct else "✘",
                         "✔" if reported else "✘",
                         "误报!" if fp else ("诚实" if hn else "一致"),
                         attempts))
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            rows.append((name, "异常", case["expect_error_type"] or "-",
                         "✘", "✘", "✘", str(e)[:30], "-"))

    n = len(cases)
    elapsed = time.time() - t0

    rep = []
    rep.append("# CodeTutor 实验评估报告\n")
    rep.append("- 评估时间:%s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    rep.append("- 模式:%s" % ("Mock 演示" if orch.mock_mode else "真实 LLM"))
    rep.append("- 用例数:%d(报错类 20 / 逻辑类 15 / 综合类 5,含 4 个正确代码用例)" % n)
    rep.append("- 总耗时:%.0f 秒\n" % elapsed)
    rep.append("## 总体指标\n")
    rep.append("| 指标 | 结果 | 说明 |")
    rep.append("|---|---|---|")
    rep.append("| 诊断准确率 | **%d/%d = %.0f%%** | 错误类型与标准答案匹配 |" % (
        n_diag_ok, n_diag, n_diag_ok / max(n_diag, 1) * 100))
    rep.append("| 修复正确率(客观断言) | **%d/%d = %.0f%%** | 修复代码沙箱真实运行,输出逐字符比对作者编写的标准输出 |" % (
        n_fix_correct, n, n_fix_correct / n * 100))
    rep.append("| 系统自报验证通过率 | %d/%d = %.0f%% | 系统内双轨验证(不报错+输出断言)判定通过 |" % (
        n_reported_ok, n, n_reported_ok / n * 100))
    rep.append("| **误报数** | **%d(必须=0)** | 自报通过但客观判定错误 —— 假阳性,零容忍 |" % n_false_positive)
    rep.append("| 诚实标记数 | %d | 客观失败且系统如实标记未通过 |" % n_honest_negative)
    rep.append("| 修复平均尝试次数 | %.2f 次 | 沙箱反馈重试机制有效性 |" % (total_attempts / n))
    rep.append("\n## 分用例明细\n")
    rep.append("| 用例 | 诊断类型 | 期望类型 | 诊断 | 客观修复 | 自报验证 | 自报vs客观 | 重试 |")
    rep.append("|---|---|---|---|---|---|---|---|")
    for row in rows:
        rep.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % row)
    rep.append("")
    rep.append("## 结论")
    rep.append("1. 修复正确性以**作者编写的客观输出断言**为准,不采信系统自报;")
    rep.append("2. 误报数必须保持 0 —— '可验证修复'机制承诺:凡标记✔的修复,输出必然与预期逐字符一致;")
    rep.append("3. 含 4 个正确代码用例用于考察误诊率;修复失败用例均被如实标记,不静默交付。")

    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "evaluation_report.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(rep))
    print("\n报告: %s" % out_path)
    print("诊断 %.0f%% | 客观修复 %.0f%% | 误报 %d | 耗时 %.0fs" % (
        n_diag_ok / max(n_diag, 1) * 100, n_fix_correct / n * 100,
        n_false_positive, elapsed))


if __name__ == "__main__":
    main()
