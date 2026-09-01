#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 papers.json(唯一真相源)生成 index.html —— 禁止手改 index.html

用法: python build_index.py
流程: papers.json + index_style.css -> index.html(自包含,浏览器直开)
数据变更: 改 papers.json 后重新运行本脚本;check.py 会校验两者是否同步。
"""
import html
import json
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))

# 分区展示顺序(与迁移时的原 index 一致)
ORDER = [
    "overview", "vg-notes-1", "vg-notes-2", "roadmap", "key-compare",
    "vg-notes-3", "panorama", "vg-timeline", "3d", "3d-compare",
    "3d-timeline", "sr", "meta", "summary",
]
CARD_SECTIONS = {"vg-notes-1", "vg-notes-2", "vg-notes-3", "3d", "sr", "meta"}

KIND_LABEL = {"note": "论文笔记", "survey": "调研综述",
              "pipeline": "工程方案", "methodology": "方法论"}
DEPTH_LABEL = {"deep": "深度", "standard": "标准", "brief": "速览"}

FILTER_CSS = """
/* ---- 筛选栏(build_index.py 生成, iOS 风格) ---- */
.filter-bar{position:sticky;top:0;z-index:50;display:flex;flex-wrap:wrap;gap:10px;align-items:center;
  background:rgba(255,255,255,.92);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
  border:1px solid var(--border);border-radius:16px;padding:12px 16px;margin-bottom:20px;
  box-shadow:var(--shadow);}
.filter-bar input[type=search]{flex:1 1 220px;min-width:180px;background:var(--tag-bg);color:var(--text);
  border:1px solid transparent;border-radius:11px;padding:8px 14px;font-size:14px;outline:none;
  transition:all .15s;}
.filter-bar input[type=search]:focus{background:#fff;border-color:var(--accent);
  box-shadow:0 0 0 3px var(--accent-soft);}
.filter-bar input[type=search]::placeholder{color:var(--text-dim);}
.filter-bar .chips{display:flex;gap:6px;flex-wrap:wrap;}
.chip{cursor:pointer;border:1px solid transparent;background:var(--tag-bg);color:#3c3c43;
  border-radius:999px;padding:5px 13px;font-size:13px;user-select:none;transition:all .15s;}
