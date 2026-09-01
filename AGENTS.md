# AGENTS.md — 论文调研与分析笔记编写规范

> 本文件是知识库 `media_paper` 的论文调研作业规范。当被要求"调研某 arXiv/GitHub 链接、提取图像、绘制框图、分点解析"时,严格按此执行。
> 所有分析笔记为**自包含单文件 HTML**(`lang="zh-CN"`),无构建步骤,浏览器直开。
> **写任何内容前必读「二、真实性硬约束」;成稿前必须 `python check.py` 通过。**

---

## 一、调研工作流(从链接到成品)

### 1. 输入解析
- **arXiv 链接**(如 `https://arxiv.org/abs/2410.01425`):提取 arxiv-id `2410.01425`。
- **GitHub 链接**(如 `https://github.com/zhenliuZJU/EVA-Gaussian`):提取仓库名作为短名,从 README 找到论文 arXiv 链接与项目主页。
- **项目主页**(`.github.io`):通常含 Abstract、Method Overview 图、可视化结果图。

### 2. 信息抓取(并行发起)
1. **arXiv abs 页** `https://arxiv.org/abs/<id>` —— 取标题、作者、机构、abstract、提交日期。
2. **arXiv HTML 全文** `https://arxiv.org/html/<id>v2` —— **最重要的内容源**,含完整方法、公式、实验、图。注意取最新版本号(在 abs 页查 submission history,v2/v3...)。
   - ⚠️ HTML 全文可能被截断(超 2000 行/51200 字节),输出会落盘到临时文件,用 Task 工具委派 explore 子代理读取并提取关键节(方法/损失/实验/消融),**不要自己 Read 全文**以免爆上下文。
3. **项目主页** —— 取 Method Overview 图、EVA/模块图、可视化对比图。
4. **GitHub README** —— 取环境配置、训练命令、数据集说明、网络结构线索。
5. **GitHub 源码**(可选,深度调研时) —— `git clone --depth 1 <repo> $TEMP` 到临时目录,读 `train.py`/`lib/*.py`/`config/*.yaml` 验证论文叙述、提取真实超参(如损失权重、特征维度、循环次数)。**源码是检验论文"宣称 vs 实现"差异的关键**。

### 3. 图像提取(两种策略)
- **策略 A — 热链 arXiv HTML 图**:优先用 `<img src="https://arxiv.org/html/<id>v<n>/x1.png" ...>`。前导注释标记来源:`<!-- arXiv HTML figures (from https://arxiv.org/html/<id>v<n>) -->`。
  - 图文件名序列:x1.png, x2.png, ...;部分用命名图:`.../figures/teaser.png`。
  - 标准内联样式:`style="max-width:100%;border-radius:8px;border:1px solid #333;"` 加 `loading="lazy"`。
- **策略 B — 本地图**(arXiv 图失效或知乎深度阅读图):存到 `images/<arxiv-id>/x1.png` 或 `images/<name>-zhihu/x1.jpg`(知乎图为 .jpg)。用 `<div class="figure"><img src="images/..."><div class="caption"><b>图N</b> 说明</div></div>`。
- **图失效处理**:见 commit `6a0112e Fix SR survey: replace broken image refs with PDF links`——改链到 PDF 下载。

### 4. 框图绘制(四代技术,按优先级选)
| 技术 | 适用场景 | 示例 |
|---|---|---|
| **Mermaid.js**(首选,方法密集型论文) | 多阶段 pipeline、模块内部数据流、训练流程 | `3D-20241002-EVA-Gaussian.html` |
| **HTML/CSS 框图**(`.hdiag`/`.hbox`/`.mtree`) | 不依赖 CDN、需轻量嵌入 | `3D-20260720-同事人体重建Pipeline详解.html` |
| **内联 SVG** | 一张"总结性大图",色码分组、复杂连线 | 同上文件 line 1316+ |
| **ASCII `<pre class="ascii">`** | **新文件不要再用了** | 旧文件 4 个,已被 commit `47102e5` 标记迁移 |

**Mermaid 用法**:
```html
<div class="mermaid">
flowchart TD
    INPUT["输入: n 张稀疏视角 RGB 图像"] --> S1
    subgraph S1["阶段一: 3D 高斯位置估计"]
        S1A["AttenUNet"] --> S1B["EVA 模块"] --> S1C["输出: 位置图"]
    end
    style INPUT fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
</div>
...
<script>mermaid.initialize({startOnLoad:true, theme:'default', flowchart:{curve:'basis', useMaxWidth:true}});</script>
```
- 用 `subgraph` 分组、`style` 节点配色(浅底深字)、`<br/>` 换行、`flowchart TD`(纵向)/`LR`(横向)。

