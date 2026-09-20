# arXiv 分类号系统扫描报告

**范围**：`cs.CV` + `cs.GR` · 提交日期 2025-10-01 ～ 2026-09-20
**目的**：兜住此前"搜索引擎式检索"可能遗漏的条目（重点 2026 年 5–6 月）
**生成日期**：2026-09-20
**数据位置**：`T1_long_video_consistency.txt` ～ `T9_wide_catchall.txt`（同目录，完整候选清单）

---

## 0. 结论摘要

1. **上轮检索确实漏了一大片，而且漏的正是最热的子方向。** 2025-12、2026-01、2026-06、2026-08 四个月在上轮结果里完全空白，其中 2026-06 一个月就有 **15+ 篇"长程一致视频生成 / 视频世界模型记忆"直接相关工作**。
2. **"视频世界模型 + 记忆机制"在本区间内从冷启动走向爆发**：T1 主题逐月命中数 2025-10 的 6 篇 → 2026-06 的 31 篇，是本期最强的信号。
3. **VGGT 家族形成独立谱系**：出现 VGG-T³、VGGT-SLAM 2.0、VGGT-Motion、Mamba-VGGT、VGGT-GS SLAM、PanoVGGT 等至少 6 篇 VGGT 衍生工作，以及大量"免位姿/未标定"前馈重建（OF³GS、StructSplat、Gesplat、LangFlash…）。这与 vggt_human 的 COLMAP 依赖问题直接相关。
4. **本月新增一个可用的评测基准**：`2608.27328 R2M-Bench` 专门评估交互式视频世界模型的**重访记忆一致性**（revisit memory）——这正是 Lyra 2.0 与 OctWorld 各自宣称解决的问题，目前库内笔记缺这个维度的量化依据。
5. **扫描本身有明确边界**（见 §1.4）：只覆盖 cs.CV/cs.GR，且筛选依赖标题。抽样估计主题矩阵漏检约 4%（点估计，小样本，置信区间宽）。

---

## 1. 方法与可核对性

### 1.1 数据获取

| 项 | 值 |
|---|---|
| 数据源 | `arxiv.org/list/<cat>/<YYYY-MM>?skip=N&show=2000`（arXiv 主站 monthly listing，非 API） |
| 分类 | cs.CV、cs.GR |
| 月份 | 2025-10 ～ 2026-09（12 个月） |
| 请求数 | 37 个页面，每页 ≤2000 条 |
| 原始条目 | 38,376 条 → **去重后 37,457 篇唯一论文** |
| 每条字段 | arXiv ID、标题、作者、comments（含会议信息）、subjects |

**为什么不用 arXiv API**：`export.arxiv.org/api/query` 对本机 IP 持续返回 429（实测 6 连发全拒），且官方 `start` 分页在 30000 之后不可靠。listing 页面通道实测稳定。

**并发度实测**：并发 3 路时第 3 路被卡满 300 秒超时；并发 2 路稳定在 4–12 秒/页（3.4 MB）。最终采用 2 路并发。

### 1.2 完整性校验（三重）

| 校验 | 方法 | 结果 |
|---|---|---|
| 页面完整性 | 每个 HTML 文件末尾必须含 `</html>` | 37/37 通过，0 破损 |
| 拉取覆盖 | 用 12 篇已知相关论文（上轮检索确认）反查 | **12/12 命中** |
| 库内交叉 | 库内 68 篇笔记中落在本区间的全部 arXiv ID | 全部命中（唯一例外的 `2511.08892 Lumine` 是 cs.AI 分类，不在扫描范围） |
| 筛选有效性 | 12 篇已知论文是否被主题矩阵召回 | 修词表后 **12/12 召回** |

> 一次实测教训：中途有一个页面（2025-12）下载被中断，文件仍有 3.1 MB。若只看文件大小会当成"已缓存"而静默产生缺口——因此校验必须检查 `</html>` 结尾，不能只看大小。

### 1.3 筛选口径（两层）

- **主矩阵 T1–T8**（多组 AND/OR 组合）：**2,677 篇**（占 7.1%）——高精度，噪声约 15–20%
- **宽口径 T9**（任一核心词命中）：**6,973 篇**（占 18.6%）——高召回，含大量"3DGS 优化型"（加速/剪枝/抗锯齿/水印）噪声
- T9 相对主矩阵的增量：**5,251 篇**，其中强相关词命中 ≥2 的仅 382 篇

