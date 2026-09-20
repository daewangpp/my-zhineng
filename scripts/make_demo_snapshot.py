# -*- coding: utf-8 -*-
"""生成静态演示页快照:服务端渲染完整分析结果为独立 HTML 文件。

用途:
1. 申报材料截图(Edge headless 截 file:// 本地文件,100% 可靠);
2. 无需启动服务的演示证据;
3. 录制演示视频时的稳定画面源。
"""
import datetime
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from codetutor.orchestrator import Orchestrator  # noqa: E402
from tests.test_cases import CASES  # noqa: E402


def esc(s):
    return html.escape(str(s if s is not None else ""))


def render(r, case_name, error_text):
    steps_html = ""
    for s in r["steps"]:
        cls = "done" if s["status"] == "done" else "error"
        icon = "✔" if s["status"] == "done" else "✘"
        title = esc(s["title"]) + ("(按需)" if s["agent"] == "quizzer" else "")
        steps_html += (
            '<div class="step %s"><div class="t">%s %s</div>'
            '<div class="step-detail">%s · %.2fs</div></div>'
            % (cls, icon, title, esc(s["detail"]), s["elapsed"]))

    d = r["diagnosis"]
    tags = "".join('<span class="tag kb">📖 %s</span>' % esc(t)
                   for t in d.get("knowledge_tags", []))
    kb_refs = "、".join(esc(k["id"] + " " + k["title"]) for k in r.get("knowledge_refs", [])) or "无"

    f = r["fix"]
    stdout_block = ""
    if f.get("sandbox_stdout"):
        stdout_block = ('<div class="muted" style="margin-top:6px;">运行结果:</div>'
                        '<div class="code-block">%s</div>' % esc(f["sandbox_stdout"]))

    e = r["explanation"]
    quiz_html = ""
    for q in r.get("quiz", []):
        quiz_html += (
            '<div class="quiz-item"><b>[%s] %s</b>'
            '<div class="quiz-q">%s</div>'
            '<details class="quiz-answer"><summary>查看答案</summary>%s</details></div>'
            % (esc(q.get("type")), esc(q.get("title")),
               esc(q.get("question")), esc(q.get("answer"))))

    mock_note = ('<span class="badge-mock">演示模式(MockLLM,未配置 API Key)</span>'
                 if r.get("mock_mode") else "")

    return PAGE % {
        "case_name": esc(case_name), "error_text": esc(error_text),
        "code": esc(CASES_BY_NAME[case_name]["code"]),
        "steps": steps_html,
        "error_type": esc(d.get("error_type")), "error_line": esc(d.get("error_line")),
        "root_cause": esc(d.get("root_cause")), "tags": tags, "kb_refs": kb_refs,
        "change_summary": esc(f.get("change_summary")),
        "fixed_code": esc(f.get("fixed_code")), "stdout_block": stdout_block,
        "concept": esc(e.get("concept")), "why_common": esc(e.get("why_common")),
        "principle": esc(e.get("principle")), "quiz": quiz_html,
        "archive_id": esc(r.get("archive_id")), "mock_note": mock_note,
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


PAGE = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>CodeTutor 演示快照 · %(case_name)s</title>
<style>
  :root { --bg:#0d1117; --panel:#161b22; --panel2:#1c2330; --border:#2d3748; --text:#e6edf3;
    --muted:#8b949e; --accent:#4f8ef7; --accent2:#7c5cff; --green:#2ea043; --green-bg:#12261e; --red:#f85149; --amber:#d29922; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:var(--bg); color:var(--text); font-family:"Microsoft YaHei","PingFang SC",sans-serif; }
  .header { padding:18px 32px; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center; background:linear-gradient(90deg,#0d1117,#131a2a); }
  .logo { font-size:22px; font-weight:700; background:linear-gradient(90deg,var(--accent),var(--accent2)); -webkit-background-clip:text; background-clip:text; color:transparent; }
  .logo small { display:block; font-size:12px; color:var(--muted); -webkit-text-fill-color:var(--muted); font-weight:400; }
  .badge-mock { background:var(--amber); color:#1a1a1a; font-size:12px; padding:3px 10px; border-radius:10px; font-weight:600; }
  .container { max-width:1100px; margin:0 auto; padding:22px 32px; }
  .user-input { background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:16px; margin-bottom:14px; }
  .code-block { background:#0a0e14; border:1px solid var(--border); border-radius:8px; padding:14px; font-family:Consolas,monospace; font-size:13px; line-height:1.6; white-space:pre-wrap; color:#a5d6ff; margin-top:10px; }
  .steps { display:flex; gap:6px; margin:14px 0; }
  .step { flex:1; text-align:center; padding:10px 4px; border-radius:8px; background:var(--panel); border:1px solid var(--green); font-size:12px; color:var(--green); }
  .step.error { border-color:var(--red); color:var(--red); }
  .step .t { font-weight:600; font-size:13px; }
  .step-detail { font-size:11px; color:var(--muted); margin-top:4px; }
  .card { background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:18px; margin-bottom:14px; }
  .card-title { font-size:15px; font-weight:600; margin-bottom:10px; display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
  .tag { display:inline-block; padding:3px 10px; border-radius:12px; font-size:12px; background:var(--panel2); border:1px solid var(--border); color:var(--muted); margin:2px 4px 2px 0; }
  .tag.type { background:rgba(248,81,73,.15); color:var(--red); border-color:var(--red); }
  .tag.kb { background:rgba(79,142,247,.12); color:var(--accent); border-color:var(--accent); }
  .verify-badge { padding:5px 14px; border-radius:14px; font-size:13px; font-weight:600; background:var(--green-bg); color:var(--green); border:1px solid var(--green); }
  .verify-badge.fail { background:rgba(248,81,73,.12); color:var(--red); border-color:var(--red); }
  .explain-item { margin:10px 0; padding-left:12px; border-left:3px solid var(--accent2); line-height:1.8; font-size:14px; }
  .explain-item b { color:var(--accent2); font-size:13px; }
  .quiz-item { border:1px solid var(--border); border-radius:10px; padding:14px; margin-top:10px; background:var(--panel2); font-size:14px; }
  .quiz-q { margin:6px 0; white-space:pre-wrap; }
  .quiz-answer { margin-top:8px; padding:10px; background:#0a0e14; border-radius:8px; font-size:13px; color:var(--muted); }
  .quiz-answer summary { color:var(--accent); cursor:pointer; font-size:12px; }
  .archive-tip { background:linear-gradient(90deg,rgba(79,142,247,.12),rgba(124,92,255,.12)); border:1px solid var(--accent); border-radius:12px; padding:14px 18px; font-size:14px; }
  .muted { color:var(--muted); font-size:12px; }
  .footer { text-align:center; color:var(--muted); font-size:12px; padding:18px; }
</style></head><body>
<div class="header"><div class="logo">CodeTutor<small>程序员的 AI 错题搭子 · 多智能体 · 沙箱验证 · 错题闭环</small></div>%(mock_note)s</div>
<div class="container">
  <div class="user-input"><b>🧑‍🎓 学生提交:</b>%(case_name)s
    <div class="code-block">%(code)s</div>
    <div class="muted" style="margin-top:6px;">问题描述:%(error_text)s</div>
  </div>
  <div class="steps">%(steps)s</div>
  <div class="card"><div class="card-title">🎯 诊断报告 <span class="tag type">%(error_type)s</span> <span class="tag">第 %(error_line)s 行</span></div>
    <p style="font-size:14px;line-height:1.8;">%(root_cause)s</p>
    <div style="margin-top:8px;">%(tags)s</div>
    <div class="muted" style="margin-top:8px;">RAG 引用知识库:%(kb_refs)s</div></div>
  <div class="card"><div class="card-title">🔧 修复方案</div>
    <div class="muted">%(change_summary)s</div>
    <div class="code-block">%(fixed_code)s</div>%(stdout_block)s</div>
  <div class="card"><div class="card-title">💡 三段式讲解</div>
    <div class="explain-item"><b>考点定位</b><br>%(concept)s</div>
    <div class="explain-item"><b>错因分析</b><br>%(why_common)s</div>
    <div class="explain-item"><b>原理解读</b><br>%(principle)s</div></div>
  <div class="card"><div class="card-title">📝 变式练习(举一反三 · 按需生成)</div>
    <div class="muted" style="margin-bottom:8px;">主流程仅做诊断/修复/讲解,练习由用户点击后触发出题 Agent 生成,缩短响应时间。以下为点击后生成结果:</div>%(quiz)s</div>
  <div class="archive-tip">🗂 本次 debug 已归档为 <b>#%(archive_id)s</b>,系统已按艾宾浩斯遗忘曲线安排复习(1/2/4/7/15 天),可在「我的档案」查看学情与今日复习。</div>
  <div class="footer">CodeTutor 演示快照 · 生成于 %(time)s</div>
</div></body></html>"""

CASES_BY_NAME = {c["name"]: c for c in CASES}


# ---------------------------------------------------------------------------
# 档案页静态快照
# ---------------------------------------------------------------------------

ARCHIVE_PAGE = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>CodeTutor 我的档案</title>
<style>
  :root { --bg:#0d1117; --panel:#161b22; --panel2:#1c2330; --border:#2d3748; --text:#e6edf3;
    --muted:#8b949e; --accent:#4f8ef7; --accent2:#7c5cff; --green:#2ea043; --red:#f85149; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:var(--bg); color:var(--text); font-family:"Microsoft YaHei","PingFang SC",sans-serif; }
  .header { padding:18px 32px; border-bottom:1px solid var(--border); background:linear-gradient(90deg,#0d1117,#131a2a); display:flex; justify-content:space-between; }
  .logo { font-size:22px; font-weight:700; background:linear-gradient(90deg,var(--accent),var(--accent2)); -webkit-background-clip:text; background-clip:text; color:transparent; }
  .logo small { display:block; font-size:12px; color:var(--muted); -webkit-text-fill-color:var(--muted); font-weight:400; }
  .user { color:var(--muted); font-size:13px; align-self:center; }
  .container { max-width:1100px; margin:0 auto; padding:22px 32px; }
  .stat-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:16px; }
  .stat-box { background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:16px; text-align:center; }
  .stat-num { font-size:28px; font-weight:700; color:var(--accent); }
  .stat-label { font-size:12px; color:var(--muted); margin-top:4px; }
  .weak-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:16px; }
  .weak-card { background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:16px; min-height:130px; }
  .weak-title { font-size:14px; font-weight:600; }
  .weak-sub { font-size:11px; color:var(--muted); margin:2px 0 10px; }
  .wrow { display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px dashed var(--border); font-size:13px; }
  .wrow:last-child { border-bottom:none; }
  .weak-count { background:rgba(79,142,247,.15); color:var(--accent); border-radius:10px; padding:1px 9px; font-size:12px; font-weight:600; }
  .weak-empty { color:var(--muted); font-size:12px; padding:12px 0; text-align:center; }
  .panel { background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:18px; margin-bottom:16px; }
  .panel h3 { font-size:15px; margin-bottom:12px; }
  .tag { display:inline-block; padding:3px 10px; border-radius:12px; font-size:12px; background:rgba(79,142,247,.12); color:var(--accent); border:1px solid var(--accent); margin:2px 4px 2px 0; }
  .tag.type { background:rgba(248,81,73,.15); color:var(--red); border-color:var(--red); }
  .row { display:flex; justify-content:space-between; padding:10px 14px; border-bottom:1px solid var(--border); font-size:13px; }
  .muted { color:var(--muted); font-size:12px; }
  .fold-card { background:var(--panel); border:1px solid var(--border); border-radius:12px; margin-bottom:14px; overflow:hidden; }
  .fold-head { display:flex; justify-content:space-between; align-items:center; padding:14px 18px; }
  .fold-title { font-size:15px; font-weight:600; }
  .fold-badge { background:rgba(79,142,247,.15); color:var(--accent); border-radius:12px; padding:2px 12px; font-size:12px; font-weight:600; margin-left:8px; }
  .fold-body { padding:4px 18px 18px; }
  .fold-closed-hint { color:var(--muted); font-size:12px; }
  .arc-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; }
  .arc-card { background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:16px; }
  .arc-card .t { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
  .arc-card .cause { font-size:12px; color:var(--muted); line-height:1.6; margin-bottom:8px; }
  .arc-card .code-preview { background:#0a0e14; border:1px solid var(--border); border-radius:8px; padding:8px 10px; font-family:Consolas,monospace; font-size:11px; line-height:1.5; color:#a5d6ff; white-space:pre-wrap; overflow:hidden; max-height:108px; margin-top:6px; }
  .arc-card .foot { display:flex; justify-content:space-between; margin-top:10px; font-size:11px; color:var(--muted); }
  .arc-card .tags { margin-top:8px; }
  .arc-card .tags .tag { font-size:11px; padding:2px 8px; }
  .arc-card .code-block { background:#0a0e14; border:1px solid var(--border); border-radius:8px; padding:10px; font-family:Consolas,monospace; font-size:11.5px; line-height:1.5; white-space:pre-wrap; color:#a5d6ff; margin-top:8px; }
</style></head><body>
<div class="header"><div class="logo">CodeTutor<small>我的档案 · 个人错题数据资产</small></div><div class="user">👤 demo</div></div>
<div class="container">
  <div class="stat-grid">
    <div class="stat-box"><div class="stat-num">%(total)s</div><div class="stat-label">错题总数</div></div>
    <div class="stat-box"><div class="stat-num">%(total_24h)s</div><div class="stat-label">今日新增</div></div>
    <div class="stat-box"><div class="stat-num">%(due_today)s</div><div class="stat-label">今日待复习</div></div>
    <div class="stat-box"><div class="stat-num">%(type_count)s</div><div class="stat-label">覆盖错误类型</div></div>
  </div>
  <div class="weak-grid">
    <div class="weak-card"><div class="weak-title">⚡ 近 24 小时薄弱点</div><div class="weak-sub">最新的问题</div>%(weak24h)s</div>
    <div class="weak-card"><div class="weak-title">📈 近 7 天薄弱点</div><div class="weak-sub">近期趋势</div>%(weak7d)s</div>
    <div class="weak-card"><div class="weak-title">🧱 历史累计薄弱点</div><div class="weak-sub">长期顽疾</div>%(weakall)s</div>
  </div>
  <div class="panel"><h3>📅 今日到期复习(艾宾浩斯调度)</h3>%(review)s</div>
  <h3 style="margin:6px 0 12px;">📚 错题档案(点击查看)</h3>
  <div class="fold-card">
    <div class="fold-head"><span class="fold-title">⚡ 近 24 小时错题<span class="fold-badge">%(n24h)s 条</span></span><span class="muted">▼ 已展开</span></div>
    <div class="fold-body"><div class="arc-grid">%(history24)s</div></div>
  </div>
  <div class="fold-card">
    <div class="fold-head"><span class="fold-title">🧱 历史累计错题<span class="fold-badge">%(nall)s 条</span></span><span class="fold-closed-hint">▶ 点击展开</span></div>
  </div>
</div></body></html>"""


def _weak_rows(items):
    if not items:
        return '<div class="weak-empty">暂无数据</div>'
    return "".join('<div class="wrow"><span>%s</span><span class="weak-count">× %d</span></div>'
                   % (esc(w["tag"]), w["count"]) for w in items)


def render_archive():
    from codetutor.memory import archive
    stats = archive.get_stats()
    # 近24小时档案件展开显示前 6 条;历史累计档案件收起(仅显示条数徽标)
    history24 = [archive.get_mistake(m["id"]) for m in archive.list_mistakes(hours=24)[:6]]
    reviews = archive.get_due_reviews()

    review_html = "".join(
        '<div class="row"><span>#%d [%s] %s</span><span class="muted">待复习</span></div>'
        % (it["id"], esc(it["error_type"]), esc((it["root_cause"] or "")[:40]))
        for it in reviews) or '<div class="muted">🎉 今天没有到期的复习任务</div>'

    def arc_card(it, open_detail=False):
        tags = "".join('<span class="tag">%s</span>' % esc(t)
                       for t in (it["knowledge_tags"] or [])[:3])
        # 卡片直接展示完整根因 + 代码片段预览,信息完整
        code_preview = "\n".join((it["code_snapshot"] or "").split("\n")[:6])
        preview = ('<div class="code-preview">%s</div>' % esc(code_preview)) if code_preview else ""
        return ('<div class="arc-card"><div class="t"><span class="tag type">%s</span></div>'
                '<div class="cause">%s</div>%s<div class="tags">%s</div>'
                '<div class="foot"><span>#%d · %s</span><span>掌握度 %d</span></div></div>'
                % (esc(it["error_type"]), esc(it["root_cause"] or "(根因见详情)"),
                   preview, tags, it["id"], esc(it["created_at"][:16]), it["mastery"]))

    history24_html = "".join(arc_card(it, open_detail=(i == 0))
                             for i, it in enumerate(history24)) or '<div class="muted">暂无档案</div>'

    return ARCHIVE_PAGE % {
        "total": stats["total"], "total_24h": stats["total_24h"],
        "due_today": stats["due_today"], "type_count": len(stats["by_error_type"]),
        "weak24h": _weak_rows(stats["weak_24h"]), "weak7d": _weak_rows(stats["weak_7d"]),
        "weakall": _weak_rows(stats["weak_all"]),
        "review": review_html,
        "n24h": stats["total_24h"], "nall": stats["total"],
        "history24": history24_html,
    }


def main():
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
    os.makedirs(out_dir, exist_ok=True)

    # archive-only 模式:只刷新档案页快照(不调用 LLM、不新增档案数据)
    if len(sys.argv) > 1 and sys.argv[1] == "archive-only":
        archive_path = os.path.join(out_dir, "archive_snapshot.html")
        with open(archive_path, "w", encoding="utf-8") as f:
            f.write(render_archive())
        print("已生成(仅档案页): %s" % archive_path)
        return

    case_idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    case = CASES[case_idx]
    print("生成演示快照: %s" % case["name"])
    orch = Orchestrator()
    result = orch.analyze(case["code"], case["symptom"])
    # 快照需展示完整能力:单独触发一次按需出题
    quiz_result = orch.quiz(result["archive_id"])
    result["quiz"] = quiz_result.get("questions", [])
    result["steps"] += quiz_result.get("steps", [])
    html_text = render(result, case["name"], case["symptom"])
    out_path = os.path.join(out_dir, "demo_snapshot.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_text)
    print("已生成: %s" % out_path)

    archive_path = os.path.join(out_dir, "archive_snapshot.html")
    with open(archive_path, "w", encoding="utf-8") as f:
        f.write(render_archive())
    print("已生成: %s" % archive_path)


if __name__ == "__main__":
    main()
