# -*- coding: utf-8 -*-
"""按 arXiv 分类号抓取 monthly listing（通道 B：arxiv.org 主站，非 API）。

用法: python fetch_listing.py [起始月] [结束月] [分类1,分类2]
      月份格式 YYYY-MM，分类如 cs.CV,cs.GR
输出: .tmp_scan/list_html/<YYYY-MM>_<skip>.html  原始页
      .tmp_scan/list_raw/<cat>_<YYYY-MM>.jsonl  解析后条目
      .tmp_scan/fetch.log                       运行日志（增量 flush）
"""
import subprocess, os, re, json, time, sys, html as H

ROOT = r'C:\code\media_paper\.tmp_scan'
HTML_DIR = os.path.join(ROOT, 'list_html')
RAW_DIR = os.path.join(ROOT, 'list_raw')
LOG = os.path.join(ROOT, 'fetch.log')
os.makedirs(HTML_DIR, exist_ok=True)
os.makedirs(RAW_DIR, exist_ok=True)

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
PER = 2000
SLEEP = 3.0
MAX_SKIP = 12000


def log(msg):
    line = '[%s] %s' % (time.strftime('%H:%M:%S'), msg)
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def months(a, b):
    ya, ma = map(int, a.split('-'))
    yb, mb = map(int, b.split('-'))
    out, y, m = [], ya, ma
    while (y, m) <= (yb, mb):
        out.append('%04d-%02d' % (y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def curl(url, out, tries=5):
    for i in range(tries):
        r = subprocess.run([
            'curl', '-sL', '--fail', '-o', out, '-w', '%{http_code}',
            '-A', UA,
            '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            '-H', 'Accept-Language: en-US,en;q=0.9',
            '-H', 'Accept-Encoding: identity',
            '-H', 'Referer: https://arxiv.org/list/recent',
            '--max-time', '180', url], capture_output=True, text=True)
        code = (r.stdout or '').strip()
        if r.returncode == 0 and code == '200' and os.path.exists(out) and os.path.getsize(out) > 20000:
            return True, code
        log('    curl retry %d code=%s rc=%d' % (i + 1, code or '-', r.returncode))
        time.sleep(6 + i * 6)
    return False, (r.stdout or '').strip()


def clean(s):
    s = re.sub(r'<[^>]+>', ' ', s)
    return re.sub(r'\s+', ' ', H.unescape(s)).strip()


def parse_page(d):
    """返回条目 list。页面结构: <dt>...arXiv:ID...</dt><dd>...title/comments/subjects...</dd>"""
    rows = []
    # 按 dd 块切，向前找最近的 dt
    for m in re.finditer(r"<dd>(.*?)</dd>", d, re.S):
        dd = m.group(1)
        head = d[max(0, m.start() - 1200):m.start()]
        am = None
        for mm in re.finditer(r'arXiv:(\d{4}\.\d{4,5})', head):
            am = mm
        if not am:
            continue
        aid = am.group(1)

        def grab(cls):
            mm = re.search(r"<div class=['\"]" + cls + r"[^'\"]*['\"]>(.*?)</div>", dd, re.S)
            return clean(mm.group(1)) if mm else ''

        title = grab('list-title')
        title = re.sub(r'^Title:\s*', '', title)
        authors = grab('list-authors')
        authors = re.sub(r'^Authors:\s*', '', authors)
        comments = grab('list-comments')
        comments = re.sub(r'^Comments?:\s*', '', comments)
        subjects = grab('list-subjects')
        subjects = re.sub(r'^Subjects?:\s*', '', subjects)
        if not title:
            continue
        rows.append({'id': aid, 'title': title, 'authors': authors,
                     'comment': comments, 'subjects': subjects})
    return rows


def fetch_month_cat(ym, cat):
    out_path = os.path.join(RAW_DIR, '%s_%s.jsonl' % (cat.replace('.', ''), ym))
    meta_path = out_path + '.meta'
    if os.path.exists(meta_path):
        try:
            mt = json.load(open(meta_path, encoding='utf-8'))
            if mt.get('done'):
                log('%s %s: cached (%d entries)' % (ym, cat, mt.get('n', 0)))
                return mt
        except Exception:
            pass
    rows, seen = [], set()
    skip = 0
    while skip < MAX_SKIP:
        hp = os.path.join(HTML_DIR, '%s_%s_%d.html' % (cat.replace('.', ''), ym, skip))
        if os.path.exists(hp) and os.path.getsize(hp) > 20000:
            log('%s %s skip=%d: html cached' % (ym, cat, skip))
        else:
            url = 'https://arxiv.org/list/%s/%s?skip=%d&show=%d' % (cat, ym, skip, PER)
            t0 = time.time()
            ok, code = curl(url, hp)
            log('%s %s skip=%d: http=%s %.0fs %s' % (ym, cat, skip, code, time.time() - t0,
                                                     'OK' if ok else 'FAIL'))
            if not ok:
                break
        d = open(hp, encoding='utf-8', errors='ignore').read()
        page = parse_page(d)
        new = 0
        for r in page:
            if r['id'] in seen:
                continue
            seen.add(r['id'])
            rows.append(r)
            new += 1
        log('   parsed=%d new=%d total=%d' % (len(page), new, len(rows)))
        if len(page) < PER * 0.9:
            break
        skip += PER
        time.sleep(SLEEP)
    # 按月过滤（ID 前缀 = YYMM）
    yy, mm = ym.split('-')
    pref = yy[2:] + mm
    rows = [r for r in rows if r['id'].startswith(pref)]
    with open(out_path, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    mt = {'month': ym, 'cat': cat, 'n': len(rows), 'done': True}
    json.dump(mt, open(meta_path, 'w', encoding='utf-8'), ensure_ascii=False)
    log('%s %s: saved %d entries' % (ym, cat, len(rows)))
    return mt


def main():
    a = sys.argv[1] if len(sys.argv) > 1 else '2025-10'
    b = sys.argv[2] if len(sys.argv) > 2 else '2026-09'
    cats = (sys.argv[3] if len(sys.argv) > 3 else 'cs.CV,cs.GR').split(',')
    ms = months(a, b)
    log('===== START %s..%s cats=%s =====' % (a, b, cats))
    man = []
    for ym in ms:
        for c in cats:
            try:
                man.append(fetch_month_cat(ym, c))
            except Exception as e:
                log('ERROR %s %s: %r' % (ym, c, e))
            time.sleep(SLEEP)
    json.dump(man, open(os.path.join(ROOT, 'listing_manifest.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    log('===== DONE total=%d =====' % sum(x.get('n', 0) for x in man))


if __name__ == '__main__':
    main()
