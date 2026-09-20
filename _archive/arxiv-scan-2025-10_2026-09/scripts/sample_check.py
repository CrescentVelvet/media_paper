# -*- coding: utf-8 -*-
"""标题召回盲区抽样验证。

主题矩阵只看得见标题，标题抽象的论文会被漏。本脚本从「未被任何主题召回」
的条目里随机抽样，供人工判断真实漏检率。

用法: python sample_check.py [抽样数] [seed]
"""
import json, os, re, glob, random, sys

ROOT = r'C:\code\media_paper\.tmp_scan'
RAW = os.path.join(ROOT, 'list_raw2')
TOPICS = os.path.join(ROOT, 'topics')


def load_raw():
    rows = {}
    for p in sorted(glob.glob(os.path.join(RAW, '*.jsonl'))):
        ym = os.path.basename(p).split('_')[-1].replace('.jsonl', '')
        for line in open(p, encoding='utf-8'):
            line = line.strip()
            if line:
                r = json.loads(line)
                r['_m'] = ym
                rows.setdefault(r['id'], r)
    return rows


def recalled_ids():
    ids = set()
    for f in glob.glob(os.path.join(TOPICS, 'T*.txt')):
        for line in open(f, encoding='utf-8'):
            m = re.match(r'^(\d{4}\.\d{4,5})', line)
            if m:
                ids.add(m.group(1))
    return ids


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 42
    rows = load_raw()
    hit = recalled_ids()
    if not rows:
        print('no index')
        return
    missed = [r for k, r in rows.items() if k not in hit]
    print('index=%d  recalled=%d  not-recalled=%d' % (len(rows), len(hit), len(missed)))
    random.seed(seed)
    samp = random.sample(missed, min(n, len(missed)))
    samp.sort(key=lambda r: r['id'])
    out = os.path.join(ROOT, 'blind_spot_sample.txt')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('# 未召回条目随机抽样 %d 条 (seed=%d, from %d)\n\n' % (len(samp), seed, len(missed)))
        for r in samp:
            f.write('%s  %s  %s\n' % (r['id'], r['_m'], r['title']))
    print('written', out)
    for r in samp[:15]:
        print('  %s %s' % (r['id'], r['title'][:100]))


if __name__ == '__main__':
    main()
