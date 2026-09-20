# -*- coding: utf-8 -*-
"""按 arXiv 分类号抓 monthly listing（v2：并发 2 路 + HTML 完整性校验 + 断点续传）。

实测：并发 3 路时第 3 路被卡满 300s；并发 2 路稳定（4-12s/页/3.4MB）。
关键修正：缓存判据必须校验文件以 </html> 结尾，否则会误用被中断的半截页面。

用法: python fetch_listing2.py [起始月] [结束月] [分类]
"""
import subprocess, os, re, json, time, sys, html as H
from concurrent.futures import ThreadPoolExecutor

ROOT = r'C:\code\media_paper\.tmp_scan'
HTML_DIR = os.path.join(ROOT, 'list_html2')
RAW_DIR = os.path.join(ROOT, 'list_raw2')
LOG = os.path.join(ROOT, 'fetch2.log')
for d in (HTML_DIR, RAW_DIR):
    os.makedirs(d, exist_ok=True)

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
PER = 2000
MAX_SKIP = 12000
CONC = 2


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


def page_ok(path):
    """完整页面判据：文件够大且以 </html> 结尾。"""
    if not os.path.exists(path) or os.path.getsize(path) < 100000:
        return False
    try:
        with open(path, 'rb') as f:
            f.seek(-3000, 2)
            tail = f.read()
        return b'</html>' in tail
    except Exception:
        return False


def curl_page(url, out, tries=4):
    for i in range(tries):
        if os.path.exists(out):
            os.remove(out)
        r = subprocess.run([
            'curl', '-sL', '--fail', '-o', out, '-w', '%{http_code}',
            '-A', UA,
            '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            '-H', 'Accept-Language: en-US,en;q=0.9',
            '-H', 'Accept-Encoding: identity',
            '-H', 'Referer: https://arxiv.org/list/recent',
            '--max-time', '300', url], capture_output=True, text=True)
        code = (r.stdout or '').strip()
        if page_ok(out):
            return True, code, os.path.getsize(out)
        log('    retry %d code=%s size=%s' % (i + 1, code or '-',
            os.path.getsize(out) if os.path.exists(out) else 0))
        time.sleep(5 + i * 8)
    return False, code if 'code' in dir() else '-', 0


def clean(s):
    s = re.sub(r'<[^>]+>', ' ', s)
    return re.sub(r'\s+', ' ', H.unescape(s)).strip()


def parse_page(d):
    rows = []
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

        title = re.sub(r'^Title:\s*', '', grab('list-title'))
        if not title:
            continue
        rows.append({
            'id': aid, 'title': title,
            'authors': re.sub(r'^Authors:\s*', '', grab('list-authors')),
            'comment': re.sub(r'^Comments?:\s*', '', grab('list-comments')),
            'subjects': re.sub(r'^Subjects?:\s*', '', grab('list-subjects')),
        })
    return rows


def do_month_cat(task):
    ym, cat = task
    out_path = os.path.join(RAW_DIR, '%s_%s.jsonl' % (cat.replace('.', ''), ym))
    meta_path = out_path + '.meta'
    if os.path.exists(meta_path):
        try:
            mt = json.load(open(meta_path, encoding='utf-8'))
            if mt.get('done'):
                return mt
        except Exception:
            pass
    rows, seen, skip = [], set(), 0
    while skip < MAX_SKIP:
        hp = os.path.join(HTML_DIR, '%s_%s_%d.html' % (cat.replace('.', ''), ym, skip))
        if page_ok(hp):
            pass
        else:
            url = 'https://arxiv.org/list/%s/%s?skip=%d&show=%d' % (cat, ym, skip, PER)
            t0 = time.time()
            ok, code, sz = curl_page(url, hp)
            log('%s %s skip=%d http=%s size=%d %.1fs %s' % (ym, cat, skip, code, sz,
                                                            time.time() - t0, 'OK' if ok else 'FAIL'))
            if not ok:
                break
        page = parse_page(open(hp, encoding='utf-8', errors='ignore').read())
        for r in page:
            if r['id'] not in seen:
                seen.add(r['id'])
                rows.append(r)
        if len(page) < PER * 0.9:
            break
        skip += PER
    yy, mm = ym.split('-')
    pref = yy[2:] + mm
    rows = [r for r in rows if r['id'].startswith(pref)]
    with open(out_path, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    mt = {'month': ym, 'cat': cat, 'n': len(rows), 'done': True}
    json.dump(mt, open(meta_path, 'w', encoding='utf-8'), ensure_ascii=False)
    log('%s %s saved %d' % (ym, cat, len(rows)))
    return mt


def main():
    a = sys.argv[1] if len(sys.argv) > 1 else '2025-10'
    b = sys.argv[2] if len(sys.argv) > 2 else '2026-09'
    cats = (sys.argv[3] if len(sys.argv) > 3 else 'cs.CV,cs.GR').split(',')
    tasks = [(ym, c) for ym in months(a, b) for c in cats]
    log('===== START v2 %s..%s %s  tasks=%d conc=%d =====' % (a, b, cats, len(tasks), CONC))
    res = []
    with ThreadPoolExecutor(CONC) as ex:
        for r in ex.map(do_month_cat, tasks):
            res.append(r)
    json.dump(res, open(os.path.join(ROOT, 'listing_manifest2.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    log('===== DONE total=%d =====' % sum(x.get('n', 0) for x in res))


if __name__ == '__main__':
    main()
