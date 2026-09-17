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
  6. 样式统一进度:仍为旧扁平样式(class="header")的笔记清单,即待迁移篇目
     (统一格式规范见 AGENTS.md「四」「八」)

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
# 页脚含生成日期,跨天后必然与当日重生成结果不同,故比对前把日期归一化;
# 真实的手改(卡片/分区/JS)仍会被检出。
GEN_DATE_RE = re.compile(r"更新于 \d{4}-\d{2}-\d{2}")
gen_date = ""
try:
    import build_index
    papers = json.load(open("papers.json", encoding="utf-8"))
    css = open("index_style.css", encoding="utf-8").read()
    expect = build_index.render(papers, css)
    actual = open("index.html", encoding="utf-8", newline="").read()
    m = GEN_DATE_RE.search(actual)
    if m:
        gen_date = m.group(0).replace("更新于 ", "")
    if GEN_DATE_RE.sub("更新于 <DATE>", actual) != GEN_DATE_RE.sub("更新于 <DATE>", expect):
        errors.append("index.html 与 papers.json 不同步(可能被手改),请运行 python build_index.py")
except FileNotFoundError as e:
    errors.append(f"缺少生成输入文件: {e.filename}")
except Exception as e:
    errors.append(f"index 重生成失败: {type(e).__name__}: {e}")

# 5. 不确定标注统计(报告项)
# 只统计正文中的标记;出现在 <pre>/<code> 里的多是在"讲解标记用法"(如规范贴的验证清单),
# 不是真实标注,计入会造成假计数。
CODE_BLOCK_RE = re.compile(r"<(pre|code)\b[^>]*>.*?</\1>", re.S)
unc = {}
for f in notes:
    s = CODE_BLOCK_RE.sub("", open(f, encoding="utf-8", errors="ignore").read())
    n = sum(s.count(k) for k in ("【存疑】", "【推测】", "【待核实】"))
    if n:
        unc[f] = n

# 6. 样式统一进度(报告项):统一格式用 .hero,旧扁平样式用 .header
legacy = []
for f in notes:
    s = open(f, encoding="utf-8", errors="ignore").read()
    if 'class="hero"' not in s and 'class="header"' in s:
        legacy.append(f)

print(f"笔记 {len(notes)} 篇 | 站内链接 | index 收录 | 本地图片")
if unc:
    print(f"不确定标注: {sum(unc.values())} 处 / {len(unc)} 篇"
          "(【存疑】【推测】【待核实】,供定期核实)")
unified = len(notes) - len(legacy)
print(f"统一格式进度: {unified}/{len(notes)} 篇已用高端样式, {len(legacy)} 篇待迁移")
if gen_date:
    print(f"index.html 最近生成日期: {gen_date}(仅供追溯,不影响校验)")
if legacy:
    print("待迁移清单(旧扁平样式,触碰时顺带迁移,见 AGENTS.md 八):")
    for f in legacy:
        print(f"  {f}")

if errors:
    print("\n[FAIL] 校验未通过:")
    for e in errors:
        print(e)
    sys.exit(1)
print("[OK] 全部通过")
