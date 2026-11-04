# InfiniSplat 论文信息提取报告

- **论文**:InfiniSplat: Implicit Gaussian Decoding for Large-Baseline Monocular View Synthesis
- **arXiv**:2608.02437(cs.CV);DOI:10.48550/arXiv.2608.02437
- **收录**:Accepted to SIGGRAPH Asia 2026 (Journal Track);代码 https://github.com/zju3dv/InfiniSplat ;项目页 https://zju3dv.github.io/InfiniSplat
- **提取来源**:`_archive/infini_v1_full.html`(full HTML,水印为 **v1**,arXiv:2608.02437v1 [cs.CV] 03 Aug 2026)与 `_archive/infini_v1_abs.html`(abs 页,当前版本 v2)
- **关键词**:Novel view synthesis, 3D Gaussian splatting, feed-forward reconstruction, single-image 3D reconstruction

---

## 1. 完整作者列表与机构

来自 abs 页 `<div class="authors">` 与 full HTML 作者区(LaTeXML),共 10 位作者:

| # | 作者 | 机构 | 备注 |
|---|------|------|------|
| 1 | Jiawei Wang | State Key Laboratory of CAD&CG, Zhejiang University, China | 共同一作("These authors contributed equally");jiawei-wang@zju.edu.cn |
| 2 | Hao Yu | Zhejiang University, China | ritianyu@zju.edu.cn |
| 3 | Yongzhen Hu | Zhejiang University, China | 22451272@zju.edu.cn |
| 4 | Xinyi Yang | Zhejiang University, China | 3240105610@zju.edu.cn |
| 5 | Tao Ni | Udeer.ai, China | nitao@udeer.ai |
| 6 | Xin Zhan | Udeer.ai, China | zhanxin@udeer.ai |
| 7 | Junbo Chen | Udeer.ai, China | 通讯作者("Corresponding authors");junbo@udeer.ai |
| 8 | Xiaowei Zhou | State Key Laboratory of CAD&CG, Zhejiang University, China | xwzhou@zju.edu.cn |
| 9 | Ruizhen Hu | Shenzhen University, China | ruizhen.hu@gmail.com |
| 10 | Sida Peng | Zhejiang University, China | pengsida@zju.edu.cn |

注:HTML 中仅 Jiawei Wang 标注了 equal-contribution 注记,未明确第二位共同一作是谁【待核实】。

## 2. 方法管线

### 2.1 总体框架(§3.1,Figure 2)

- 输入图像 **I ∈ R^{H×W×3}**,一次前馈输出高斯集合 **G = {g_i}_{i=1}^N**,每个高斯存 position、scale、rotation、color、opacity。
- **两条并行预处理分支** + **两阶段紧耦合核心**:
  1. **并行预处理**:冻结的单目几何模型 Φ_geo 预测 dense depth map D 与相机内参 K̂(几何 scaffold);可训练的双分支图像编码器 Φ_img 提取 DINO 语义特征图 F_dino 与 CNN 纹理特征图 F_cnn。
  2. **耦合核心**:(1) Geometry-guided sampling **Q** 由预测深度构造 surface-aligned 2D supports,把深度反投影得 per-patch 3D 表面积、按面积比例分布 supports、并把每个 support 初始化为 base Gaussian;(2) Implicit Gaussian decoding **D_θ** 在每个 support 处双线性查询 F_dino/F_cnn,经 gated 融合后预测 position/scale/rotation/color/opacity 的**有界(bounded)更新**。
- 流水线公式(§3.1 Eq. 1-4):
  - (D, K̂) = Φ_geo(I)
  - (F^dino, F^cnn) = Φ_img(I)
  - (S, Ḡ) = Q(D, I, K̂)
  - G = D_θ(Ḡ, S, F^dino, F^cnn)
- 论文强调两阶段互相依存:sampling 摆脱 pixel grid 但产生不规则布局,per-pixel 回归无法处理;implicit decoding 可处理任意布局但无几何 scaffold 则缺乏表面感知(§3.1)。

### 2.2 几何先验预测(§3.1、§3.4)

- 使用**冻结的预训练单目深度模型**,论文举例 **DepthPro**(Bochkovskiy et al., 2025),同时预测 dense depth D 与相机内参 K̂。
- **InfiniSplat-RGB**:几何 scaffold 完全来自 DepthPro(仅 RGB 输入)。
- **InfiniSplat-LiDAR**:改用 **InfiniDepth-Metric**(Yu et al., 2026),由 RGB + 稀疏深度 prompt 估计 dense depth。
- 两变体中几何先验均冻结;深度/法线方面:论文只用**深度**(未用法线);相机内参 K̂ 由该单目模型估计。

