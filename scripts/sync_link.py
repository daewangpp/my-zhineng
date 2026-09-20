# -*- coding: utf-8 -*-
"""链接同步:隧道域名变化后,一键同步所有材料中的公网地址。

用法: py scripts/sync_link.py https://新域名.trycloudflare.com

自动完成:
1. 更新《03_参赛申报书.md》中的访问链接
2. 更新《README.md》中的访问链接
3. 重写 reports/current_url.txt(当前域名记录)
4. 重新生成二维码(PNG + SVG)
5. 重新打包提交材料(dist/)
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # codetutor/
WORKSPACE = os.path.dirname(ROOT)                                    # 智能体/
URL_FILE = os.path.join(ROOT, "reports", "current_url.txt")

FILES_TO_SYNC = [
    os.path.join(WORKSPACE, "03_参赛申报书.md"),
    os.path.join(ROOT, "README.md"),
]

URL_PATTERN = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def sync_files(new_url):
    for path in FILES_TO_SYNC:
        if not os.path.exists(path):
            print("  跳过(不存在): %s" % path)
            continue
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        new_text, n = URL_PATTERN.subn(new_url, text)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_text)
        print("  ✔ %s 更新 %d 处链接" % (os.path.basename(path), n))


def save_url(new_url):
    os.makedirs(os.path.dirname(URL_FILE), exist_ok=True)
    with open(URL_FILE, "w", encoding="utf-8") as f:
        f.write(new_url)
    print("  ✔ current_url.txt 已记录新域名")


def regen_qrcode(new_url):
    import qrcode
    import qrcode.image.svg
    out_dir = os.path.join(ROOT, "reports")
    img = qrcode.make(new_url, box_size=12, border=2)
    img.save(os.path.join(out_dir, "qrcode_link.png"))
    svg_img = qrcode.make(new_url, image_factory=qrcode.image.svg.SvgImage,
                          box_size=12, border=2)
    with open(os.path.join(out_dir, "qrcode_link.svg"), "wb") as f:
        svg_img.save(f)
    print("  ✔ 二维码已重新生成(PNG + SVG)")


def repackage():
    import subprocess
    script = os.path.join(ROOT, "scripts", "package_submission.py")
    subprocess.run([sys.executable, script], cwd=ROOT, check=True)
    print("  ✔ 提交包已重新打包")


def main():
    if len(sys.argv) < 2 or not sys.argv[1].startswith("https://"):
        print("用法: py scripts/sync_link.py https://新域名.trycloudflare.com")
        sys.exit(1)
    new_url = sys.argv[1].rstrip("/")
    print("同步新域名: %s" % new_url)
    sync_files(new_url)
    save_url(new_url)
    regen_qrcode(new_url)
    repackage()
    print("\n全部同步完成,申报书/README/二维码/提交包均已使用新域名。")


if __name__ == "__main__":
    main()
