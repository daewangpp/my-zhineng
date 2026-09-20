# -*- coding: utf-8 -*-
"""一键打包提交材料。

生成: dist/CodeTutor_提交材料/
├── 01_项目申报书/        申报书 md + 可打印 HTML(浏览器打开 Ctrl+P 另存 PDF)
├── 02_源代码/codetutor/  干净代码(已脱敏 API Key、清理缓存)
├── 03_演示证据/          3 张系统截图 + 实验评估报告
├── 04_演示视频/          空目录,放入你录好的 mp4
└── 提交说明.txt
"""
import os
import re
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # codetutor/
WORKSPACE = os.path.dirname(ROOT)                                    # 智能体/
DIST = os.path.join(WORKSPACE, "dist", "CodeTutor_提交材料")


def safe_copytree(src, dst):
    """复制源码,排除缓存与运行数据。"""
    def ignore(dir_, names):
        return [n for n in names
                if n in ("__pycache__", "data", "dist", ".git",
                         "package_submission.py",   # 打包工具自身不进提交包
                         "cloudflared.exe")          # 隧道二进制(52MB)不属于源代码
                or n.endswith(".pyc")]
    shutil.copytree(src, dst, ignore=ignore)


def desensitize_config(dst_root):
    """将提交版 config.py 中的真实 Key 替换为占位符。"""
    cfg = os.path.join(dst_root, "config.py")
    with open(cfg, "r", encoding="utf-8") as f:
        text = f.read()
    text = text.replace(
        'API_KEY = os.environ.get("CODETUTOR_API_KEY",\n'
        '                         "sk-3FNzA6cM3w9VMnFsuuKGRO9HeCCYWdyPQrbJ9zgXfnlzvlvV")',
        'API_KEY = os.environ.get("CODETUTOR_API_KEY", "")  # 请填入你的 API Key')
    with open(cfg, "w", encoding="utf-8") as f:
        f.write(text)
    # 校验:真实 key 不得残留
    with open(cfg, "r", encoding="utf-8") as f:
        assert "sk-3FNzA6" not in f.read(), "Key 脱敏失败!"
    print("  ✔ config.py 已脱敏(真实 Key 不会进入提交包)")


def md_to_html(md_text, title):
    """极简 Markdown → 可打印 HTML(覆盖申报书用到的语法)。"""
    lines = md_text.split("\n")
    out, in_table, in_code = [], False, False
    for ln in lines:
        if ln.strip().startswith("```"):
            if in_code:
                out.append("</pre>")
                in_code = False
            else:
                out.append("<pre>")
                in_code = True
            continue
        if in_code:
            out.append(ln.replace("&", "&amp;").replace("<", "&lt;"))
            continue
        s = ln.strip()
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue
            if not in_table:
                out.append("<table border='1' cellspacing='0' cellpadding='6'>")
                in_table = True
                out.append("<tr>" + "".join("<th>%s</th>" % c for c in cells) + "</tr>")
            else:
                out.append("<tr>" + "".join("<td>%s</td>" % c for c in cells) + "</tr>")
            continue
        elif in_table:
            out.append("</table>")
            in_table = False
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        if s.startswith("#### "):
            out.append("<h4>%s</h4>" % s[5:])
        elif s.startswith("### "):
            out.append("<h3>%s</h3>" % s[4:])
        elif s.startswith("## "):
            out.append("<h2>%s</h2>" % s[3:])
        elif s.startswith("# "):
            out.append("<h1>%s</h1>" % s[2:])
        elif s.startswith("> "):
            out.append("<blockquote>%s</blockquote>" % s[2:])
        elif s.startswith("- "):
            out.append("<li>%s</li>" % s[2:])
        elif s == "---":
            out.append("<hr>")
        elif s:
            out.append("<p>%s</p>" % s)
        else:
            out.append("")
    if in_table:
        out.append("</table>")
    return ("""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>%s</title><style>
body{font-family:"Microsoft YaHei",serif;max-width:800px;margin:40px auto;padding:0 20px;line-height:1.9;color:#222}
h1{font-size:22px;border-bottom:2px solid #333;padding-bottom:8px}
h2{font-size:18px;margin-top:28px;border-left:4px solid #4f8ef7;padding-left:10px}
h3{font-size:16px;margin-top:20px}
table{border-collapse:collapse;margin:12px 0;width:100%%;font-size:14px}
th{background:#f0f4fa} blockquote{background:#f7f7f7;border-left:4px solid #ccc;padding:8px 14px;color:#555}
code{background:#f0f0f0;padding:1px 5px;border-radius:4px;font-size:13px}
pre{background:#f6f8fa;padding:14px;border-radius:8px;font-size:12.5px;overflow-x:auto}
li{margin:4px 0} hr{border:none;border-top:1px solid #ddd;margin:20px 0}
</style></head><body>%s</body></html>""" % (title, "\n".join(out)))


