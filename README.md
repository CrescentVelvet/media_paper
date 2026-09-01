# media_paper — 论文调研知识库

以「微动人体三维重建 / 数字人」为主线方向的论文调研笔记库：62 篇自包含单文件 HTML 笔记 + 生成式索引。写作规范见 [AGENTS.md](AGENTS.md)。

## 快速上手：用 index.html 找东西

浏览器直接打开 `index.html`，顶部筛选栏支持四重组合筛选（筛选时静态章节自动隐藏，仅显示匹配卡片）：

| 操作 | 场景举例 |
|---|---|
| **搜索框**输入关键词 | 搜「多视角一致性」→ 命中标题/标签/摘要里提到它的所有笔记 |
| 点**类型 chip** | 点「调研综述」→ 只看 11 篇领域全景与选型调研 |
| 点**深度 chip** | 点「深度」→ 只看 16 篇含可改进方向分析的高价值笔记 |
| **主题下拉**选择 | 选「前馈式大重建模型」→ 聚合 VGGT / Pi3 / ReSplat 等 7 篇 |

筛选栏右侧实时显示「显示 N / 62 篇」；结果为空或想重来时，点「✕ 清除筛选」一键重置。

## 维护流程（重要：index.html 是生成物，禁止手改）

`papers.json` 是唯一真相源，`index.html` 由脚本生成。`check.py` 会校验两者同步，手改 index 会被检出。

**新增 / 修改笔记条目**：

```bash
# 1. 编辑 papers.json（加卡片条目或改字段）
# 2. 重新生成索引
python build_index.py
# 3. 校验（commit 前必须通过）
python check.py
```

**修正主题归属**：发现某篇笔记归错主题，直接改 `papers.json` 里那篇的 `topics` 字段，跑一次 `python build_index.py` 即可，不用碰任何 HTML。

**调整外观**：样式在 `index_style.css`（生成时内联进 index.html），改完同样跑 `python build_index.py`。

## 文件说明

| 文件 | 作用 |
|---|---|
| `index.html` | 索引页（**生成物，勿手改**），含搜索 + 类型/深度/主题筛选 |
| `papers.json` | 唯一真相源：62 篇元数据（kind/depth/topics/锚点）+ 8 个静态章节 |
| `index_style.css` | 索引页样式源（生成时内联） |
| `build_index.py` | 生成器：papers.json + index_style.css → index.html |
| `check.py` | 离线完整性校验（死链/收录/图片/生成同步），commit 硬门槛 |
| `check_images.py` | 外链图存活检测（需联网），失效图按规范本地化 |
| `AGENTS.md` | AI 作业规范：真实性硬约束、depth 三档、命名/样式/流程 |
| `topics.json` | 主题骨架快照（已并入 papers.json，留作追溯） |

## 笔记的两个正交分类维度

- **kind 类型**：`note` 论文笔记 / `survey` 调研综述 / `pipeline` 工程方案 / `methodology` 方法论
- **depth 深度**：`deep` 深度（含可改进方向分析）/ `standard` 标准 / `brief` 速览（行业全景）

新笔记写作前必读 `AGENTS.md`：禁止编造、不确定内容必须用【存疑】/【推测】/【待核实】标注、改名必须全库同步引用并通过 `check.py`。