### 2.3 DINO/CNN 双分支特征提取(§3.3 "Feature Query"、§1、§4.1)

- **DINO 分支**:DINOv3 **ViT-L/16** backbone(Siméoni et al., 2025),取最后一层 patch tokens reshape 成高层语义特征图;**单尺度**(明确不用多尺度 DINO 特征金字塔)。
- **CNN 分支**:128 通道 CNN,以 **7×7 stride-2 卷积**开始,后接 **8 个 3×3 残差块**;多尺度特征经 **3×3 卷积**融合、再经 **1×1 卷积**投影到 **C=128** 的特征图,保留局部纹理与边缘线索。
- 在每个 support 坐标 q_i 处对两特征图做**双线性网格采样**:f^dino_i = B(F^dino, q_i),f^cnn_i = B(F^cnn, q_i)(§3.3 Eq. 6)。该查询方式借鉴 InfiniDepth 的 local implicit decoder,但 InfiniSplat 输出的是整套 3D 高斯基元而非单通道图像/深度信号(§2.2)。

### 2.4 Geometry-guided support 采样(§3.2 "Geometry-Guided Sampling")

具体规则(可由 depth-induced local surface structure 决定 2D supports):

1. 像素 p 经反投影 X(p) = Π^{-1}(p, D(p); K̂) 得 3D 点(§3.2 Eq. 2)。
2. 相邻像素构成的局部三角形 t = (p_a, p_b, p_c),其反投影后的 **3D 面积**作为该局部表面块的采样权重(§3.2 Eq. 3):
   **A_t = 1/2 · || (X(p_b) − X(p_a)) × (X(p_c) − X(p_a)) ||_2**
3. 采样前**丢弃顶点相对深度变化过大的候选三角形**,防止面片跨越前景–背景深度不连续(§3.2)。
4. 面积归一化为采样分配权重(§3.2 Eq. 4):**w_t = A_t / Σ_{t'} A_{t'}**。面积更大或倾斜(slant)更强的局部表面被分配更多样本。
5. 在对应 **2D 三角形区域内**生成采样查询坐标 {q_i}_{i=1}^N,即 supports。

**Base Gaussian 初始化**(§3.2):每个 q_i 初始化 base Gaussian ḡ_i = (μ̄_i, s̄_i, r̄_i, c̄_i, ᾱ_i),其中 **μ̄_i = Π^{-1}(q_i, D(q_i); K̂)**(bilinear 采样深度反投影),**c̄_i = I(q_i)**(bilinear 采样图像颜色);scale、rotation、opacity 用统一基础初始化。后续 decoder 只预测对该 base set 的参数更新。

### 2.5 Query-conditioned implicit decoder 结构(§3.3)

解码器分**三步**:Feature Query → Feature Fusion → Gaussian Parameter Update。

1. **Feature Query**(§3.3):如上,在 q_i 处双线性查询 F_dino 与 F_cnn。query 即 geometry-guided 采样得到的 support 坐标 q_i(不是自由学习的 query token)。
2. **Feature Fusion**(§3.3 Eq. 7-8):CNN 特征先投影(P)到 DINO 特征维度,再用 **channel-wise 门控融合**自适应平衡语义与外观:
   - α_i = σ( W_g [ f^dino_i , f̃^cnn_i ] )
   - **h_i = α_i ⊙ f^dino_i + (1 − α_i) ⊙ f̃^cnn_i**
   h_i 为送入 Gaussian MLP 的融合描述子。
3. **Gaussian Parameter Update**(§3.3 Eq. 9-11):MLP_θ 把 h_i 映射为高斯更新
   **Δg_i = (Δu_i ∈ R^2, Δz_i, Δs_i ∈ R^3, Δr_i ∈ R^4, Δc_i ∈ R^3, Δα_i) ∈ R^14**。
   - 位置:Δu_i 为图像平面位移、Δz_i 为深度方向位移,经 **μ_i = Π^{-1}( ū_i + λ_xy·Δu_i , d̄_i + λ_z·Δz_i ; K̂ )** 反投影为最终 3D mean(有界,补偿单目深度误差)。
   - scale/color/opacity:在对应激活函数 ψ_a 的无约束空间做加性更新 **g = ψ_a( ψ_a^{-1}(ḡ) + λ_a·Δg )**(follow SHARP),保证属性合法。
   - rotation:在 base 四元数上预测朝向更新并归一化。

