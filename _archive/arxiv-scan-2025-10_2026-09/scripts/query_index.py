# -*- coding: utf-8 -*-
"""全量索引查询/筛选工具。

用法:
  python query_index.py count <kw> [kw2 ...]        # 统计命中数
  python query_index.py grep  <kw> [n]              # 列出前 n 条(默认 40)
  python query_index.py group kw1|kw2 kw3|kw4 [n]   # AND(组) / OR(|) 组合查询
  python query_index.py id <arxiv-id> [more ids...]  # 按 id 直查
  python query_index.py stats                        # 索引概览
  python query_index.py months                       # 每月条数
"""
import json, os, re, sys, glob, html

ROOT = r'C:\code\media_paper\.tmp_scan\raw'


def load():
    rows = []
    for p in sorted(glob.glob(os.path.join(ROOT, '*.jsonl'))):
        for line in open(p, encoding='utf-8'):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    return rows


def blob(r):
    return (r['title'] + ' || ' + r['summary']).lower()


def show(rows, n=40, wid=115):
    for r in rows[:n]:
        c = ('  [' + r['comment'][:44] + ']') if r.get('comment') else ''
        print('%s %s  %s%s' % (r['published'][:10], r['id'].ljust(11),
                               r['title'][:wid], c))
    print('  --- %d shown / %d matched' % (min(n, len(rows)), len(rows)))


def main():
    rows = load()
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if not rows:
        print('index empty, run fetch_arxiv.py first')
        return

    if cmd == 'stats':
        print('entries:', len(rows))
        print('id range:', min(r['id'] for r in rows), '-', max(r['id'] for r in rows))
        prim = {}
        for r in rows:
            prim[r['primary']] = prim.get(r['primary'], 0) + 1
        for k, v in sorted(prim.items(), key=lambda x: -x[1]):
            print('   %-12s %d' % (k, v))
        return

    if cmd == 'months':
        m = {}
        for r in rows:
            m[r['published'][:7]] = m.get(r['published'][:7], 0) + 1
        for k in sorted(m):
            print('  %s  %6d' % (k, m[k]))
        return

    if cmd == 'id':
        want = set(sys.argv[2:])
        for r in rows:
            if r['id'] in want:
                print('%s %s  %s' % (r['published'][:10], r['id'], r['title']))
                print('     prim=%s comment=%s' % (r['primary'], r['comment'][:90]))
        found = {r['id'] for r in rows}
        miss = [w for w in want if w not in found]
        if miss:
            print('NOT IN INDEX:', miss)
        return

    if cmd == 'count':
        for kw in sys.argv[2:]:
            k = kw.lower()
            n = sum(1 for r in rows if k in blob(r))
            nt = sum(1 for r in rows if k in r['title'].lower())
            print('  %-34s title=%5d  full=%6d' % (kw, nt, n))
        return

    if cmd == 'grep':
        kw = sys.argv[2].lower()
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 40
        hit = [r for r in rows if kw in blob(r)]
        hit.sort(key=lambda r: r['id'])
        show(hit, n)
        return

    if cmd == 'group':
        groups = sys.argv[2].split()
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 40
        def ok(r, g):
            b = blob(r)
            return any(alt.strip().lower() in b for alt in g.split('|'))
        hit = [r for r in rows if all(ok(r, g) for g in groups)]
        hit.sort(key=lambda r: r['id'])
        show(hit, n)
        return

    print('unknown cmd', cmd)


if __name__ == '__main__':
    main()
