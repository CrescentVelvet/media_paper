# -*- coding: utf-8 -*-
"""召回自检：用库内已有笔记的 arXiv ID 作为验证集，量化两件事
  (1) 全量 listing 索引是否覆盖这些论文（证明拉取完整）
  (2) 主题矩阵是否能召回它们（证明筛选有效）

用法: python verify_recall.py
"""
import json, os, re, glob

ROOT = r'C:\code\media_paper\.tmp_scan'
RAW = os.path.join(ROOT, 'list_raw2')
LIB = os.path.join(ROOT, 'lib_ids.json')

# 区间内、已知相关的验证集（上一轮检索确认过的高相关论文）
VERIFY = {
    '2510.15264': 'DriveGen3D',
    '2511.00503': 'Diff4Splat',
    '2602.14941': 'AnchorWeave',
    '2602.22960': 'UCM',
    '2603.00492': 'ArtiFixer',
    '2603.14965': 'GeoNVS',
    '2604.13036': 'Lyra 2.0',
    '2605.19949': 'AnyCity',
    '2607.01202': 'World from Motion',
    '2609.03919': 'OctWorld',
    '2609.17039': 'Bi-FlowGS',
    '2609.17230': 'DecoGS',
}


def load_index():
    rows = {}
    for p in sorted(glob.glob(os.path.join(RAW, '*.jsonl'))):
        ym = os.path.basename(p).split('_')[-1].replace('.jsonl', '')
        for line in open(p, encoding='utf-8'):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            r['_file'] = ym
            rows.setdefault(r['id'], r)
    return rows


def main():
    idx = load_index()
    months = sorted({r['_file'] for r in idx.values()})
    print('index: %d unique papers, months=%s' % (len(idx), months))
    print()
    print('=== (1) 验证集覆盖情况（拉取完整性）===')
    miss = []
    for aid, name in sorted(VERIFY.items()):
        r = idx.get(aid)
        ym = '20' + aid[:2] + '-' + aid[2:4]
        if r:
            print('  OK    %s  %s  [%s]  %s' % (aid, name.ljust(18), r['_file'], r['title'][:70]))
        else:
            ok_month = ym in months
            miss.append((aid, name, ym, ok_month))
            print('  MISS  %s  %s  (所属月 %s %s)' % (aid, name.ljust(18), ym,
                    '已抓取' if ok_month else '未抓取'))
    print('  -> %d/%d covered' % (len(VERIFY) - len(miss), len(VERIFY)))
    print()
    print('=== (2) 主题矩阵召回情况（筛选有效性）===')
    tp = os.path.join(ROOT, 'topics')
    if not os.path.isdir(tp):
        print('  (run topic_scan.py first)')
        return
    recall = {k: [] for k in VERIFY}
    for f in sorted(glob.glob(os.path.join(tp, 'T*.txt'))):
        tname = os.path.basename(f).replace('.txt', '')
        ids = set()
        for line in open(f, encoding='utf-8'):
            m = re.match(r'^(\d{4}\.\d{4,5})', line)
            if m:
                ids.add(m.group(1))
        for aid in VERIFY:
            if aid in ids:
                recall[aid].append(tname)
    for aid, name in sorted(VERIFY.items()):
        t = recall.get(aid) or []
        flag = 'OK  ' if t else 'MISS'
        print('  %s %s  %s  -> %s' % (flag, aid, name.ljust(18),
              ', '.join(x.split('_')[0] for x in t) if t else '(未被任何主题召回)'))
    print()
    # 库内全部 ID 的覆盖情况
    if os.path.exists(LIB):
        lib = json.load(open(LIB, encoding='utf-8'))
        rng = [k for k in lib if '2510' <= k[:4] + k[5:7] <= '2609' or k[:4] in ('2510', '2511', '2601', '2602', '2603', '2604', '2605', '2606', '2607', '2608', '2609')]
        print('=== (3) 库内笔记 ID 中落在区间内的 ===')
        for k in sorted(rng):
            print('  %s  %s  %s' % ('OK  ' if k in idx else 'MISS', k, lib[k][0][:60]))


if __name__ == '__main__':
    main()