### 5. 分点解析模板
**方法密集型论文(推荐 Style A 模板)**:
```
1. 论文摘要
2. 研究背景与动机(对比现有方法局限,用 .grid-3 .card 卡片)
3. 算法总体框架(三阶段概览 + 数学形式化)
4~6. 阶段一/二/三(每阶段:网络结构表 → 数学公式 → 工作流列表 → Mermaid 框图 → 损失)
7. 属性正则化(锚点损失等附加损失)
8. 总损失函数(表格列每项公式/权重/作用)
9. 逻辑流程图(Mermaid:总流程 + 训练流程 + 模块组成)
10. 实验结果(量化表格,用 class="best"/"fail" 标色)
11. 消融实验(每个组件 + ΔPSNR)
12. 可改进方向分析  ← 知识库特色分析章节,见下
13. 总结
```

**通用论文(Style B 模板,14 节)**:
```
📌 论文概要 → 🏗️ 模型架构 → 🎯 关键创新 → ⚙️ 技术细节 → 📐 损失函数 →
📊 数据集 → 📊 实验结果 → 消融 → 🔄 技术路线对比与演进 → 🎯 应用场景 →
💡 个人分析/核心洞察 → 结论 → 👥 研究团队 → 🔗 资源链接
```

### 6. 「可改进方向分析」章节(知识库特色,强烈推荐加入)
位于结论前,从三维度分点(每点为 `.card` 带左色条):
- **方法层面**:如"多视角支持名不副实(代码硬编码 lmain/rmain)"、"1D 窗口假设的几何脆弱性"
- **数据与评估**:如"仅在合成数据集验证"、"缺乏时序一致性评估"
- **工程实用性**:如"深度预训练依赖 GT depth"、"anchor loss 权重固定过大"

每点含:① 问题描述 + **代码佐证**(`code` 引用)、② 改进建议。标优先级 `[高优先级]`/`[中优先级]`/`[低优先级]`。末尾加优先级总览表 + "个人认为最关键的三点"。

**关键原则**:改进点要**有代码/实验佐证**,不能空谈。例:说"多视角名不副实"要引用 `EVANet.forward` 中 `torch.stack([lmain, rmain])`;说"伪影在手脚"要引用消融实验原文。

### 7. 更新 papers.json 并重新生成 index.html(**禁止手改 index.html**)
`index.html` 是生成物,由 `build_index.py` 从 `papers.json`(唯一真相源)+ `index_style.css` 生成。新增笔记流程:
1. 在 `papers.json` 的 `notes[]` 对应分区位置追加条目,字段:`file`(笔记文件名)、`title`、
   `section`(卡片分区: `vg-notes-1`/`vg-notes-2`/`vg-notes-3`/`3d`/`sr`/`meta`)、`kind`、`depth`、
   `topics`(从 `topics` 列表中选,可多选)、`meta`(📅 日期/📄 arXiv/🏢 机构等,原文照抄)、
   `tags`、`summary`(一段摘要,可含 `<strong>`)、`links`(`📖 阅读笔记` 本地 + `📄 arXiv` + `💻 GitHub`)。
   **内容必须取自笔记自身 header,禁止编造**(见「二、真实性硬约束」)。
2. 运行 `python build_index.py` 重新生成 `index.html`(编号自动连续,卡片自动带 kind/depth 徽章与筛选数据)。
3. 运行 `python check.py` —— 它会重新生成 index 并与磁盘文件比对,**手改 index.html 会被检出**。

- 页面样式改 `index_style.css`;静态章节(调研总览/对比表/时间线/总结)内容存于 `papers.json` 的 `extra_sections`,同样改后需重新生成。

---

## 二、真实性硬约束(最高优先级,违反即返工)

本库服务于工程选型决策,**错误信息比没有信息更危险**。以下三条为硬性规定,优先级高于一切排版与模板要求。

### 1. 禁止编造
- **代码**:引用源码必须真实读过(`git clone` 后引用文件路径+行号)。**禁止凭印象编造代码片段、函数名、类名、超参数值**。历史教训:commit `47102e5` 曾清除 AI 编造的代码块。
- **数字**:PSNR/SSIM/FPS/参数量/训练时长等必须来自论文原文(注明表号/章节)或官方源码 README,禁止"估计一个合理值"。历史教训:commit `f4ac3f4` 曾纠正错误的 SOTA 数字。
- **引用**:arXiv ID、作者、机构、会议、日期必须可从 abs 页核实;不存在的链接禁止写入。

### 2. 不确定必须标注(统一格式)
任何无法从原文/源码核实的内容,**必须**用下列统一标记,禁止自由发挥措辞(历史遗留有「不确定/存疑/推测/笔记误差」等 5 种说法,分散且无法检索):

