# media_paper 工作区长期记忆

> 项目:`C:\code\media_paper` — 论文调研知识库(自包含单文件 HTML 笔记 + 生成式索引)。作业规范以 `AGENTS.md` 为准,本文件只记规范之外的约定与踩坑。

## 1. 格式统一(2026-09-17 定案)
- 全库**只保留一套「方法密集型高端格式」**(`.hero` + `.toc` 2 列 + `<h2><span class="num">N</span>` + Mermaid + MathJax,蓝紫 `#60a5fa`/`#a78bfa`)。
- 旧的 NVIDIA 绿扁平样式(`--accent:#76b900`、`.header` + `.section` + emoji 节标题)**已废弃**。
- 判定新旧样式:`class="hero"` 判新,`class="header"` 判旧。
- 存量迁移走**渐进路线**:新笔记一律新规范;旧笔记在因补内容/修错被打开时顺带迁移;不做一次性批量重排。`python check.py` 输出进度与待迁移清单。
- 统一的核心不止样式,还有**四类内容精度硬要求**:① 思路(失败模式/关键假设/假设失效条件)② 算法逻辑(符号表 + 张量维度级数据流 + 机制解释)③ 工程细节(源码超参带 file:line + 资源账 + 落地坑)④ 同类方法对比(固定维度横向表 ≥3 方法含 baseline 以外 + 对比结论 + 演进定位 + 库内交叉链接)。

## 2. 工具链踩坑
- **check.py 跨天误报(已修)**:`index.html` 页脚含 `生成于 YYYY-MM-DD`,`build_index.py` 每次生成写当日日期,导致隔天再跑 `check.py` 必然报「index.html 与 papers.json 不同步」。修法是比对前把日期正则归一化(`GEN_DATE_RE`),真实手改仍会被检出。新增这类带时间戳的生成内容时要注意同类问题。
- **bash 环境缺 coreutils**:该环境下 `ls`/`head`/`tail`/`dirname` 不可用(报 command not found),用 `python -c` 或专用工具替代。
- `index.html` 是生成物,**禁止手改**;改 `papers.json` 后跑 `python build_index.py`,再跑 `python check.py`。
- **提交一律列明具体路径,禁用 `git add -A`**(2026-09-17 踩坑):一次误把 `.workbuddy/memory/*` 与 `images/2607.20789/`(5 张全库无引用的孤儿图)带进提交,只能 `git reset --soft HEAD~1` 撤回重提。
- `.workbuddy/` 此前一直未纳入版本管理,`.gitignore` 里也没有它 —— 是否入库属未决事项,动它之前先问用户。
- **本仓库可能被多个会话同时写入**(2026-09-17 实测):`papers.json` / `index.html` / 本记忆文件均为并发热点。判断"未跟踪文件是否属于别人在飞的活",看 mtime(秒级)与 `git status` 的两次快照差异;在别人写作中途提交会把半成品固化进历史。**提交前先确认没有文件正在被写入,且不要替别的会话做提交决定。**
- `images/2607.20789/` 是 **3D-GIMP(arXiv 2607.20789)的配图**,2026-09-17 起由笔记 `3D-20260722-3D-GIMP.html` 正式引用,不再是悬空图片。(此前文字曾误判为「SHARP 调研遗留」——`2607.20789` 本身即 3D-GIMP 的 arXiv ID,与 SHARP 无关,SHARP 是 `2512.xxxxx` 系列。**教训:遇到按 arXiv ID 命名的孤儿图目录,先去 `arxiv.org/abs/<id>` 查证标题再下结论。**)现目录含 6 张图,均被该笔记引用。
- **arXiv 配图获取**(2026-09-17 实测):
  - **不能靠猜文件名**。`https://arxiv.org/html/<id>v1/x1.png` 这类序列名常直接 404;不同论文用命名图(如 `2607.20789v1/teaser_v3.jpg`)。
  - 正确做法:用带浏览器 UA 的 GET 抓 `https://arxiv.org/html/<id>v1` 的 HTML,正则提取 `<img src="([^"]+)">`;页内 src 是**相对路径**(`2607.20789v1/teaser_v3.jpg`),完整 URL = `https://arxiv.org/html/<id>v1/<name>`。
  - **HEAD 一律被反爬拦截**(404/406),必须 GET;GET 时带 `Accept: image/avif,image/webp,image/*,*/*;q=0.8` + UA + `Referer`。
  - **偶发 406 需重试**:本次 `ablation_1.jpg` 重试 4 次仍 406,其余 6 张一次成功 → 单张失败不要放弃整批。
  - 图注(Fig.N + caption)也在 HTML 里,`<figcaption class="ltx_caption">` 与 `<figure id="S0.F1">` 配对,可直接提取写入 `figures/<id>.json`。
