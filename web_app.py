# -*- coding: utf-8 -*-
"""CodeTutor Web 界面(Flask,多用户版)。

启动: py web_app.py  然后浏览器访问 http://127.0.0.1:5050
- 未登录访问自动跳转登录页;
- 每个用户的错题档案/薄弱点/复习计划完全隔离。
"""
import functools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from flask import Flask, jsonify, redirect, render_template, request, session

from codetutor.memory import archive
from codetutor.orchestrator import Orchestrator

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"))
app.secret_key = os.environ.get("CODETUTOR_SECRET", "codetutor-dev-secret-2026")
orch = Orchestrator()

# 后台预热 LLM 连接,消除首个真实请求的冷启动延迟
import threading as _threading
from codetutor.llm import warmup as _llm_warmup
_threading.Thread(target=_llm_warmup, daemon=True).start()


def login_required(view):
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "未登录", "need_login": True}), 401
            return redirect("/login")
        return view(*args, **kwargs)
    return wrapper


# ---------------- 页面 ----------------

@app.route("/login")
def login_page():
    if session.get("user_id"):
        return redirect("/")
    return render_template("login.html")


@app.route("/")
@login_required
def index():
    return render_template("index.html", mock_mode=orch.mock_mode,
                           username=session.get("username"))


# ---------------- 认证 API ----------------

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(force=True)
    ok, result = archive.register(data.get("username"), data.get("password"))
    if not ok:
        return jsonify({"error": result}), 400
    session["user_id"] = result
    session["username"] = data["username"].strip()
    return jsonify({"ok": True, "username": session["username"]})


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    uid = archive.verify(data.get("username"), data.get("password"))
    if not uid:
        return jsonify({"error": "用户名或密码错误"}), 401
    session["user_id"] = uid
    session["username"] = data["username"].strip()
    return jsonify({"ok": True, "username": session["username"]})


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


# ---------------- 业务 API(均需登录,数据按用户隔离) ----------------

@app.route("/api/analyze", methods=["POST"])
@login_required
def analyze():
    data = request.get_json(force=True)
    code = (data.get("code") or "").strip()
    error_text = (data.get("error") or "").strip()
    if not code:
        return jsonify({"error": "请粘贴问题代码"}), 400
    result = orch.analyze(code, error_text, user_id=session["user_id"])
    return jsonify(result)


@app.route("/api/quiz", methods=["POST"])
@login_required
def quiz():
    data = request.get_json(force=True)
    archive_id = data.get("archive_id")
    if not archive_id:
        return jsonify({"error": "缺少 archive_id"}), 400
    # 只能为自己的档案出题
    record = archive.get_mistake(int(archive_id))
    if not record or record["user_id"] != session["user_id"]:
        return jsonify({"error": "档案不存在或无权访问"}), 403
    return jsonify(orch.quiz(int(archive_id)))


@app.route("/api/stats")
@login_required
def stats():
    return jsonify(archive.get_stats(session["user_id"]))


@app.route("/api/history")
@login_required
def history():
    hours = request.args.get("hours", type=int)
    # limit 提到 500,避免档案多时被截断
    return jsonify(archive.list_mistakes(session["user_id"], hours=hours, limit=500))


@app.route("/api/mistake/<int:mid>")
@login_required
def mistake_detail(mid):
    m = archive.get_mistake(mid)
    if not m or m["user_id"] != session["user_id"]:
        return jsonify({"error": "档案不存在或无权访问"}), 404
    return jsonify(m)


@app.route("/api/review")
@login_required
def review():
    return jsonify(archive.get_due_reviews(session["user_id"]))


@app.route("/api/review_done", methods=["POST"])
@login_required
def review_done():
    data = request.get_json(force=True)
    record = archive.get_mistake(int(data["id"]))
    if not record or record["user_id"] != session["user_id"]:
        return jsonify({"error": "档案不存在或无权访问"}), 404
    return jsonify(archive.mark_reviewed(int(data["id"]), bool(data.get("passed"))))


if __name__ == "__main__":
    # 本地默认 5050;云平台(Render 等)用环境变量 PORT 并绑定 0.0.0.0
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=False)
