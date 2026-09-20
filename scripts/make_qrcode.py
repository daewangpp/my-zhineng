# -*- coding: utf-8 -*-
"""生成公网访问二维码(PNG + SVG),用于答辩 PPT / 海报。"""
import os
import sys

import qrcode
import qrcode.image.svg

sys.stdout.reconfigure(encoding="utf-8")

URL = "https://casio-jamie-stunning-tions.trycloudflare.com"
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "reports")

# PNG 版(PPT/Word 通用)
img = qrcode.make(URL, box_size=12, border=2)
png_path = os.path.join(OUT_DIR, "qrcode_link.png")
img.save(png_path)
print("PNG 二维码: %s" % png_path)

# SVG 版(无损放大,海报用)
svg_img = qrcode.make(URL, image_factory=qrcode.image.svg.SvgImage,
                      box_size=12, border=2)
svg_path = os.path.join(OUT_DIR, "qrcode_link.svg")
with open(svg_path, "wb") as f:
    svg_img.save(f)
print("SVG 二维码: %s" % svg_path)
print("指向: %s" % URL)