主题定义（完整词表见 `topic_scan` 脚本）：

| 主题 | 命中 | 说明 |
|---|---|---|
| T1 长程/世界一致视频生成 | 170 | 与 Lyra 2.0 / OctWorld 同问题 |
| T2 扩散→3D 表示 | 841 | 宽，含大量 3D 生成 |
| T3 前馈/生成式 3D 重建 | 184 | vggt_human 主战场 |
| T4 4D / 动态高斯 | 567 | 含优化型 |
| T5 人体/人脸/avatar | 423 | vggt_human 主战场 |
| T6 几何先验注入生成 | 210 | |
| T7 场景记忆/长时程建图 | 572 | 与 T1 重叠 |
| T8 表面重建/网格提取 | 336 | |
| T9 宽口径兜底 | 6,973 | 用于量化漏检 |

### 1.4 已知局限（**使用本报告前必读**）

1. **未覆盖 cs.AI / cs.LG**。范围限于 cs.CV + cs.GR。实测库内 `Lumine`（2511.08892）因 primary 为 cs.AI 而落在范围外。3D 生成/重建类论文绝大多数挂在 cs.CV，判断影响有限，但若需绝对完备需补扫 cs.LG。
2. **筛选依赖标题，存在系统性盲区**。listing 不含摘要，标题抽象的论文（如 "Lyra 2.0: Explorable Generative 3D Worlds" 全文没有 "diffusion" 一词）无法被关键词矩阵捕获。
   - 量化：从 34,780 篇"未被任何主题召回"的条目中随机抽 50 条人工判读，**2 条高相关**（`2512.10369` 稀疏+运动模糊下的连贯 3DGS；`2607.10792` MAC-Splat 稀疏视角重建），另有 6–7 条边缘相关。
   - 点估计漏检率 **4%**（n=50，95% 置信区间大致 0.5%–14%）。**不要把主矩阵当作完备清单**。
   - 两条漏检项已被宽口径 T9 捞回。
3. **2026-09 不完整**（截至 9-20，仅 1,854 篇，约占整月 40%）。
4. **会议信息来自 comments 字段**，作者若未填写则缺失（不代表未被接收）。

---

## 2. 上轮搜索引擎式检索的覆盖缺口

上轮命中的 12 篇相关工作的月份分布：`2025-10 ×1`、`2025-11 ×1`、`2026-02 ×2`、`2026-03 ×2`、`2026-04 ×1`、`2026-05 ×1`、`2026-07 ×1`、`2026-09 ×3`

**完全空白的月份：2025-12、2026-01、2026-06、2026-08**

本轮扫描显示这些"空白月"的实际相关论文量（主矩阵命中数）：

| 月份 | 主矩阵命中 | 当月论文数 | 上轮是否覆盖 |
|---|---|---|---|
| 2025-10 | 179 | 3,027 | 部分（1 篇） |
| 2025-11 | 198 | 3,212 | 部分（1 篇） |
| **2025-12** | **239** | 3,175 | **无** |
| **2026-01** | **151** | 2,408 | **无** |
| 2026-02 | 190 | 2,767 | 部分（2 篇） |
| 2026-03 | 306 | 4,322 | 部分（2 篇） |
| 2026-04 | 233 | 3,395 | 部分（1 篇） |
| 2026-05 | 311 | 4,040 | 部分（1 篇） |
| **2026-06** | **274** | 3,689 | **无** |
| 2026-07 | 237 | 3,111 | 部分（1 篇） |
| **2026-08** | **226** | 3,376 | **无** |
| 2026-09（不完整） | 133 | 1,854 | 部分（3 篇） |

各月相关占比稳定在 6–8%，因此**空白月的问题不是那个月没货，而是检索方式没有覆盖到**。

---

## 3. 分主题新发现（精选，非全集）

> 完整清单见同目录 `T1_long_video_consistency.txt` ～ `T9_wide_catchall.txt`。以下按"与现有工作的关系"排序。

### 3.1 长程一致视频生成 / 视频世界模型记忆（T1，170 篇）

**与 Lyra 2.0 / OctWorld 正面同问题（重访一致性 + 长程不漂移）**