.chip:hover{background:#e8e8ed;}
.chip.active{background:var(--accent);color:#fff;font-weight:600;}
.chip.chip-clear{display:none;background:transparent;border-color:var(--border-strong);color:var(--text-dim);}
.filter-bar.filtering .chip-clear{display:inline-block;}
.filter-bar select{background:var(--tag-bg);color:var(--text);border:1px solid transparent;
  border-radius:11px;padding:8px 10px;font-size:14px;outline:none;cursor:pointer;transition:all .15s;}
.filter-bar select:focus{background:#fff;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft);}
.result-count{font-size:13px;color:var(--text-dim);margin-left:auto;}
.empty{display:none;text-align:center;color:var(--text-dim);padding:48px 0;background:var(--card);
  border:1px dashed var(--border-strong);border-radius:16px;margin-bottom:20px;font-size:0.95em;}
.tag-kind{background:var(--kind-bg) !important;color:var(--kind-fg) !important;}
.tag-depth{background:var(--depth-bg) !important;color:var(--depth-fg) !important;}
"""


def _plain(text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text)).strip()


def _card_html(n, num):
    tags = [f'<span class="tag tag-kind">{KIND_LABEL[n["kind"]]}</span>',
            f'<span class="tag tag-depth">{DEPTH_LABEL[n["depth"]]}</span>']
    tags += [f'<span class="tag">{html.escape(t)}</span>' for t in n["tags"]]
    meta = "\n".join(f"                <span>{m}</span>" for m in n["meta"])
    links = []
    for l in n["links"]:
        tgt = ' target="_blank"' if l["href"].startswith("http") else ""
        links.append(f'            <a href="{l["href"]}"{tgt}>{l["text"]}</a>')
    return (
        '        <div class="note-card" data-file="%s" data-kind="%s" data-depth="%s"\n'
        '              data-topics="%s" data-search="%s">\n'
        '            <h3>%d. %s</h3>\n'
        '            <div class="meta">\n%s\n            </div>\n'
        '            <div class="tags">\n                %s\n            </div>\n'
        '            <p>%s</p>\n%s\n        </div>'
    ) % (
        html.escape(n["file"], quote=True), n["kind"], n["depth"],
        html.escape("|".join(n["topics"]), quote=True),
        html.escape(_plain(n["title"] + " " + " ".join(n["tags"]) + " " + n["summary"]), quote=True),
        num, n["title"], meta, "\n                ".join(tags), n["summary"],
        "\n".join(links),
    )


def render(papers, css):
    page = papers["page"]
    static = {e["id"]: e for e in papers["extra_sections"]}
    by_sec = {}
    for n in papers["notes"]:
        by_sec.setdefault(n["section"], []).append(n)
    missing = [sid for sid in CARD_SECTIONS if sid not in by_sec]
    assert not missing, f"papers.json 缺少卡片分区: {missing}"

    # --- 计数(kind/depth chips 用) ---
    from collections import Counter
    kc, dc = Counter(n["kind"] for n in papers["notes"]), Counter(n["depth"] for n in papers["notes"])

    parts = []
    parts.append('<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="UTF-8">\n'
                 '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
                 f'<title>{html.escape(page["title"])}</title>\n'
                 '<style>\n' + css.strip() + "\n" + FILTER_CSS + '\n</style>\n</head>\n<body>\n')
    parts.append('<div class="header">\n'
                 f'    <h1>{page["title"]}</h1>\n    <p>{page["subtitle"]}</p>\n</div>\n')
    parts.append('<div class="container">\n')

    # --- 筛选栏 ---
    kind_chips = "".join(
        f'<span class="chip{" active" if v == "all" else ""}" data-k="{k}" data-v="{v}">{label} {kc[v] if v in kc else ""}</span>'
        for k, v, label in
        [("kind", "all", "全部类型")] + [("kind", k, KIND_LABEL[k]) for k in ["note", "survey", "pipeline", "methodology"]])
    depth_chips = "".join(
        f'<span class="chip{" active" if v == "all" else ""}" data-k="{k}" data-v="{v}">{label} {dc[v] if v in dc else ""}</span>'
        for k, v, label in
        [("depth", "all", "全部深度")] + [("depth", d, DEPTH_LABEL[d]) for d in ["deep", "standard", "brief"]])
    topic_opts = '<option value="all">全部主题</option>' + "".join(
        f'<option value="{html.escape(t["name"])}">{html.escape(t["name"])}</option>' for t in papers["topics"])
    parts.append(
        '<div class="filter-bar" id="filterBar">\n'
        '    <input type="search" id="q" placeholder="搜索标题 / 标签 / 摘要…">\n'
        f'    <div class="chips">{kind_chips}</div>\n'
        f'    <div class="chips">{depth_chips}</div>\n'
        f'    <select id="topic">{topic_opts}</select>\n'
        '    <button type="button" class="chip chip-clear" id="clear">✕ 清除筛选</button>\n'
        '    <span class="result-count" id="cnt"></span>\n'
        '</div>\n'
        '<div class="empty" id="empty">🔍 没有匹配的笔记 —— 换个关键词，或点上方「✕ 清除筛选」重置条件</div>\n')

    # --- 分区(按固定顺序) ---
    num = 0
    for sid in ORDER:
        if sid in CARD_SECTIONS:
            cards = "\n\n".join(_card_html(n, (num := num + 1)) for n in by_sec[sid])
            title = static_title = None
            # 卡片分区标题取该区第一篇 meta 外的原始标题——存于 extra? 不,静态标题如下:
            titles = {"vg-notes-1": "📖 阅读笔记",
                      "vg-notes-2": "📖 横向对比: 其他视频生成模型 + 技术方向 (2026-06-25 新增)",
                      "vg-notes-3": "📖 业界最新视频生成模型调研 (2026-06-25 新增)",
                      "3d": "📖 三维重建与生成 (2026-06-25 新增)",
                      "sr": "📖 图像超分辨率与图像复原 (Real-ISR + HYPIR)",
                      "meta": "🛠️ 方法论与工作流"}
            parts.append(f'<div class="section" data-sid="{sid}" data-cards="1">\n'
                         f'        <h2>{titles[sid]}</h2>\n\n{cards}\n\n    </div>\n\n')
        else:
            e = static[sid]
            parts.append(f'<div class="section" data-sid="{sid}" data-static="1">\n'
                         f'        <h2>{e["title"]}</h2>\n{e["html"]}\n    </div>\n\n')
    parts.append("</div>\n")
    parts.append(f'<div class="footer">\n'
                 f'    📝 调研索引 · 更新于 {date.today().isoformat()} · 涵盖 {len(papers["notes"])} 篇笔记 · '
                 f'由 build_index.py 从 papers.json 生成(勿手改本文件)\n</div>\n')

    # --- 筛选 JS ---
    parts.append("""<script>
(function(){
  var cards=[].slice.call(document.querySelectorAll('.note-card'));
  var q=document.getElementById('q'),topic=document.getElementById('topic'),cnt=document.getElementById('cnt');
  var bar=document.getElementById('filterBar'),empty=document.getElementById('empty'),clear=document.getElementById('clear');
  var state={kind:'all',depth:'all'};
  function bindChips(key){
    document.querySelectorAll('.chip[data-k="'+key+'"]').forEach(function(ch){
      ch.addEventListener('click',function(){
        state[key]=ch.dataset.v;
        document.querySelectorAll('.chip[data-k="'+key+'"]').forEach(function(c){c.classList.toggle('active',c===ch);});
        apply();
      });
    });
  }
  function apply(){
    var query=q.value.trim().toLowerCase(),tp=topic.value;
    var filtering=!!query||state.kind!=='all'||state.depth!=='all'||tp!=='all';
    var vis={};
    cards.forEach(function(c){
      var show=(state.kind==='all'||c.dataset.kind===state.kind)
            &&(state.depth==='all'||c.dataset.depth===state.depth)
            &&(tp==='all'||('|'+c.dataset.topics+'|').indexOf('|'+tp+'|')>=0)
            &&(!query||c.dataset.search.toLowerCase().indexOf(query)>=0);
      c.style.display=show?'':'none';
      if(show)vis[c.closest('.section').dataset.sid]=1;
    });
    document.querySelectorAll('.section[data-cards]').forEach(function(s){
      s.style.display=(!filtering||vis[s.dataset.sid])?'':'none';
    });
    document.querySelectorAll('.section[data-static]').forEach(function(s){
      s.style.display=filtering?'none':'';
    });
    bar.classList.toggle('filtering',filtering);
    if(filtering){
      var n=cards.filter(function(c){return c.style.display!=='none';}).length;
      cnt.textContent='显示 '+n+' / '+cards.length+' 篇';
      empty.style.display=n?'none':'block';
    }else{cnt.textContent='';empty.style.display='none';}
  }
  clear.addEventListener('click',function(){
    q.value='';topic.value='all';state.kind='all';state.depth='all';
    document.querySelectorAll('.chip[data-k]').forEach(function(c){
      c.classList.toggle('active',c.dataset.v==='all');
    });
    apply();
  });
  bindChips('kind');bindChips('depth');
  q.addEventListener('input',apply);topic.addEventListener('change',apply);
})();
</script>
</body>
</html>
""")
    return "".join(parts)


def main():
    os.chdir(ROOT)
    papers = json.load(open("papers.json", encoding="utf-8"))
    css = open("index_style.css", encoding="utf-8").read()
    out = render(papers, css)
    open("index.html", "w", encoding="utf-8", newline="").write(out)
    print(f"index.html 已生成: {len(papers['notes'])} 篇卡片, {os.path.getsize('index.html')//1024} KB")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
