# -*- coding: utf-8 -*-
"""个人 Bug 档案:多用户体系 + SQLite 长期记忆 + 艾宾浩斯复习调度。

- users 表:用户名 + 加盐密码哈希(标准库实现,零依赖);
- mistakes 表带 user_id:每个用户的错题档案完全隔离;
- 复习调度:掌握阶段沿艾宾浩斯间隔 [1,2,4,7,15] 天推进,复习通过则升一级;
- 统计支持时间窗(近24小时/近7天/历史累计),用于薄弱点对比卡片。
"""
import datetime
import hashlib
import json
import os
import secrets
import sqlite3

import config

EBBINGHAUS_DAYS = [1, 2, 4, 7, 15]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mistakes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    language TEXT DEFAULT 'python',
    error_type TEXT,
    error_key TEXT,
    knowledge_tags TEXT,
    code_snapshot TEXT,
    fixed_code TEXT,
    root_cause TEXT,
    verified INTEGER DEFAULT 0,
    mastery INTEGER DEFAULT 0,
    review_stage INTEGER DEFAULT 0,
    next_review_at TEXT,
    review_count INTEGER DEFAULT 0
);
"""


def _conn():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    # timeout=30:busy_timeout,等待写锁,避免多进程并发写时立刻报错
    conn = sqlite3.connect(config.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as conn:
        conn.executescript(_SCHEMA)
        _migrate(conn)


def _migrate(conn):
    """老库升级:mistakes 表补 user_id 列,旧数据归到内置 demo 用户。"""
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(mistakes)").fetchall()]
    if "user_id" not in cols:
        conn.execute("ALTER TABLE mistakes ADD COLUMN user_id INTEGER DEFAULT 0")
    # 内置演示用户(demo / demo123),旧数据归属它
    row = conn.execute("SELECT id FROM users WHERE username='demo'").fetchone()
    if not row:
        salt = secrets.token_hex(8)
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, created_at) VALUES (?,?,?,?)",
            ("demo", _hash("demo123", salt), salt,
             datetime.datetime.now().isoformat(timespec="seconds")))
        demo_id = conn.execute("SELECT id FROM users WHERE username='demo'").fetchone()["id"]
        conn.execute("UPDATE mistakes SET user_id=? WHERE user_id=0", (demo_id,))


def _hash(password, salt):
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# 用户系统
# ---------------------------------------------------------------------------

def register(username, password):
    """注册。返回 (ok, msg_or_user_id)。"""
    username = (username or "").strip()
    if not (3 <= len(username) <= 20):
        return False, "用户名需 3-20 个字符"
    if not (6 <= len(password or "") <= 64):
        return False, "密码需 6-64 个字符"
    init_db()
    with _conn() as conn:
        if conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            return False, "用户名已被占用"
        salt = secrets.token_hex(8)
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, salt, created_at) VALUES (?,?,?,?)",
            (username, _hash(password, salt), salt,
             datetime.datetime.now().isoformat(timespec="seconds")))
        return True, cur.lastrowid


def verify(username, password):
    """登录校验。成功返回 user_id,失败返回 None。"""
    init_db()
    with _conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=?",
                           ((username or "").strip(),)).fetchone()
        if row and row["password_hash"] == _hash(password or "", row["salt"]):
            return row["id"]
    return None


def get_username(user_id):
    init_db()
    with _conn() as conn:
        row = conn.execute("SELECT username FROM users WHERE id=?", (user_id,)).fetchone()
        return row["username"] if row else None


def _next_review_time(stage):
    days = EBBINGHAUS_DAYS[min(stage, len(EBBINGHAUS_DAYS) - 1)]
    return (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()


def add_mistake(error_type, error_key, knowledge_tags, code_snapshot,
                fixed_code, root_cause, verified, language="python", user_id=0):
    """归档一条错题,返回记录 id。"""
    init_db()
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO mistakes
               (user_id, created_at, language, error_type, error_key, knowledge_tags,
                code_snapshot, fixed_code, root_cause, verified, next_review_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, datetime.datetime.now().isoformat(timespec="seconds"), language,
             error_type, error_key, json.dumps(knowledge_tags, ensure_ascii=False),
             code_snapshot, fixed_code, root_cause, 1 if verified else 0,
             _next_review_time(0)),
        )
        return cur.lastrowid


def get_due_reviews(user_id=None, limit=20):
    """取出到期的复习任务(可按用户过滤)。"""
    init_db()
    now = datetime.datetime.now().isoformat()
    sql = ("SELECT * FROM mistakes WHERE next_review_at <= ? AND mastery < ?")
    args = [now, len(EBBINGHAUS_DAYS)]
    if user_id is not None:
        sql += " AND user_id = ?"
        args.append(user_id)
    sql += " ORDER BY next_review_at LIMIT ?"
    args.append(limit)
    with _conn() as conn:
        rows = conn.execute(sql, args).fetchall()
    return [dict(r) for r in rows]


def mark_reviewed(mistake_id, passed):
    """复习打卡:通过则掌握度+1、进入下一复习阶段;未通过则回到第一阶段。"""
    init_db()
    with _conn() as conn:
        row = conn.execute("SELECT * FROM mistakes WHERE id=?",
                           (mistake_id,)).fetchone()
        if not row:
            return None
        if passed:
            stage = row["review_stage"] + 1
            mastery = row["mastery"] + 1
        else:
            stage, mastery = 0, max(0, row["mastery"] - 1)
        conn.execute(
            "UPDATE mistakes SET mastery=?, review_stage=?, next_review_at=?,"
            " review_count=review_count+1 WHERE id=?",
            (mastery, stage, _next_review_time(stage), mistake_id))
        return {"mastery": mastery, "review_stage": stage}


def _weak_points(user_id, hours=None, top=5):
    """薄弱知识点统计:按时间窗(近24h/近7天/全部)聚合标签出现次数。"""
    init_db()
    sql = "SELECT knowledge_tags, mastery FROM mistakes WHERE 1=1"
    args = []
    if user_id is not None:
        sql += " AND user_id=?"
        args.append(user_id)
    if hours is not None:
        since = (datetime.datetime.now() - datetime.timedelta(hours=hours)).isoformat()
        sql += " AND created_at >= ?"
        args.append(since)
    with _conn() as conn:
        rows = conn.execute(sql, args).fetchall()
    tag_count, tag_mastery = {}, {}
    for r in rows:
        for t in json.loads(r["knowledge_tags"] or "[]"):
            tag_count[t] = tag_count.get(t, 0) + 1
            tag_mastery.setdefault(t, []).append(r["mastery"])
    ranked = sorted(tag_count.items(), key=lambda kv: -kv[1])[:top]
    return [{"tag": t, "count": c,
             "avg_mastery": round(sum(tag_mastery[t]) / len(tag_mastery[t]), 2)}
            for t, c in ranked]


def get_stats(user_id=None):
    """学情统计(支持按用户隔离):
    总量、已验证修复率、错误类型分布,以及三档时间窗薄弱点对比:
    近24小时(最新问题)/ 近7天(近期趋势)/ 历史累计(长期顽疾)。"""
    init_db()
    sql_where = " WHERE user_id=?" if user_id is not None else ""
    args = [user_id] if user_id is not None else []
    with _conn() as conn:
        total = conn.execute("SELECT COUNT(*) c FROM mistakes" + sql_where, args).fetchone()["c"]
        verified = conn.execute(
            "SELECT COUNT(*) c FROM mistakes" + sql_where +
            (" AND" if user_id is not None else " WHERE") + " verified=1",
            args).fetchone()["c"]
        by_type = conn.execute(
            "SELECT error_type, COUNT(*) c FROM mistakes" + sql_where +
            " GROUP BY error_type ORDER BY c DESC", args).fetchall()
    return {
        "total": total,
        "verified": verified,
        "verified_rate": round(verified / total * 100, 1) if total else 0.0,
        "by_error_type": {r["error_type"]: r["c"] for r in by_type},
        "weak_24h": _weak_points(user_id, hours=24),
        "weak_7d": _weak_points(user_id, hours=24 * 7),
        "weak_all": _weak_points(user_id, hours=None),
        "total_24h": count_mistakes(user_id, hours=24),
        "due_today": len(get_due_reviews(user_id)),
    }


def list_mistakes(user_id=None, limit=50, hours=None):
    """错题列表(支持用户隔离 + 时间窗过滤,hours=24 即近24小时)。"""
    init_db()
    sql = ("SELECT id, created_at, error_type, knowledge_tags, mastery, verified,"
           " root_cause, code_snapshot FROM mistakes WHERE 1=1")
    args = []
    if user_id is not None:
        sql += " AND user_id=?"
        args.append(user_id)
    if hours is not None:
        since = (datetime.datetime.now() - datetime.timedelta(hours=hours)).isoformat()
        sql += " AND created_at >= ?"
        args.append(since)
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    with _conn() as conn:
        rows = conn.execute(sql, args).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["knowledge_tags"] = json.loads(d["knowledge_tags"] or "[]")
        out.append(d)
    return out


def count_mistakes(user_id=None, hours=None):
    """错题计数(用于卡片标题徽标)。"""
    init_db()
    sql = "SELECT COUNT(*) c FROM mistakes WHERE 1=1"
    args = []
    if user_id is not None:
        sql += " AND user_id=?"
        args.append(user_id)
    if hours is not None:
        since = (datetime.datetime.now() - datetime.timedelta(hours=hours)).isoformat()
        sql += " AND created_at >= ?"
        args.append(since)
    with _conn() as conn:
        return conn.execute(sql, args).fetchone()["c"]


def get_mistake(mistake_id):
    """取出单条错题档案的完整内容(用于详情查看)。"""
    init_db()
    with _conn() as conn:
        row = conn.execute("SELECT * FROM mistakes WHERE id=?",
                           (mistake_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["knowledge_tags"] = json.loads(d["knowledge_tags"] or "[]")
    return d