| 标记 | 含义 | 使用场景 |
|---|---|---|
| `【存疑】` | 来源不可靠(口述整理、二手资料、记忆还原) | 同事方案按记忆整理的流程 |
| `【推测】` | 无原文佐证的推断 | "该方法可能使用了……" |
| `【待核实】` | 需后续验证的结论 | 未实际跑通的复现结论 |

- 标记必须**原样包含** `【存疑】`/`【推测】`/`【待核实】` 字样(`check.py` 按此扫描汇总,供定期核实)。
- 建议用 `<span class="uncertain">⚠️【存疑】 ……</span>` 包裹,样式参考 `.highlight.warn`(黄底左条)。

### 3. 改名必须同步全库引用
重命名/移动任何 `.html` 后,按顺序执行:
1. 全库搜索旧文件名(`grep -rn "旧文件名" --include="*.html" --include="*.json" .`),逐一替换为新名;
2. 运行 `python check.py` 确认 0 死链;
3. 通过后才允许 commit。

历史教训:commit `06d83ac` 改名 5 个文件未同步引用,造成全库 48 处断链(commit `91ce20d` 修复)。

---

## 三、文件命名规范

格式:`PREFIX-YYYYMMDD-Name.html`

| Prefix | 领域 | 示例 |
|---|---|---|
| `3D-` | 3D 重建/生成/人体/高斯 | `3D-20241002-EVA-Gaussian.html` |
| `VideoGen-` | 视频生成模型 | `VideoGen-20250326-Wan2.1.html` |
| `SR-` | 超分辨率/图像修复 | `SR-20250728-HYPIR.html` |
| `CV-AI-` | 通用 CV/AI | `CV-AI-20260625-Cosmos3.html` |

- **Name**:有英文短名用英文(`Wan2.1`、`EVA-Gaussian`、`VGGT`);综述/调研用中文并以 `综述`/`调研`/`思路辨析` 结尾(`前馈3D重建模型综述.html`)。
- **日期**:论文 arXiv 提交日期(如 `20250326`);综述用编撰日期。
- **改名**:重命名后必须同步全库引用并跑 `python check.py`,见「二、真实性硬约束」第 3 条。
- commit `d3239b5 整理知识库命名规范` 确立此规范。

---

## 四、HTML 样式规范

### 默认主题(Style B,NVIDIA 绿,适用于 95% 论文)
```css
:root {
  --bg: #0f1117; --card: #1a1d27; --accent: #76b900;  /* NVIDIA 绿,签名色 */
  --accent-dim: #5a8f00; --text: #e0e0e0; --text-dim: #9a9a9a;
  --border: #2a2d37; --tag-bg: #252830; --code-bg: #15171f;
  --warn: #d29922; --red: #f85149;
}
```
- 头部:`<div class="header">` linear-gradient + `border-bottom:3px solid var(--accent)`;h1 + `.meta`(📄 arxiv / 🏢 org / 📅 date / 📂 category)+ `.tags`。
- 节容器:扁平 `.section` 卡片,**节标题用 emoji 前缀**(📌/🏗️/🎯/⚙️/📊/💡/🔗),**不加数字编号**。
- 组件:`.highlight`(绿底左条,变体 `.warn`/`.red`/`.blue`/`.purple`)、`.stat-row`/`.stat`(大数字卡)、`.grid-2`、`.tags`/`.tag`。

### 高端样式(Style A,Mermaid+MathJax,方法密集型论文)
```css
:root{
  --bg:#0f1419; --panel:#1a2029; --accent:#60a5fa; --accent2:#a78bfa;
  --green:#34d399; --orange:#fb923c; --red:#f87171; --code-bg:#0d1117;
}
```
- Hero:`<div class="hero">` 双层渐变 + `<span class="badge">arXiv:ID · 年 · 类</span>` + h1 + `.subtitle` + `.authors` + `.links`。
- 2 列 TOC:`.toc ol { columns:2; column-gap:40px }`。
- 数字编号标题:`<h2><span class="num">N</span>标题</h2>`(渐变方块徽章)。
- `.equation` 包 `$$...$$` + 右浮 `\text{(式 N)}` 标号。
- `.callout.key/.warn/.tip`、`.grid-2/3`、`.card`、`.stage-tag`、表格 `.best`/`.fail`。

### 公式处理(三档,按需选)
| 档位 | 适用 | 实现 |
|---|---|---|
| MathJax | 真公式多 | `<script>MathJax={tex:{inlineMath:[['$','$'],['\\(','\\)']],displayMath:[['$$','$$'],['\\[','\\]']]}}</script>` + `tex-mml-chtml.js async` |
| 纯文本 `.formula` | 少量公式 | Unicode 数学字符(ℒ、‖·‖、×、→) |
| `<code>` 内联 | 极少 | 损失写成 `L_FM = E[...]` |