- **输出高斯属性**:position(3D)、scale(3)、rotation(4 元数)、color、opacity。
- **颜色为 RGB 3 维**(c_i ∈ R^3,初始化直接取图像颜色):论文**未使用球谐(SH)颜色**,全文无 SH / spherical harmonics 表述,故 SH 阶数不适用/未提及。
- decoder 为所有 support 共享的同一 MLP(共享 feature query、fusion、Gaussian MLP),学习统一更新规则,天然处理不规则 support 布局。
- 【待核实】decoder MLP 的具体**层数与隐藏维度**正文未给出(§4.1 仅给出 backbone 与 CNN 结构)。

## 3. 关键超参(§4.1 "Implementation Details"、§3.4)

- **Backbone**:DINOv3 **ViT-L/16**(Siméoni et al., 2025);CNN 为 **128 通道**(7×7/s2 卷积 + 8 个 3×3 残差块,3×3 融合卷积 + 1×1 投影到 C=128)。
- **特征维度**:CNN 特征图 C=128;DINO 特征为 ViT-L/16 最终层 patch tokens(CNN 特征先投影到 DINO 维度再融合,具体 DINO 维度数正文未写【待核实】)。
- **训练数据**:Hypersim(Roberts et al., 2021);每个训练样本含 1 个 context view + **3 个 target views**。
- **支持点/高斯数**:每张输入图像采样 **1.5M** 个 Gaussian supports(即约 1.5M 个高斯)。
- **训练分辨率**:正文未给出【待核实】(评测时保留各数据集原始长宽比,目标尺寸 ETH3D 2016×1344、ScanNet++ 1536×1024、Tanks-and-Temples 与 DL3DV 1920×1080)。
- **Batch size**:per-GPU batch size = 1。
- **训练步数/硬件**:8 张 **NVIDIA H20** GPU,约 **100K** 步。
- **优化器与学习率**:**AdamW**,lr = **5×10^{-5}**。
- **损失函数**(§3.4,权重来自 §4.1):
  - L = λ_rgb·L_rgb + λ_perc·L_perc + λ_reg·L_reg,其中 **λ_rgb = 1, λ_perc = 1, λ_reg = 0.1**。
  - **L_rgb**:所有 target views 的 L1 重建损失(§3.4 Eq. 13)。
  - **L_perc**:跟随 SHARP 的感知损失,冻结 VGG 多层特征距离 + Gram 矩阵距离(§3.4 Eq. 14),**γ = 10**,仅作用于 target views。
  - **L_reg = λ_scale·L_scale + λ_smooth·L_smooth**,**λ_scale = 0.1, λ_smooth = 0.1**;log-scale 边界 **[ℓ_min, ℓ_max] = [−8, −3]**(归一化高斯尺度空间);L_smooth 约束相邻 supports 间 scale 与 opacity 局部平滑(§3.4 Eq. 15-17)。

## 4. 推理规格

- **输入分辨率**:正文未给出统一输入分辨率【待核实】;评测按数据集原始长宽比,目标尺寸 ETH3D 2016×1344、ScanNet++ 1536×1024、Tanks-and-Temples / DL3DV 1920×1080(§4.1)。
- **输出高斯数量**:默认 **1.5M**;消融覆盖 0.5M / 1.0M / 1.5M / 2.0M(Table 3)。
- **推理耗时**(Table 3,ScanNet++;Inference 为表示推理时间,Rendering 为高斯渲染时间):
  | Budget | PSNR | SSIM | LPIPS | Inference | Rendering |
  |---|---|---|---|---|---|
  | 0.5M | 18.779 | 0.785 | 0.359 | 0.444s | 0.004s |
  | 1.0M | 21.180 | 0.848 | 0.294 | 0.552s | 0.007s |
  | 1.5M | 22.240 | 0.864 | 0.270 | 0.598s | 0.009s |
  | 2.0M | 22.237 | 0.864 | 0.271 | 0.772s | 0.011s |
- **推理硬件**:正文未说明【待核实】(训练硬件为 8×NVIDIA H20)。

## 5. 实验主表数字(Table 1,zero-shot NVS;§4.1、§4.2)

