#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""media_paper 知识库完整性校验(离线,无需网络)

硬性校验(任一失败则退出码 1,禁止 commit):
  1. 站内链接:所有 .html 中 href="*.html" 指向的文件必须存在
  2. index 收录:所有笔记 .html 必须被 index.html 链接
  3. 本地图片:src="images/..." 指向的文件必须存在
  4. 生成同步:index.html 必须与 papers.json + index_style.css 的生成结果一致

报告项(仅统计,不失败):
  5. 不确定标注:【存疑】/【推测】/【待核实】数量(供定期核实)

外链图片存活检测需要网络,见 check_images.py。
"""
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.chdir(os.path.dirname(os.path.abspath(__file__)))

html_files = sorted(glob.glob("*.html"))
notes = [f for f in html_files if f != "index.html"]
errors = []

# 1. 站内死链
dead = []
for f in html_files:
    s = open(f, encoding="utf-8", errors="ignore").read()
    for h in re.findall(r'href="([^"#?]+\.html)', s):
        if not os.path.exists(h):
            dead.append((f, h))
if dead:
    errors.append(f"站内死链 {len(dead)} 处:")
    errors += [f"  {f} -> {h}" for f, h in dead]

# 2. index 收录完整性
idx = open("index.html", encoding="utf-8", errors="ignore").read()
linked = set(re.findall(r'href="([^"#?]+\.html)"', idx))
missing = [f for f in notes if f not in linked]
if missing:
    errors.append(f"index.html 未收录 {len(missing)} 篇:")
    errors += [f"  {f}" for f in missing]

# 3. 本地图片完整性
badimg = []
for f in html_files:
    s = open(f, encoding="utf-8", errors="ignore").read()
    for m in re.findall(r'src="(images/[^"]+)"', s):
        if not os.path.exists(m):
            badimg.append((f, m))
if badimg:
    errors.append(f"缺失本地图片 {len(badimg)} 处:")
    errors += [f"  {f} -> {m}" for f, m in badimg]

# 4. index.html 与 papers.json 同步(生成物不可手改)
try:
    import build_index
    papers = json.load(open("papers.json", encoding="utf-8"))
    css = open("index_style.css", encoding="utf-8").read()
    expect = build_index.render(papers, css)
    actual = open("index.html", encoding="utf-8", newline="").read()
    if actual != expect:
        errors.append("index.html 与 papers.json 不同步(可能被手改),请运行 python build_index.py")
except FileNotFoundError as e:
    errors.append(f"缺少生成输入文件: {e.filename}")
except Exception as e:
    errors.append(f"index 重生成失败: {type(e).__name__}: {e}")

# 5. 不确定标注统计(报告项)
unc = {}
for f in notes:
    s = open(f, encoding="utf-8", errors="ignore").read()
    n = sum(s.count(k) for k in ("【存疑】", "【推测】", "【待核实】"))
    if n:
        unc[f] = n

print(f"笔记 {len(notes)} 篇 | 站内链接 | index 收录 | 本地图片")
if unc:
    print(f"不确定标注: {sum(unc.values())} 处 / {len(unc)} 篇"
          "(【存疑】【推测】【待核实】,供定期核实)")

if errors:
    print("\n[FAIL] 校验未通过:")
    for e in errors:
        print(e)
    sys.exit(1)
print("[OK] 全部通过")
