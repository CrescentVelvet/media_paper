#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""外链图片存活检测(需要网络)

扫描所有 .html 中 src="http(s)://..." 的外链图片,并发 HEAD 检测,
报告非 200 的失效图及其引用位置。失效图应按 AGENTS.md 图像策略 B
本地化到 images/<arxiv-id>/。

用法:
  python check_images.py              检测全部外链图
  python check_images.py --limit 20   只检测前 20 张(快速抽查)
  python check_images.py --timeout 30 网络差时加大超时
"""
import argparse
import glob
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="只检测前 N 张(0=全部)")
    ap.add_argument("--timeout", type=int, default=15, help="单张超时秒数")
    args = ap.parse_args()

    refs = {}  # url -> [引用它的 html 文件]
    for f in sorted(glob.glob("*.html")):
        s = open(f, encoding="utf-8", errors="ignore").read()
        for u in re.findall(r'src="(https?://[^"]+)"', s):
            refs.setdefault(u, [])
            if f not in refs[u]:
                refs[u].append(f)

    urls = sorted(refs)
    if args.limit:
        urls = urls[: args.limit]
    print(f"外链图片共 {len(refs)} 张(去重),本次检测 {len(urls)} 张")

    def check(u):
        try:
            req = urllib.request.Request(
                u, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=args.timeout) as r:
                return u, r.status
        except Exception as e:
            return u, getattr(e, "code", None) or type(e).__name__

    bad = []
    with ThreadPoolExecutor(16) as ex:
        for u, st in ex.map(check, urls):
            if st != 200:
                bad.append((u, st))

    if bad:
        print(f"\n[FAIL] 失效 {len(bad)} / {len(urls)}:")
        for u, st in bad:
            print(f"  [{st}] {u}")
            for f in refs[u]:
                print(f"        引用自: {f}")
        print("\n处理:按 AGENTS.md 策略 B 将失效图本地化到 images/<arxiv-id>/")
        sys.exit(1)
    print("[OK] 全部存活")


if __name__ == "__main__":
    main()