**注意**:论文实际评测数据集为 **ETH3D / ScanNet++ / Tanks-and-Temples / DL3DV**(带 metric poses 的真实场景数据集,均不参与训练),而非 Replica/ScanNet/Matterport3D。每个数据集 512 对 source-target 对(由 10 连续视角的轨迹窗口生成,要求 frustum overlap > 60%,按 [0,0.5)/[0.5,1)/[1,2)/[2,∞) 米四个 baseline 区间各取 128 对,固定随机种子)。每个单元格格式为 **PSNR / SSIM / LPIPS**;PSNR、SSIM 越高越好,LPIPS 越低越好。

### 5.1 RGB-only / monocular methods

| Method | ETH3D | ScanNet++ | Tanks-and-Temples | DL3DV | Avg. |
|---|---|---|---|---|---|
| LVSM | 17.306 / 0.532 / 0.488 | 13.177 / 0.499 / 0.538 | 13.696 / 0.394 / 0.531 | 14.249 / 0.311 / 0.518 | 14.607 / 0.434 / 0.519 |
| LagerNVS | 18.130 / 0.598 / 0.462 | 16.749 / 0.634 / 0.395 | 16.844 / 0.661 / 0.371 | 18.118 / 0.510 / 0.571 | 17.460 / 0.601 / 0.450 |
| Flash3D | 18.546 / 0.874 / 0.239 | 17.375 / 0.782 / 0.350 | 15.952 / 0.674 / 0.326 | 17.502 / 0.622 / 0.395 | 17.344 / 0.738 / 0.328 |
| Flash3D-DepthPro | 17.917 / 0.853 / 0.257 | 17.561 / 0.775 / 0.367 | 12.168 / 0.652 / 0.410 | 17.602 / 0.642 / 0.405 | 16.312 / 0.731 / 0.360 |
| SHARP | 19.046 / 0.868 / 0.241 | 20.801 / 0.838 / 0.273 | 15.750 / 0.674 / 0.310 | 18.305 / 0.652 / 0.370 | 18.475 / 0.758 / 0.299 |
| **InfiniSplat-RGB** | **20.531 / 0.895 / 0.220** | **22.240 / 0.864 / 0.270** | **17.118 / 0.695 / 0.306** | **21.685 / 0.772 / 0.310** | **20.394 / 0.806 / 0.277** |

### 5.2 RGB+DepthSensor / LiDAR-conditioned methods

| Method | ETH3D | ScanNet++ | Tanks-and-Temples | DL3DV | Avg. |
|---|---|---|---|---|---|
| ADGaussian | 12.752 / 0.749 / 0.337 | 10.474 / 0.565 / 0.506 | 13.523 / 0.604 / 0.412 | – | 12.249 / 0.639 / 0.418 |
| **InfiniSplat-LiDAR** | **25.880 / 0.946 / 0.151** | **24.148 / 0.896 / 0.237** | **17.617 / 0.712 / 0.287** | –(DL3DV 无可用源深度输入,未评测) | **22.548 / 0.851 / 0.225** |

§4.2 关键结论:
- InfiniSplat-RGB 在四个 RGB-only 数据集上 PSNR/SSIM/LPIPS 全部第一;平均较 SHARP **+1.919 PSNR、+0.048 SSIM、LPIPS −0.022**;较 Flash3D / Flash3D-DepthPro / LagerNVS 平均 PSNR 分别 **+3.050 / +4.082 / +2.934**。
- 分数据集较 SHARP 的 PSNR 提升:ETH3D **+1.485**、ScanNet++ **+1.439**、T&T **+1.368**、DL3DV **+3.380**。
- InfiniSplat-LiDAR 在有源深度的三个数据集平均 **22.548/0.851/0.225**,较 ADGaussian **+10.299 PSNR、+0.212 SSIM、LPIPS −0.193**。

## 6. 变体:InfiniSplat-RGB vs InfiniSplat-LiDAR(§3.4 "Model Variants")

- 同一框架下的两个变体:
  - **InfiniSplat-RGB**:本文主设定,输入仅单张 RGB 图像,几何 scaffold 来自 **DepthPro**。
  - **InfiniSplat-LiDAR**:除 RGB 外额外接收**稀疏深度或 LiDAR prompt**,通过 **InfiniDepth-Metric**(Yu et al., 2026)获得更强的几何条件。具体输入形式:**每幅源视图从源视图深度采样 1,500 个稀疏深度样本作为 prompt**,InfiniDepth-Metric 由 RGB + 这些 prompt 估计 dense depth。