| arXiv | 标题 | 为什么值得看 |
|---|---|---|
| **2608.27328** | R2M-Bench: Evaluating Revisit Memory via Relative Consistency in Interactive Video World Models | **专门评测"重访记忆"的基准**。Lyra 2.0 与 OctWorld 都宣称解决此问题但各自用自有指标，这是独立第三方口径 |
| **2606.02479** | Retrieve What's Missing: Coverage-Maximizing Retrieval for Consistent Long Video Generation | 覆盖度最大化的历史帧检索——与 Lyra 2.0 的"可见性评分 + 贪心检索 Ns=5"是同一机制的不同解法，可直接对照 |
| **2606.14667** | Memento: Reconstruct to Remember for Consistent Long Video Generation | "重建即记忆"，可能是介于 Lyra 2.0（存帧）与 OctWorld（显式几何）之间的第三条路线 |
| **2603.03482** | Beyond Pixel Histories: World Models with Persistent 3D State | 持久 3D 状态的世界模型——与 OctWorld 的 TSDF 记忆同思路，可对照实现代价 |
| **2606.09828** | Latent Spatial Memory for Video World Models | latent 空间记忆，与 Lyra 2.0 的 latent 操作路线接近 |
| 2512.14614 | WorldPlay: Long-Term Geometric Consistency for Real-Time Interactive World Modeling | 实时交互 + 长期几何一致，Lyra 2.0 的直接竞品 |
| 2606.10671 | FadeMem: Distance-Aware Memory Consolidation for Autoregressive Video Diffusion | 按距离衰减的记忆固化策略 |
| 2608.07408 | Addressable Memory for Video World Models | 可寻址记忆结构 |
| 2608.26902 | Tether the Subject, Release the Scene: Query-Aware Memory Routing for Long-Horizon Autoregressive | 查询感知的记忆路由 |
| 2606.31734 | MemLearner: Learning to Query Context Memory for Video World Models | ECCV 2026；学习如何查询记忆 |
| 2606.23105 | Compression and Retrieval: Implicit Memory Retrieval for Video World Models | 压缩 + 隐式检索 |
| 2606.04527 | Echo-Infinity: Learning Evolving Memory for Real-Time Infinite Video Generation | 实时无限生成 |

**抑制自回归漂移（anti-drifting，Lyra 2.0 的第二个核心问题）**

| arXiv | 标题 |
|---|---|
| 2512.12080 | BAgger: Backwards Aggregation for Mitigating Drift in Autoregressive Video Diffusion Models |
| 2602.06028 | Context Forcing: Consistent Autoregressive Video Generation with Long Context |
| 2603.21366 | Relax Forcing: Relaxed KV-Memory for Consistent Long Video Generation（BMVC 2026）|
| 2608.26794 | Ring Forcing: Towards Precise Long-Term Memory for Autoregressive Video Diffusion |
| 2602.07854 | Geometry-Aware Rotary Position Embedding for Consistent Video World Model |
| 2605.16579 | Attend Locally, Remember Linearly: Linear Attention as Cross-Frame Memory |

> "xxx Forcing" 已形成一个小家族（Context/Relax/Ring Forcing），与 Lyra 2.0 的 self-augmented histories 训练互为替代方案。

**规模与上下文**

| arXiv | 标题 | 备注 |
|---|---|---|
| 2602.02393 | Infinite-World: Scaling Interactive World Models to 1000-Frame Horizons via Pose-Free Hierarchical | pose-free + 1000 帧 |
| 2605.31336 | DecMem: Towards Minute-Long Consistent World Generation with Decoupled Memory | 分钟级 |
| 2605.30519 | OmniMem: Scalable and Adaptive Memory Retrieval for Long Video Generation | |
| 2605.15185 | Quantitative Video World Model Evaluation for Geometric-Consistency | 几何一致性评测 |
| 2603.19137 | GSMem: 3D Gaussian Splatting as Persistent Spatial Memory for Zero-Shot Embodied Exploration | 用 3DGS 当记忆 |
| 2604.01605 | F3DGS: Federated 3D Gaussian Splatting for Decentralized Multi-Agent World Modeling | |
| 2604.08995 | Matrix-Game 3.0 / 2608.29910 Matrix-Game 3.5 | 实时流式交互世界模型系列 |
| 2606.18250 | Future Dynamic 3D Reconstruction: Toward 3D World Modeling with Disentangled Ego-Motion（ICML 2026）| |