def main():
    if os.path.exists(DIST):
        shutil.rmtree(DIST)

    # ① 申报书
    doc_dir = os.path.join(DIST, "01_项目申报书")
    os.makedirs(doc_dir)
    md_path = os.path.join(WORKSPACE, "03_参赛申报书.md")
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()
    shutil.copy(md_path, os.path.join(doc_dir, "CodeTutor_参赛申报书.md"))
    with open(os.path.join(doc_dir, "CodeTutor_参赛申报书_可打印.html"), "w", encoding="utf-8") as f:
        f.write(md_to_html(md_text, "CodeTutor 参赛申报书"))
    print("✔ 01_项目申报书(md + 可打印 html)")

    # ② 源代码(脱敏)
    code_dir = os.path.join(DIST, "02_源代码")
    os.makedirs(code_dir)
    safe_copytree(ROOT, os.path.join(code_dir, "codetutor"))
    desensitize_config(os.path.join(code_dir, "codetutor"))
    print("✔ 02_源代码(已清理缓存与运行数据)")

    # ③ 演示证据
    evi_dir = os.path.join(DIST, "03_演示证据")
    os.makedirs(evi_dir)
    shots = os.path.join(ROOT, "reports", "screenshots")
    for name in sorted(os.listdir(shots)):
        if name.endswith(".png"):
            shutil.copy(os.path.join(shots, name), evi_dir)
    shutil.copy(os.path.join(ROOT, "reports", "evaluation_report.md"), evi_dir)
    # 公网访问二维码(PNG,可直接插入 PPT)
    qr = os.path.join(ROOT, "reports", "qrcode_link.png")
    if os.path.exists(qr):
        shutil.copy(qr, evi_dir)
    print("✔ 03_演示证据(截图 + 评估报告 + 访问二维码)")

    # ④ 视频目录
    video_dir = os.path.join(DIST, "04_演示视频")
    os.makedirs(video_dir)
    with open(os.path.join(video_dir, "把演示视频放这里.txt"), "w", encoding="utf-8") as f:
        f.write("将录制好的演示视频(建议 90 秒,mp4)重命名为 CodeTutor_演示视频.mp4 后放入本目录。\n"
                "录制方法:py web_app.py 启动后访问 http://127.0.0.1:5050/?demo=0 自动演示。\n")

    # 提交说明
    with open(os.path.join(DIST, "提交说明.txt"), "w", encoding="utf-8") as f:
        f.write("""CodeTutor · 程序员的 AI 错题搭子 —— 提交材料清单

01_项目申报书/    申报书(用浏览器打开 html 版,Ctrl+P 另存为 PDF 提交)
02_源代码/        完整可运行代码,运行方法见其中 README.md
03_演示证据/      系统截图 3 张 + 实验评估报告
04_演示视频/      演示视频 mp4(待放入)

本地复现:进入 02_源代码/codetutor,安装 requests、flask,
在 config.py 填入任意 OpenAI 兼容接口的 Key,运行 py web_app.py。
""")
    print("✔ 提交说明.txt")
    print("\n打包完成: %s" % DIST)


if __name__ == "__main__":
    main()
