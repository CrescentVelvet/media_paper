# -*- coding: utf-8 -*-
"""按 arXiv 分类号系统拉取区间元数据（按月切片，增量落盘，可断点续传）。

用法: python fetch_arxiv.py [起始月] [结束月]
输出: .tmp_scan/raw/<YYYY-MM>.jsonl  每行一条 JSON
      .tmp_scan/raw/_manifest.json  每月 totalResults 与实际条数对账
"""
import urllib.request, urllib.parse, re, time, os, json, sys, html

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
API = 'https://export.arxiv.org/api/query?'
ROOT = r'C:\code\media_paper\.tmp_scan'
OUT = os.path.join(ROOT, 'raw')
os.makedirs(OUT, exist_ok=True)

PAGE = 1000
SLEEP = 4.0


def months(a, b):
    ya, ma = map(int, a.split('-'))
    yb, mb = map(int, b.split('-'))
    out = []
    y, m = ya, ma
    while (y, m) <= (yb, mb):
        out.append('%04d-%02d' % (y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def next_month(ym):
    y, m = map(int, ym.split('-'))
    m += 1
    if m > 12:
        m = 1
        y += 1
    return '%04d-%02d' % (y, m)


def req(q, start, maxr, tries=7):
    url = API + urllib.parse.quote('search_query=%s&start=%d&max_results=%d' % (q, start, maxr), safe='=&')
    last = None
    for i in range(tries):
        try:
            r = urllib.request.Request(url, headers={
                'User-Agent': UA,
                'Accept': 'application/atom+xml,application/xml,*/*'})
            return urllib.request.urlopen(r, timeout=120).read().decode('utf-8', 'ignore')
        except Exception as e:
            last = e
            code = getattr(e, 'code', '')
            wait = 8 + i * 7 if code != 429 else 20 + i * 15
            print('    retry %d (%s) wait %.0fs' % (i + 1, code or type(e).__name__, wait), flush=True)
            time.sleep(wait)
    print('    GIVE UP:', repr(last)[:150], flush=True)
    return None


ENTRY_RE = re.compile(r'<entry>(.*?)</entry>', re.S)


def parse_entries(xml):
    out = []
    for m in ENTRY_RE.finditer(xml):
        b = m.group(1)

        def g(tag, block=b):
            mm = re.search(r'<%s[^>]*>(.*?)</%s>' % (tag, tag), block, re.S)
            if not mm:
                return ''
            t = re.sub(r'<[^>]+>', ' ', mm.group(1))
            return re.sub(r'\s+', ' ', html.unescape(t)).strip()

        aid = ''
        am = re.search(r'<id>http://arxiv\.org/abs/([^<]+)</id>', b)
        if am:
            aid = re.sub(r'v\d+$', '', am.group(1).strip())
        prim = ''
        pm = re.search(r'<arxiv:primary_category[^>]*term="([^"]+)"', b)
        if pm:
            prim = pm.group(1)
        cats = re.findall(r'<category[^>]*term="([^"]+)"', b)
        authors = re.findall(r'<name>([^<]+)</name>', b)
        comment = ''
        cm = re.search(r'<arxiv:comment[^>]*>(.*?)</arxiv:comment>', b, re.S)
        if cm:
            comment = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', cm.group(1)))).strip()
        out.append({
            'id': aid,
            'title': g('title'),
            'published': g('published'),
            'updated': g('updated'),
            'summary': g('summary'),
            'authors': authors,
            'primary': prim,
            'cats': cats,
            'comment': comment,
        })
    return out


def fetch_month(ym):
    path = os.path.join(OUT, ym + '.jsonl')
    meta_path = os.path.join(OUT, '_meta_' + ym + '.json')
    if os.path.exists(meta_path):
        meta = json.load(open(meta_path, encoding='utf-8'))
        if meta.get('done'):
            print('%s: already done (%d entries)' % (ym, meta.get('n', 0)), flush=True)
            return meta
    lo = ym.replace('-', '') + '010000'
    hi = next_month(ym).replace('-', '') + '010000'
    q = '(cat:cs.CV OR cat:cs.GR) AND submittedDate:[%s TO %s]' % (lo, hi)
    print('%s: query %s' % (ym, q), flush=True)
    x = req(q, 0, 1)
    if not x:
        return {'month': ym, 'done': False, 'err': 'first request failed'}
    tm = re.search(r'<opensearch:totalResults[^>]*>(\d+)<', x)
    total = int(tm.group(1)) if tm else 0
    print('%s: totalResults=%d' % (ym, total), flush=True)
    rows, seen = [], set()
    start = 0
    while start < total:
        x = req(q, start, PAGE)
        if not x:
            break
        ents = parse_entries(x)
        if not ents:
            break
        for e in ents:
            if not e['id'] or e['id'] in seen:
                continue
            # 本地切月：过滤掉落在下月的条目
            pub = e['published'][:10].replace('-', '')
            if pub >= hi[:8]:
                continue
            if pub < lo[:8]:
                continue
            seen.add(e['id'])
            rows.append(e)
        print('   start=%d got=%d uniq=%d' % (start, len(ents), len(rows)), flush=True)
        start += PAGE
        if len(ents) < PAGE:
            break
        time.sleep(SLEEP)
    with open(path, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    meta = {'month': ym, 'total': total, 'n': len(rows), 'done': True}
    json.dump(meta, open(meta_path, 'w', encoding='utf-8'), ensure_ascii=False)
    print('%s: saved %d entries -> %s' % (ym, len(rows), path), flush=True)
    return meta


def main():
    a = sys.argv[1] if len(sys.argv) > 1 else '2025-10'
    b = sys.argv[2] if len(sys.argv) > 2 else '2026-09'
    ms = months(a, b)
    print('months:', ms, flush=True)
    manifest = []
    for i, ym in enumerate(ms):
        m = fetch_month(ym)
        manifest.append(m)
        json.dump(manifest, open(os.path.join(OUT, '_manifest.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        if i < len(ms) - 1:
            time.sleep(SLEEP)
    print('===== DONE =====', flush=True)
    for m in manifest:
        print(m, flush=True)


if __name__ == '__main__':
    main()