### 3.2 VGGT 家族与前馈 3D 重建（T3，184 篇 + T1 中的交叉项）

**VGGT 直接衍生（与 vggt_human 同源）**

| arXiv | 标题 | 备注 |
|---|---|---|
| **2602.23361** | VGG-T³: Offline Feed-Forward 3D Reconstruction at Scale | CVPR 2026，大规模离线前馈重建 |
| **2605.17478** | Mamba-VGGT: Persistent Long-Sequence Video Geometry Grounded Transformer via External Sliding Window | 长序列视频几何，状态空间替换注意力 |
| **2602.05508** | VGGT-Motion: Motion-Aware Calibration-Free Monocular SLAM for Long-Range Consistency | **免标定** + 运动感知 |
| **2601.19887** | VGGT-SLAM 2.0: Real-time Dense Feed-forward Scene Reconstruction | 实时稠密 |
| 2609.19628 | VGGT-GS SLAM: Uncalibrated Monocular Gaussian Splatting SLAM with Feed-Forward Priors | 未标定 + 高斯 |
| 2603.17571 | PanoVGGT: Feed-Forward 3D Reconstruction from Panoramic Imagery | CVPR 2026 |
| 2602.20160 | tttLRM: Test-Time Training for Long Context and Autoregressive 3D Reconstruction | CVPR 2026；**测试时训练**扩上下文 |

**免位姿 / 未标定（直接对标 COLMAP 依赖）**

| arXiv | 标题 | 备注 |
|---|---|---|
| 2606.03254 | OF³GS: On-the-Fly Feed-Forward 3D Gaussian Splatting from Unposed Images | 免位姿 |
| 2606.28321 | StructSplat: Generalizable 3D Gaussian Splatting from Uncalibrated Sparse Views | 未标定稀疏视角 |
| 2605.23287 | LangFlash: Feed-forward 3D Language Gaussian Splatting from Sparse Unposed Images | CVPR 2026 |
| 2605.24304 | ArtSplat: Feed-Forward Articulated 3D Gaussian Splatting from Sparse Multi-State Uncalibrated | 未标定 + 关节体 |
| 2510.10097 | Gesplat: Robust Pose-Free 3D Reconstruction via Geometry-Guided Gaussian Splatting | |
| 2605.22190 | No Pose, No Problem in 4D: Feed-Forward Dynamic Gaussians from Unposed Multi-View Videos | 免位姿 + 4D |
| 2605.09362 | FRUC: Feedforward Dynamic Scene Reconstruction from Uncalibrated Collaborative Driving Video | |
| 2604.06740 | LiveStre4m: Feed-Forward Live Streaming of Novel Views from Unposed Multi-View Video | |
| 2603.00697 | TokenSplat: Token-aligned 3D Gaussian Splatting for Feed-forward Pose-free Reconstruction | |

**其他前馈重建基线与分析**

| arXiv | 标题 | 备注 |
|---|---|---|
| 2603.22851 | UniQueR: Unified Query-based Feedforward 3D Reconstruction | |
| 2603.08055 | Speed3R: Sparse Feed-forward 3D Reconstruction Models | CVPR 2026 Findings |
| 2511.22429 | Fin3R: Fine-tuning Feed-forward 3D Reconstruction Models via Monocular Knowledge Distillation | 微调范式 |
| 2604.09862 | FF3R: Feedforward Feature 3D Reconstruction from Unconstrained Views | CVPR 2026 Findings |
| 2608.29705 | A Calibration Audit of Confidence in Feed-Forward 3D Reconstruction Models | **校准审计**（可信度） |
| 2512.11508 | On Geometric Understanding and Learned Priors in Feed-forward 3D Reconstruction Models | 机理性分析 |
| 2605.11354 | Lite3R / 2605.19539 Trust3R / 2605.06270 Spark3R | 效率与可信度分支 |
| 2605.26115 | TriSplat: Simulation-Ready Feed-Forward 3D Scene Reconstruction | 仿真就绪 |

### 3.3 人体 / 头像前馈重建（T5，423 篇；下列为最相关）