- **本仓库提交**:`media_paper: <中文简短描述>`(带项目名前缀),标题一行 + 正文 ≤3 行;提交时列明具体路径,**禁用 `git add -A`**。`.workbuddy/` **已于 2026-09-18 纳入版本管理**(commit 80a2b1a),改记忆文件也走常规 commit。
- **配图下载必须双向 diff**(2026-09-20 踩坑):批量下载脚本会静默漏文件(子目录图扁平化后名字对不上),只报"下载完成"不代表笔记引用的图都到位。**收尾动作** = 用「笔记内 `src="images/..."` 全集」与「`images/<id>/` 目录文件全集」双向 diff,同时查出缺失与孤儿;下载后用 `tail -8` 判 `IEND` 确认 PNG 完整。
- **孤儿图优先"挂进对应段落"而非删除**:若论文里该图对应的章节笔记已写到,直接把图插进去(本次 `action_model.png`→§11.4、`firstdepth.png`→§9.6)。
- **图号编排**:`图N` 按文档出现顺序编号。中途插图后若顺序脱节,用正则 `<b>图(\d+)(\(` 捕获图注 + 映射表批量替换(避免链式碰撞),再校验位置序列递增、无重号、交叉引用同步。**插入前先查重**——笔记内可能已有同题材图(本次 §15 图10 就是同一张 `invsible.png`)。
- **stat 卡等"提炼数字"核对优先级高于正文表格**:本次 OctWorld stat 卡写"3.1–2.0× PSNR 提升"而论文实为 +1.39 dB(全文无 3.1× 表述),正文表格逐格对比却全部命中。凭空数字最易出现在提炼型短句里。
- **`papers.json` 的 summary 只允许 `<strong>`**:全库 summary 无 `<a>`、无 LaTeX(`$...$`),新条目保持一致,否则 index 卡片渲染异常。
- **会话可能跨天,`<current_time>` 注入值会过时**:判断"今天是哪天"以系统时钟为准(本次注入 09-18、实际 09-20)。
- **会议信息必须回 abs 页 comments 字段核实**,不能从同系列论文推断(上一轮曾把 Lyra 1.0 的 ICLR 2026 误挂到 2.0)。

## 3. 文档同步清单(改规范时必查)
改 `AGENTS.md` 的规范条目后,按下表逐项排查,否则会留下自相矛盾的文档:
- `README.md`:规范描述、笔记篇数(现 68)、维护流程小节。
- `CV-AI-20260813-用AI做论文调研经验分享.html`:3.2 模块清单 / 3.3 验证清单 / 3.4 样式选型 / §9 索引设计 —— 已按统一格式改写(commit c05de7e),后续改规范仍需复查。
- `papers.json`:相关条目的 tags/summary 是否仍准确 → 改完必须 `python build_index.py`。
- `check.py`:若规范新增可脚本化的约束项,同步加校验或报告项。
- 全库 grep 旧措辞(如 `Style A`、`76b900`、旧篇数)确认无遗漏。
