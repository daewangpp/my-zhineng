# -*- coding: utf-8 -*-
"""GitHub 部署脚本:建仓库 → 推送代码 → 开启 Pages。

全程走 api.github.com(REST),绕开 github.com 的 git 推送端口问题。
安全:推送前对 config.py 脱敏(不含真实 Key)。
"""
import base64
import os
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")

TOKEN = os.environ.get("GITHUB_TOKEN", "")  # 用前:set GITHUB_TOKEN=ghp_xxx
OWNER = "daewangpp"
REPO = "my-zhineng"
API = "https://api.github.com"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # codetutor/

H = {"Authorization": "Bearer " + TOKEN,
     "Accept": "application/vnd.github+json",
     "User-Agent": "codetutor-deploy"}

# 排除规则(不推送这些)
EXCLUDE_DIRS = {".git", "data", "dist", "__pycache__", ".vscode"}
EXCLUDE_FILES = {"cloudflared.exe"}
EXCLUDE_EXT = {".pyc", ".log"}


def api(method, path, **kw):
    r = requests.request(method, API + path, headers=H, timeout=30, **kw)
    return r


def collect_files():
    files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            if fn in EXCLUDE_FILES or os.path.splitext(fn)[1] in EXCLUDE_EXT:
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, ROOT).replace("\\", "/")
            files.append((full, rel))
    return files


def main():
    if not TOKEN:
        print("请先设置环境变量: set GITHUB_TOKEN=ghp_你的令牌")
        return
    # 1. 创建仓库(若已存在则忽略)
    r = api("POST", "/user/repos", json={
        "name": REPO, "private": False,
        "description": "CodeTutor · 程序员的 AI 错题搭子(多智能体编程学习系统)"})
    if r.status_code == 201:
        print("✔ 仓库已创建: %s" % r.json()["html_url"])
    elif r.status_code == 422:
        print("· 仓库已存在,直接推送")
    else:
        print("✘ 建仓库失败: %s %s" % (r.status_code, r.text[:300])); return

    # 2. 先用 Contents API 初始化仓库(空仓库无法用 Git Data API)
    init_content = base64.b64encode(
        "# CodeTutor\n\n程序员的 AI 错题搭子 · 多智能体编程学习系统\n".encode("utf-8")).decode("ascii")
    ri = api("PUT", "/repos/%s/%s/contents/README.md" % (OWNER, REPO),
             json={"message": "init", "content": init_content})
    if ri.status_code in (200, 201):
        print("✔ 仓库已初始化")
    else:
        print("· 初始化返回 %s(仓库可能已非空,继续)" % ri.status_code)

    # 3. 收集文件并逐个创建 blob
    files = collect_files()
    print("共 %d 个文件待推送" % len(files))

    # 获取当前 master 的 commit/tree(作为增量基础)
    base_tree, parent_commit = None, []
    rg = api("GET", "/repos/%s/%s/git/refs/heads/master" % (OWNER, REPO))
    if rg.status_code == 200:
        parent_commit = [rg.json()["object"]["sha"]]
        rc0 = api("GET", "/repos/%s/%s/git/commits/%s" % (OWNER, REPO, parent_commit[0]))
        if rc0.status_code == 200:
            base_tree = rc0.json()["tree"]["sha"]
    tree_items = []
    for i, (full, rel) in enumerate(files, 1):
        with open(full, "rb") as f:
            content = f.read()
        # config.py 脱敏:移除真实 Key
        if rel == "config.py":
            text = content.decode("utf-8")
            import re as _re
            text = _re.sub(r'"sk-[A-Za-z0-9]+"', '""', text)
            content = text.encode("utf-8")
        b64 = base64.b64encode(content).decode("ascii")
        rb = api("POST", "/repos/%s/%s/git/blobs" % (OWNER, REPO),
                 json={"content": b64, "encoding": "base64"})
        if rb.status_code != 201:
            print("  ✘ blob 失败 %s: %s" % (rel, rb.text[:150])); continue
        tree_items.append({"path": rel, "mode": "100644",
                           "type": "blob", "sha": rb.json()["sha"]})
        if i % 10 == 0:
            print("  ...blob %d/%d" % (i, len(files)))

    # 3. 创建 tree
    rt = api("POST", "/repos/%s/%s/git/trees" % (OWNER, REPO),
             json={"tree": tree_items})
    if rt.status_code != 201:
        print("✘ tree 失败: %s" % rt.text[:300]); return
    tree_sha = rt.json()["sha"]

    # 4. 创建 commit
    rc = api("POST", "/repos/%s/%s/git/commits" % (OWNER, REPO),
             json={"message": "CodeTutor: 多智能体编程错题学习搭子 + Pages 演示站",
                   "tree": tree_sha, "parents": []})
    if rc.status_code != 201:
        print("✘ commit 失败: %s" % rc.text[:300]); return
    commit_sha = rc.json()["sha"]

    # 5. 创建/更新 master 分支引用
    rr = api("POST", "/repos/%s/%s/git/refs" % (OWNER, REPO),
             json={"ref": "refs/heads/master", "sha": commit_sha})
    if rr.status_code == 422:  # 已存在则更新
        rr = api("PATCH", "/repos/%s/%s/git/refs/heads/master" % (OWNER, REPO),
                 json={"sha": commit_sha, "force": True})
    if rr.status_code not in (200, 201):
        print("✘ ref 失败: %s" % rr.text[:300]); return
    print("✔ 代码已推送到 master")

    # 6. 开启 GitHub Pages(source: master 分支 /docs 目录)
    rp = api("POST", "/repos/%s/%s/pages" % (OWNER, REPO),
             json={"source": {"branch": "master", "path": "/docs"}})
    if rp.status_code in (201, 204):
        print("✔ GitHub Pages 已开启")
    elif rp.status_code == 409:
        print("· Pages 已开启过")
    else:
        print("· Pages 开启返回 %s(可能需在仓库设置里手动开): %s" % (rp.status_code, rp.text[:200]))

    print("\n部署完成!访问地址:")
    print("  仓库: https://github.com/%s/%s" % (OWNER, REPO))
    print("  演示站: https://%s.github.io/%s/" % (OWNER, REPO))
    print("(Pages 构建需 1-2 分钟,首次访问稍等)")


if __name__ == "__main__":
    main()