| arXiv | 标题 | 为什么重要 |
|---|---|---|
| **2606.27720** | Scene and Human in One World: Reconstruction in a Feedforward Pass | **场景与人在同一次前馈中重建**——正是 vggt_human 拆分架构（head/body/scene）的目标形态 |
| **2606.29333** | HiReFF: High-Resolution Feedforward Human Reconstruction from Uncalibrated Sparse-View Video | 未标定 + 稀疏视角 + 视频，三个条件全中 |
| **2606.30347** | FFAvatar: Feed-Forward 4D Head Avatar Reconstruction from Sparse Portrait Images | ECCV 2026；稀疏人像→4D 头 avatar |
| 2606.24232 | FiCA: Feed-forward Instant Gaussian Codec Avatars from a Single Portrait Image | 单图秒级 |
| 2604.10259 | Real-Time Human Reconstruction and Animation using Feed-Forward Gaussian Splatting | |
| 2604.25466 | Generalizable Human Gaussian Splatting via Multi-view Semantic Consistency | 泛化性 |
| 2605.02784 | HumanSplatHMR: Closing the Loop Between Human Mesh Recovery and Gaussian Splatting | HMR ↔ GS 闭环 |
| 2606.14841 | Multi-HMR 2: Multi-Person Camera-Centric Human Detection, Mesh Recovery and Tracking | 多人 + 跟踪（与 SAM3 track 去重同问题） |
| 2603.15811 | Feed-forward Gaussian Registration for Head Avatar Creation and Editing | 前馈头模配准 |
| 2604.22865 | MeshLAM: Feed-Forward One-Shot Animatable Textured Mesh Avatar | 单次前馈 + 可动 |
| 2601.12770 | One-Shot Feed-Forward 360° Animatable Avatar via Inpainted UV-Space Gaussian | |
| 2601.13837 | FastGHA: Generalized Few-Shot 3D Gaussian Head Avatars with Real-Time Animation | |
| 2607.19100 | FlexiAvatar: Unified 3D Gaussian Human Avatars Under Arbitrary Body Visibility | 任意可见性 |
| 2604.04787 | AvatarPointillist: AutoRegressive 4D Gaussian Avatarization | CVPR 2026 |
| 2606.13655 | Flex4DHuman: Flexible Multi-view Video Diffusion for 4D Human Reconstruction | 视频扩散 + 4D 人体 |
| 2606.05912 | Self-Learning Expression Deformations for Data-Efficient Gaussian Avatars | 表情形变（与"固定表情系数"策略相关）|
| 2608.18388 | Depth Anything V4: Dynamic 4D Scene Reconstruction via Riemannian Flow Matching | DA 系列新代 |

### 3.4 4D / 动态高斯（T4，567 篇；下列为前馈与时序一致性相关）

| arXiv | 标题 | 备注 |
|---|---|---|
| 2606.19156 | Hand-4DGS: Feed-Forward 3D Gaussian Splatting for 4D Hand Reconstruction from Egocentric Videos | 前馈 4D |
| 2606.29374 | L2D2-GS: Learning to Densify for Feedforward Dynamic Gaussian Scene Reconstruction | 前馈动态 |
| 2606.31388 | One Video, One World: Turning Monocular Video into Physical 4D Scenes | ECCV 2026 |
| 2606.28828 | Ground4D: Consistency-Aware 4D Reconstruction from Monocular Video | 一致性感知 |
| 2510.01119 | Instant4D: 4D Gaussian Splatting in Minutes | NeurIPS 25 |
| 2603.13783 | RetimeGS: Continuous-Time Reconstruction of 4D Gaussian Splatting | CVPR 2026 |
| 2604.04063 | 4C4D: 4 Camera 4D Gaussian Splatting | CVPR 2026 |
| 2604.00538 | TRiGS: Temporal Rigid-Body Motion for Scalable 4D Gaussian Splatting | |

### 3.5 宽口径补充（T9 增量中的高价值项）

抽样漏掉、被 T9 捞回的代表：`2512.10369`（稀疏 + 运动模糊下的连贯 3DGS，与库内"微动人体"主线相关）、`2607.10792` MAC-Splat、`2608.02145` UniqueSplat、`2603.17519` UniSem（Sparse Unposed）、`2608.08585` EvTrajGS（Unposed Event Streams）。