- 两变体共享 geometry-guided 灵活 support 采样、query-conditioned implicit Gaussian decoder 及后续高斯生成管线;差异仅在几何先验的输入形式。
- 几何先验在两个变体中均**冻结**;双分支图像分支、特征融合模块与 Gaussian MLP 可训练。

## 7. 消融实验(§4.4,Table 2;ETH3D / ScanNet++,格式 PSNR / SSIM / LPIPS)

| 变体 | ETH3D | ScanNet++ |
|---|---|---|
| **Full model** | **20.531 / 0.895 / 0.220** | **22.240 / 0.864 / 0.270** |
| w/o learned updates(base GS only) | 18.819 / 0.877 / 0.237 | 19.861 / 0.833 / 0.298 |
| w/o DINO | 11.465 / 0.768 / 0.336 | 12.501 / 0.655 / 0.431 |
| w/o CNN | 18.646 / 0.873 / 0.240 | 20.368 / 0.833 / 0.293 |
| w/o Gaussian regularization | 19.741 / 0.884 / 0.231 | 20.717 / 0.836 / 0.299 |
| w/o Geometry-guided Sampling | 19.934 / 0.888 / 0.227 | 21.576 / 0.855 / 0.274 |
| w/o Implicit Decoder | 18.678 / 0.873 / 0.240 | 20.811 / 0.833 / 0.290 |

变体定义(§4.4):
- **w/o learned updates**:只保留由深度与采样颜色初始化的 base Gaussians,不预测学习更新。
- **w/o DINO**:去掉 DINO 分支,仅保留 CNN 低层特征。
- **w/o CNN**:去掉 CNN 分支,仅保留 DINO 特征。
- **w/o Gaussian regularization**:仅用 RGB 重建损失与感知损失训练,去掉高斯正则。
- **w/o Geometry-guided Sampling**:把几何引导 support 换成 pixel-aligned supports,保留后续 implicit decoding。
- **w/o Implicit Decoder**:去掉 query-conditioned implicit decoder,改用 pixel-aligned 的 **DPT(Dense Prediction Transformer,Ranftl et al., 2021)decoder** 预测高斯参数。