---

## 五、外部资源规则

- **CDN 仅限**:`cdn.jsdelivr.net/npm/mermaid@10` 与 `cdn.jsdelivr.net/npm/mathjax@3`。**不用** Bootstrap、Font-Awesome、外部 CSS。
- **资源链接**用 emoji 徽章 + `target="_blank"`:`📄 arXiv abs` / `🌐 arXiv HTML 全文` / `📥 PDF` / `💻 GitHub` / `🤗 HuggingFace` / `🌐 项目主页`。
- **图片**:优先热链 arXiv HTML 图(`loading="lazy"`);失效则本地化到 `images/<arxiv-id>/`。**有网络时定期运行 `python check_images.py`** 扫描外链图存活情况,发现失效即本地化(arXiv 图路径绑定版本号,论文出 v2 后旧版图可能消失)。
- **页脚**:`📝 阅读笔记 · 生成于 YYYY-MM-DD · 领域: ...`。

---

## 六、对比表格规范

- 方法对比:用 ✓/✗/~ 标记,CSS 类 `.check`(绿)/`.cross`(红)/`.partial`(橙);或直接 emoji ✅/❌/~。
- 最优行高亮:`class="best"`(绿粗)或 `style="background:rgba(108,142,239,0.12)"`。
- 失败项:`class="fail"`(红),如 GPS-Gaussian 在 Δ=90° 标"失败"。

---

## 七、分析深度要求

1. **不只复述论文**:要有"个人分析/核心洞察"、"可改进方向"、"技术路线对比与演进"等增值章节。
2. **代码佐证**:深度调研时读源码,把真实超参/损失权重/硬编码限制写入分析(如 EVA-Gaussian 的 `10**3*L_anchor` 权重、双视角硬编码)。
3. **跨论文引用**:用本地相对链接 `<a href="3D-20260720-MHR.html">MHR</a>` 关联知识库内兄弟笔记。
4. **演进定位**:放"技术路线对比与演进"表(范式 → 代表方法 → 先验 → 局限),把论文置于领域脉络中。

### 深度分级(depth,新笔记必须声明)

深度与视觉样式(Style A/B)正交:Style 管外观,depth 管内容要求。

| 级别 | 适用 | 章节要求 |
|---|---|---|
| `deep` | 与项目主线强相关、需精读的方法 | 完整模板 + Mermaid/MathJax + 「可改进方向分析」(必须有代码/实验佐证) |
| `standard` | 一般论文笔记 | Style B 14 节模板,含「个人分析/核心洞察」 |
| `brief` | 行业全景速查(如 VideoGen 模型谱系) | 概要/架构/关键创新/应用场景/资源链接 5 节即可,不强制深度章节 |

- **声明位置**:笔记头部 `.meta` 加 `📊 deep`(或 `standard`/`brief`);`index.html` 卡片 `.tags` 同步标注。
- **定级时机**:立项调研时先定 depth 再动笔,避免把 brief 写成 standard 浪费时间、或把 deep 写成 standard 丢失价值。
- 存量 62 篇的分级与主题映射记录在 `topics.json`,可作为定级参考。

---

## 八、验证清单(成稿前)

**硬性项(脚本校验,不通过禁止 commit)**:
- [ ] `python check.py` 通过(0 站内死链、index 全收录、本地图片完整)

**真实性项(见「二、真实性硬约束」)**:
- [ ] 无编造:代码引用有真实文件路径,数字有原文出处
- [ ] 不确定内容已用 `【存疑】`/`【推测】`/`【待核实】` 统一标注(无自由措辞)
- [ ] 笔记头部 `.meta` 与 index 卡片已声明 depth(deep/standard/brief)

**规范项**:
- [ ] 文件名符合 `PREFIX-YYYYMMDD-Name.html`
- [ ] `<html lang="zh-CN">`
- [ ] 主题色与所选 Style 一致(NVIDIA 绿 / EVA 蓝)
- [ ] 资源链接含 arXiv abs + HTML 全文 + GitHub(若有)+ 项目主页(若有)
- [ ] 图像有 `loading="lazy"` 与 `alt`
- [ ] Mermaid/MathJax(若用)CDN 与 init 脚本正确
- [ ] 实验表格含 PSNR/SSIM/LPIPS 等量化指标,最优行标 `.best`
- [ ] deep 级笔记含「可改进方向分析」章节(三维度 + 优先级表 + 代码佐证)
- [ ] 已更新 `papers.json` 并运行 `python build_index.py` 重新生成 index(禁止直接改 index.html)
- [ ] commit 信息中文,描述新增/改动章节