---

## 4. 趋势判断

1. **"长程一致性"已从技巧变成独立子领域**。T1 从 2025-10 的 6 篇涨到 2026-06 的 31 篇，且分化出记忆检索、漂移抑制（"xxx Forcing"家族）、评测基准三条支线。Lyra 2.0 的问题定义（spatial forgetting + temporal drifting）正在被这个社区当作通用框架语言使用。
2. **显式几何记忆 vs 隐式 latent 记忆的路线之争正在展开**。OctWorld（TSDF/八叉树）、`2603.03482`（persistent 3D state）、`2603.19137` GSMem 属显式派；Lyra 2.0、`2606.09828`、Latent Spatial Memory 属隐式派。本期两派都有新工作，尚无定论。
3. **VGGT 正在成为基础设施**。至少 6 篇直接衍生工作 + 大量以前馈 3R 为基线的论文，说明"前馈重建"已从"新方法"变成"默认底座"。对 vggt_human 的含义：**可以开始把 VGGT 当作可替换组件，而不是被绑定的实现**。
4. **免位姿（pose-free / uncalibrated）成为前馈重建的标配卖点**，至少 9 篇明确以此为核心。COLMAP 位姿依赖正在被系统性解决。
5. **3DGS 优化型论文泛滥**（T9 增量中 382 篇强相关里绝大多数属此类：加速、剪枝、压缩、抗锯齿、水印、鲁棒性）。这条线的边际收益可能已不高。

---

## 5. 精读优先级建议

**第一档（3 篇，立即可做）**
1. `2608.27328` **R2M-Bench** —— 给 Lyra 2.0 / OctWorld 的"重访一致性"提供独立评测口径，是判断这两条路线优劣的前提
2. `2606.02479` **Retrieve What's Missing** —— 与 Lyra 2.0 的检索机制正面同题，对照读能看出 Lyra 2.0 的可见性评分是否必要
3. `2603.03482` **Beyond Pixel Histories: World Models with Persistent 3D State** —— 显式几何记忆派，与 OctWorld 对照

**第二档（vggt_human 直接可用，4 篇）**
4. `2606.27720` Scene and Human in One World（场景+人一次前馈）
5. `2606.29333` HiReFF（未标定稀疏视角视频人体重建）
6. `2606.30347` FFAvatar（稀疏人像→4D 头 avatar, ECCV 2026）
7. `2605.17478` Mamba-VGGT（VGGT 的长序列改造）

**第三档（按需）**
- 想要漂移抑制方案集合 → `2512.12080` BAgger + `2602.06028` Context Forcing + `2608.26794` Ring Forcing
- 想要免位姿方案集合 → `2606.03254` OF³GS + `2606.28321` StructSplat + `2605.23287` LangFlash
- 想要评测口径 → `2605.15185`（几何一致性）+ `2608.27328`（重访记忆）
- 想要 VGGT 谱系全貌 → `2602.23361` VGG-T³ + `2602.20160` tttLRM + `2601.19887` VGGT-SLAM 2.0

---

## 6. 复现方式

扫描脚本已归档于本目录 `scripts/`（内部路径为绝对路径写死，复用时需调整各脚本顶部的 `ROOT` 变量）。大体积中间产物（37 个 listing HTML、38,376 条原始 jsonl）已清理。核心方法：

```
1. 逐月抓 https://arxiv.org/list/cs.CV/<YYYY-MM>?skip=<N>&show=2000（curl + 浏览器头，并发 2）
   注意：必须校验响应以 </html> 结尾，不能只判文件大小
2. 解析 <dt>arXiv:ID</dt><dd>list-title/comments/subjects</dd> 配对
3. 按 ID 前缀（YYMM）切月，去重
4. 主题矩阵：多组 AND/OR 关键词组合；另跑一个"任一核心词"的宽口径主题用于量化漏检
5. 三重自检：页面完整性 / 已知论文反查 / 库内 ID 交叉
6. 盲区抽样：从未召回条目随机抽 50 条人工判读，估计漏检率
```

本目录 `T1_*.txt` ～ `T9_*.txt` 为完整候选清单（格式：`arXivID  s=强相关词命中数  标题  [comments]`）。