消融要点(§4.4 各小节):
- **Learned updates**:去掉后 ETH3D PSNR 降 1.712、ScanNet++ 降 2.379(即 20.531→18.819、22.240→19.861);渲染变糊,说明模型并非简单渲染提升后的深度图。
- **Dual-Branch Image Encoder**:去 DINO 破坏最大(ScanNet++ PSNR 22.240→12.501,LPIPS 0.270→0.431),跨数据集泛化失败、出现大洞;去 CNN 也稳定下降(ScanNet++ 20.368 / 0.293),边界与细节变糊。
- **Gaussian Regularization**:去掉后 ScanNet++ PSNR 22.240→20.717,LPIPS 0.270→0.299;产生退化(过薄、半透明)高斯。
- **Geometry-guided Sampling & Implicit Decoding**:w/o Geometry-guided Sampling ScanNet++ 降至 21.576 / 0.855 / 0.274(大侧视角下沿 pixel-aligned supports 开裂);w/o Implicit Decoder 降至 20.811 / 0.833 / 0.290(裂缝、孔洞更严重)。两者联合作用带来完整提升。
- **Support Budget**(Table 3,见 §4):0.5M 明显不足,1.0M→2.0M 进入收益递减,默认 1.5M。
- **Prompt Depth Robustness**(Table 4,ETH3D 上对 1,500 个稀疏深度 prompt 施加乘性噪声 d' = d(1+ε),ε ~ N(0, σ²)):
  | Noise σ | PSNR | SSIM | LPIPS |
  |---|---|---|---|
  | 0% | 25.880 | 0.946 | 0.151 |
  | 1% | 25.439 | 0.944 | 0.156 |
  | 3% | 24.337 | 0.937 | 0.170 |
  | 5% | 23.595 | 0.931 | 0.179 |
  指标随噪声平滑单调退化,无突变失效。

## 8. 相关工作定位(§2)

- **§2.1 Single-Image Novel View Synthesis**:论文把 **Splatter Image**(Szymanowicz et al., 2024)、**Flash3D**(Szymanowicz et al., 2025a)、**SHARP**(Mescheder et al., 2025)、**ADGaussian**(Song et al., 2025)列为最直接相关的单图 feed-forward 3DGS 方法;指出它们"基本遵循 pixel-aligned 生成范式",高斯支持点被规则图像格点约束,大视角变化下易出现裂缝、孔洞与不稳定几何。InfiniSplat 则面向 surface-aligned 高斯生成,用 geometry-guided supports + implicit decoder 突破 pixel-aligned 限制。
- 论文未直接引用 **pixelSplat** 与 **LongVol**(正文与参考文献中均无对应条目,全文 grep 无匹配)——pixelSplat 是多视图 pixel-aligned feed-forward 方法,与本论文的关联仅体现在对 "pixel-aligned representation" 的批评语境中;LongVol 未出现【待核实:确认全文未提及】。
- 实验中 **LVSM**(Jin et al., 2024)与 **LagerNVS**(Szymanowicz et al., 2026)被用作 single-view image-to-image NVS baseline(§4.1),即"直接合成图像或依赖迭代生成"的方法,不产生紧凑、显式、可实时渲染的场景表示。
- **§2.2 Implicit Neural Representations**:定位继承 LIIF(Chen et al., 2021,图像隐式连续函数)与 InfiniDepth(Yu et al., 2026,隐式深度场)的隐式解码思想,但把输出从单通道图像/深度变为"摆放、形状、不透明度、外观需联合构成连贯表面布局"的 3D 高斯集合。
- 同节把 **C3G**(An et al., 2025)与 **TokenGS**(Ren et al., 2026)归为 query-based Gaussian decoding:它们在**多视图**设定下用 learnable query tokens 聚合多视图特征;InfiniSplat 认为单图设定中这类自由学习的 query token 缺乏几何锚点,因此改用来自单目几何先验的 **geometry-guided support queries**,保留 query 解码的灵活性同时显式锚定表面结构。

## 9. 版本与提交历史(abs 页 submission history)

- 提交者:Jiawei Wang。
- **v1**:Mon, 3 Aug 2026 16:17:39 UTC(21,964 KB);dateline 注 "Submitted on 3 Aug 2026 (v1)"。abs 页该条目无文字备注。
- **v2**:Tue, 4 Aug 2026 03:15:02 UTC(21,964 KB);dateline 注 "last revised 4 Aug 2026 (this version, v2)"。abs 页该条目无文字备注(未给出修订说明)。
- abs 页元数据:citation_date 2026/08/03,citation_online_date 2026/08/04;当前 og:url 指向 v2。
- 本地存档的 full HTML 水印为 **arXiv:2608.02437v1 [cs.CV] 03 Aug 2026**,即正文提取自 **v1**(v2 的修订内容未包含在本存档中)。

## 10. 局限性章节(§5,Figure 11)

- 单视图歧义 + 深度先验不完美导致两类几何误差:
  1. 只有一张输入图,无法观测遮挡区域、也无法消歧可见像素背后的多种可能 3D 解释;暴露大片未见区域的目标视图(前景物体后或源视锥外)可能产生不完整几何、拉伸结构或幻觉外观。
  2. 几何引导采样依赖预测深度;当先验在**反射面、透明物体、细结构、无纹理区域或非常规场景**上失效时,supports 会被放在不准确的几何 scaffold 上。
- 除先验失效外,**极端视角外推**,以及单一 depth-induced support 分布难以覆盖的场景——**非朗伯表面、重复细结构、极薄几何、强深度不连续**——仍有挑战。
- Figure 11 失败案例展示三类:大 disocclusion、错误深度先验、极端外推。
- 未来方向:结合更强的生成先验、不确定性感知的几何估计,或稀疏多视图输入,同时保持 feed-forward 高斯预测的效率。

---

## 附:其余核对要点

- 结论(§6):在 ETH3D、ScanNet++、Tanks-and-Temples、DL3DV 的跨数据集评测中,RGB-only 与 LiDAR-conditioned 设定下均对 feed-forward baseline 取得 SOTA;定性上裂缝孔洞更少、法线更干净、大视角变化下表面更连贯。
- 评测 mask:对有参考深度的数据集,把源视图几何投影到目标视图得初始可见性图,经图像空间形态学操作生成完整 frustum-visible mask,所有方法共用同一 mask(§4.1)。
- 感知损失与 context/target 分工:感知损失只用于 target views;context view 主要用于稳定生成表示的约束(§3.4)。
- 全文待核实项汇总:decoder MLP 层数/隐藏维、DINO 特征具体维度、训练与推理输入分辨率、推理硬件、v2 相对 v1 的修改内容、共同一作的第二人。
