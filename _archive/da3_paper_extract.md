# Depth Anything 3 (DA3) 论文提取报告

- 论文:Depth Anything 3: Recovering the Visual Space from Any Views
- arXiv:2511.10647v1 [cs.CV],2025-11-13
- 来源文件:da3_full.html(全文 HTML)、da3_abs.html(abs 页)
- 说明:HTML 中 "0pt" 均为 LaTeXML 对 depth 宏的渲染残留,本报告一律还原为 depth;拿不准处标【待核实】;表格已做 \xa0 不换行空格归一化。

## 1. 作者列表与机构(abs 页 / 全文标题区)

作者(顺序):Haotong Lin、Sili Chen、Jun Hao Liew(abs 页写作 "Junhao Liew")、Donny Y. Chen、Zhenyu Li、Guang Shi、Jiashi Feng、Bingyi Kang。

- 机构:全体作者标注 **ByteDance Seed**(全文标题区仅出现 "]ByteDance Seed" 一个机构标注,作者名无机构区分上标)。
- 贡献标注:存在 "[†]Project Lead"(项目负责人)与 "[*]Equal Contribution"(共同一作)两种脚注,但 HTML 转换丢失了 †/* 与具体作者的对应关系【待核实】。
- 通讯:Bingyi Kang,项目页 depth-anything-3.github.io。
- abs 页 Comments:仅含项目页链接 "this https URL"(https://depth-anything-3.github.io/),无会议标注;无 "accepted by ..." 字样(项目页口径未知)【待核实】。
- 提交历史:v1,2025-11-13 18:59:53 UTC,21,837 KB,From: Haotong Lin。截至抓取时仅 v1 一个版本。

## 2. 核心思想

### 2.1 任务 formulation(§3.1)

输入 I = {I_i}_{i=1..Nv},每图 H×W×3;Nv=1 为单目,Nv>1 为视频/多视图。每图有深度 D_i、外参 [R_i|t_i]、内参 K_i;相机也可表示为 9 维向量 v_i = (t_i∈R^3, q_i∈R^4 旋转四元数, f_i∈R^2 FOV)。像素 p=(u,v,1) 投影到 3D 点:

  P = R_i ( D_i(u,v) K_i^{-1} p ) + t_i

### 2.2 Depth-ray 表示(§3.1 "Depth-ray representation")

- 每像素光线 r ∈ R^6,由原点 t∈R^3(即相机平移)与方向 d∈R^3 组成:r=(t,d)。方向由像素反投影到相机系再旋转到世界系:d = R K^{-1} p。
- 密集 ray map M ∈ R^{H×W×6}:前 3 通道存 per-pixel ray origin(M(:,:, :3)),后 3 通道存方向(M(:,:, 3:))。
- d 不做归一化,模长保留投影尺度,因此世界系 3D 点直接为:P = t + D(u,v)·d。点云可由 depth map 与 ray map 逐元素组合生成。
- 相机参数可从 ray map 恢复(pose-free 推理用,"Deriving Camera Parameters from the Ray Map"):
  1. 相机中心 t_c = 所有像素 ray origin 的均值(公式 1);
  2. 估计 R、K 被建模为求单应 H = K R:设标准相机 K_I = I,标准光线 d_I = p,则 d_cam = K R d_I,即两组光线间存在 H = K R 的单应关系;
  3. 通过最小化几何误差 ‖H p_{h,w} × M(h,w,3:)‖ 求解 H*(公式 2),‖H‖=1 约束,是标准最小二乘,用 DLT 算法高效求解;
  4. 对 H* 做 RQ 分解(K 上三角、R 正交)唯一恢复 K、R。

### 2.3 两个核心论断(§3.1 "Minimal prediction targets" 与摘要/§7.2)

1. **单个 plain transformer 足够**(如 vanilla DINO encoder),无需专门架构设计(§7.2.2 实证:VGGT 式双 transformer 设计仅达本方法 79.8% 性能)。
2. **depth-ray 单一预测目标足够**:depth + ray 是最小且充分的目标集,优于 point map(DUSt3R 式)或 pose+point map+depth 的冗余组合(VGGT/CUT3R/Fast3R 式)(§7.2.1 / Table 6)。
   - 附加说明:ray map 推相机在推理时计算昂贵,故加一个轻量 camera head D_C(transformer,只处理每视图 1 个 camera token,预测 f∈R^2、q∈R^4、t∈R^3),开销可忽略。最终采用 depth+ray+cam。

## 3. 架构(§3.2 + Figure 2)

三组件:单一 transformer backbone + 可选 camera encoder + Dual-DPT head。

### 3.1 Single transformer backbone

- 视觉 transformer,L 个 block,大规模单目图像语料预训练(如 DINOv2)。
- 不做架构修改,通过 input-adaptive self-attention 实现跨视图推理:靠重排输入 token 完成。
- 将 L 层分两组:L_s 层组内做 within-view(图内)self-attention;后续 L_g 层组在 cross-view 与 within-view attention 间交替,通过 tensor reordering 对所有 token 联合操作。
- 实践中 L_s : L_g = 2 : 1,L = L_s + L_g(Table 7 消融显示该比例最优)。
- input-adaptive 特性:单张输入时自然退化为单目深度估计,无额外开销。
- patch size:正文未显式给出;由 base resolution 504 可被 14 整除且 DINOv2 常规为 14x14 推测 patch size = 14【待核实】。

### 3.2 Camera condition injection(cam_enc)

- 每视图前置一个 camera token c_i;若已知相机参数 (K_i, R_i, t_i),token 由轻量 MLP E_c 编码:c_i = E_c(f_i, q_i, t_i)(输入为 FOV、四元数、平移);否则使用共享可学习 token c_l。
- camera token 与 patch token 拼接,参与所有 attention 操作,提供显式几何上下文或一致的学习占位符。

### 3.3 Dual-DPT head(Figure 3)

- 共享一组 reassembly 模块处理 backbone 特征,之后用**两组不同的 fusion 层**分别融合(depth 分支、ray 分支各一组),最后两个独立输出层分别产出 depth map 与 ray map。
- 即两分支共享 reassembly、仅最终 fusion 阶段不同,促进两任务交互且避免冗余中间表示。
- 输出通道数:depth 分支 1 通道、ray 分支 6 通道(由 formulation 推得,正文未逐一写明通道数)【待核实,但与 §3.1 的 D∈R^{H×W}、M∈R^{H×W×6} 一致】。

## 4. 训练(§3.3、§3.4、§4)

### 4.1 训练目标(§3.3)

- 模型 F_θ: I 映射到 {D̂, R̂, ĉ}(ĉ 为可选输出,原文灰色标注)。
- 损失计算前,所有 GT 信号用一个公共尺度因子归一化:尺度 = 有效重投影 point map P 的均值 ℓ2 范数。
- 总损失(正文公式):
  L = L_D(D̂, D) + L_M(R̂, M) + L_P(D̂⊙d + t, P) + β L_C(ĉ, v) + α L_grad(D̂, D)
- L_D 为带置信度的尺度不变形式:L_D(D̂,D;D_c) = (1/Z_Ω) Σ_{p∈Ω} m_p ( D_{c,p} |D̂_p − D_p| − λ_c log D_{c,p} ),其中 D_{c,p} 为深度 D_p 的置信度。
- 所有损失项基于 ℓ1 范数;权重 α = 1、β = 1。
- L_grad(公式 3):L_grad = ‖∇_x D̂ − ∇_x D‖_1 + ‖∇_y D̂ − ∇_y D‖_1(水平/垂直有限差分),保持锐利边缘、平面平滑。
- 注:任务消息中的 "Lp/Lc/Ld" 记号与原文不完全一致,原文目标项为 L_D(深度)、L_M(ray map)、L_P(point map 重投影一致性)、L_C(相机)、L_grad(梯度),权重仅 α、β 显式给出【其余项权重默认为 1,待核实】。

### 4.2 Teacher-student 范式(§3.3 + §4)

- 动机:真实数据深度噪声大、不完整(Fig. 4),故仅用合成数据训练单目相对深度 teacher(Depth-Anything-3-Teacher),生成高质量伪深度;伪深度经 RANSAC 最小二乘与原始稀疏/噪声 GT 对齐(scale+shift),提升细节与完整度且保持几何精度。
- §4.1 Teacher 构建:基于 DA2 扩展,backbone 与 DA3 框架对齐(纯 DINOv2 ViT + DPT decoder,无专门修改)。
  - 数据扩展:仅合成数据,共 20 个数据集——Hypersim、TartanAir、IRS、vKITTI2、BlendedMVS、SPRING、MVSSynth、UnrealStereo4K、GTA-SfM、TauAgent、KenBurns、MatrixCity、EDEN、ReplicaGSO、UrbanSyn、PointOdyssey、Structured3D、Objaverse、Trellis、OmniObject。
  - 表示:与 DA2 的 scale-shift-invariant disparity 不同,teacher 输出 scale-shift-invariant **depth**;为补偿 depth 在近处敏感度低,预测 exponential depth。
  - 损失(公式 4-7):标准深度梯度损失 + ROE 对齐的 global-local 损失(wang2025moge)+ 距离加权表面法线损失(中心像素采样 4 邻域,权重 w_i = Σ_{j=0..4}‖n_j‖ − ‖n_i‖,加权平均法线 n_m = Σ w_i n_i/‖n_i‖,最终 L_N = E(n̂_m, n_m) + Σ E(n̂_i, n_i)),另联合预测 sky mask 与 object mask(MSE 监督)。总损失 L_T = α L_grad + L_gl + L_N + L_sky + L_obj,α = 0.5。
- §4.2 教 DA3:teacher 相对深度 D̃ 与可用稀疏深度 D(COLMAP 或主动传感器)通过鲁棒 RANSAC scale-shift 对齐(公式 8):(ŝ, t̂) = argmin Σ m_p (s D̃_p + t − D_p)^2,内点阈值为残差中位数的平均绝对偏差;对齐后 D^{T→M} = ŝ D̃ + t̂ 作为尺度一致、pose-depth 一致的监督。
- §4.3 教单目学生:沿用 DA2 框架,无标注图像 + teacher 伪标签训练;关键区别:学生预测 depth(DA2 预测 disparity);用与 teacher 相同的损失监督伪深度标签;仅相对深度。
- §4.4 教 metric 模型:沿用 Metric3Dv2 的 canonical camera space 变换,按 f^c/f 缩放 GT 深度消除焦距歧义;teacher 预测与 GT metric 深度对齐 scale/shift 后作为监督。14 个训练数据集:Taskonomy、DIML(Outdoor)、DDAD、Argoverse、Lyft、PandaSet、Waymo、ScanNet++、ARKitScenes、Map-free、DSEC、Driving Stereo、Cityscapes(stereo 数据集用 FoundationStereo 预测作标签)。
  - metric 模型实现细节:base resolution 504、多种长宽比(1:1, 1:2, 16:9, 9:16, 3:4, 1:1.5, 1.5:1, 1:1.8);AdamW,encoder lr 5e-6、decoder lr 5e-5;5% 概率随机旋转 90/270 度;canonical focal f^c = 300;20% 概率用原始 GT 标签;batch 64,160K 迭代;损失 = w_d L_depth + L_grad + L_sky。

### 4.3 训练数据组成(Table 1,§3.4)

评测集(pose-geometry benchmark):

| Dataset | #Scenes | Data Type |
|---|---|---|
| HiRoom (ours) | 29 | Synthetic |
| ETH3D | 11 | LiDAR |
| DTU | 22 | LiDAR |
| 7Scenes | 7 | LiDAR |
| ScanNet++ | 20 | LiDAR |

(§6.3 称 HiRoom 共 30 个 Blender 渲染室内场景、benchmark 选 29;正文另有 "5 datasets totaling over 89 scenes":29+11+22+7+20=89。)

训练集(pose-geometry training):

| Dataset | #Scenes | Data Type |
|---|---|---|
| AriaDigitalTwin | 237 | Synthetic |
| AriaSyntheticENV | 99950 | Synthetic |
| ArkitScenes | 4388 | LiDAR |
| BlendedMVS | 503 | 3D Recon |
| Co3dv2 | 30616 | Colmap |
| DL3DV | 6379 | Colmap |
| HyperSim | 344 | Synthetic |
| MapFree | 921 | Colmap |
| MegaDepth | 268 | Colmap |
| MegaSynth | 6049 | Synthetic |
| MvsSynth | 121 | Synthetic |
| Objaverse | 505557 | Synthetic |
| Omniobject | 5885 | Synthetic |
| OmniWorld | 1039 | Synthetic |
| PointOdyssey | 44 | Synthetic |
| ReplicaVMAP | 17 | Synthetic |
| ScanNet++ | 230 | LiDAR |
| ScenenetRGBD | 16866 | Synthetic |
| TartanAir | 355 | Synthetic |
| Trellis | 557408 | Synthetic |
| vKitti2 | 50 | Synthetic |
| WildRGBD | 23050 | LiDAR |

注意:ScanNet++ 训练/测试在场景级严格互斥;作者指出 ScanNet++ 用于训练对其它方法也是公平的(VGGT、DUSt3R 也用它训练)。

### 4.4 训练细节(§3.4)

- 128 张 H100 训练 200k 步;8k 步 warm-up;peak lr = 2×10^{-4}。
- base resolution 504×504(可被 2, 3, 4, 6, 9, 14 整除,兼容 2:3、3:4、9:16 等照片长宽比)。
- 训练分辨率从 {504×504, 504×378, 504×336, 504×280, 336×504, 896×504, 756×504, 672×504} 随机采样。
- 504×504 分辨率下视图数从 [2, 18] 均匀采样;batch size 动态调整使每步 token 数近似恒定。
- 120k 步时监督从 GT 深度切换为 teacher 标签。
- pose conditioning 训练时以 0.2 概率随机激活。
- 主模型 optimizer 未显式写明(metric 模型用 AdamW)【待核实】。
- 消融设定(§7.2 开头):DA3-Giant 全量训练需 128×H100 约 10 天;所有消融用 ViT-L backbone、最多 10 视图,32×H100 约 4 天。

## 5. 实验主表数字

### 5.1 Table 2:Pose accuracy(Auc3 ↑ / Auc30 ↑;Params 列)

| Methods | Params | HiRoom A3/A30 | ETH3D A3/A30 | DTU A3/A30 | 7Scenes A3/A30 | ScanNet++ A3/A30 |
|---|---|---|---|---|---|---|
| DUSt3R | 0.57B | 17.6 / 54.3 | 4.30 / 27.3 | 4.00 / 74.3 | 6.90 / 61.6 | 8.10 / 33.9 |
| Fast3R | 0.65B | 25.9 / 77.0 | 8.10 / 44.4 | 9.50 / 79.1 | 19.0 / 78.6 | 17.9 / 72.5 |
| MapAnything | 0.56B | 17.9 / 82.8 | 19.2 / 77.4 | 6.50 / 72.7 | 12.6 / 79.7 | 20.2 / 84.1 |
| Pi3 | 0.96B | 67.0 / 94.8 | 35.2 / 87.3 | 62.5 / 94.9 | 25.5 / 86.3 | 50.7 / 92.1 |
| VGGT | 1.19B | 49.1 / 88.0 | 26.3 / 80.8 | 79.2 / 99.8 | 23.9 / 85.0 | 62.6 / 95.1 |
| DA3-Giant | 1.10B | 80.3 / 95.9 | 48.4 / 91.2 | 94.1 / 99.4 | 28.5 / 86.8 | 85.0 / 98.1 |
| DA3-Large | 0.36B | 58.7 / 94.2 | 32.2 / 86.9 | 70.2 / 96.7 | 29.2 / 86.6 | 60.2 / 94.7 |
| DA3-Base | 0.11B | 19.0 / 83.2 | 15.1 / 74.6 | 60.1 / 95.9 | 20.1 / 82.9 | 25.1 / 83.4 |
| DA3-Small | 0.03B | 9.49 / 75.2 | 8.59 / 62.1 | 30.6 / 91.2 | 14.0 / 78.7 | 10.9 / 71.9 |

正文要点:DA3-Giant 几乎所有指标最佳,唯一例外是 DTU 的 Auc30(VGGT 99.8 > DA3-Giant 99.4);Auc3 上至少比所有对手高 8% 相对提升;ScanNet++ Auc3 比第二名(VGGT 62.6)相对提升正文称 33%。

### 5.2 Table 3:Reconstruction accuracy(除 DTU 外报 F1 ↑;DTU 报 CD ↓ mm;w/o p. / w/ p. = 是否提供 GT pose)

| Methods | Params | HiRoom w/o/w | ETH3D w/o/w | DTU w/o/w | 7Scenes w/o/w | ScanNet++ w/o/w |
|---|---|---|---|---|---|---|
| DUSt3R | 0.57B | 30.1 / 39.5 | 19.7 / 18.8 | 7.60 / 7.97 | 26.6 / 39.8 | 18.9 / 27.3 |
| Fast3R | 0.65B | 40.7 / 48.2 | 38.5 / 50.3 | 6.88 / 8.20 | 41.0 / 49.8 | 37.1 / 53.7 |
| MapAnything | 0.56B | 32.4 / 69.2 | 54.8 / 71.9 | 7.91 / 3.97 | 44.8 / 55.2 | 39.4 / 71.3 |
| Pi3 | 0.96B | 75.8 / 85.0 | 72.7 / 80.6 | 3.28 / 1.72 | 44.2 / 57.5 | 63.1 / 73.3 |
| VGGT | 1.19B | 56.7 / 70.2 | 57.2 / 66.7 | 2.05 / 1.44 | 47.9 / 51.4 | 66.4 / 70.7 |
| DA3-Giant | 1.10B | 85.1 / 95.6 | 79.0 / 87.1 | 1.85 / 1.85 | 53.5 / 56.5 | 77.0 / 79.3 |
| DA3-Large | 0.36B | 69.5 / 87.1 | 65.8 / 75.2 | 2.08 / 1.23 | 56.3 / 49.2 | 67.9 / 75.7 |
| DA3-Base | 0.11B | 25.9 / 71.4 | 49.5 / 66.7 | 2.87 / 2.36 | 49.9 / 50.6 | 47.2 / 67.8 |
| DA3-Small | 0.03B | 18.3 / 52.2 | 41.6 / 63.4 | 5.83 / 2.49 | 41.0 / 46.8 | 32.3 / 53.8 |

正文要点:DA3-Giant 在全部 5 个 pose-free 设定 SOTA;平均相对提升:超 VGGT 25.1%、超 Pi3 21.5%(几何精度)。注意 §7.1 正文称 "DA3-Large (0.30B parameters)",与 Table 2/3 的 0.36B 不一致【待核实;Table 8 中 DA3-Large backbone 为 0.300B】。有 pose 时多数数据集仍有增益,7Scenes 除外(视频设定已饱和);pose-conditioned 下模型尺寸带来的增益小于 pose-free,说明 pose 估计比深度估计更需要大模型。

### 5.3 Table 4:Monocular depth(δ1 ↑;数据集 KITTI/NYU/SINTEL/ETH3D/DIODE + Rank)

| Method | KITTI | NYU | SINTEL | ETH3D | DIODE | Rank |
|---|---|---|---|---|---|---|
| DA2 | 94.6 | 97.9 | 77.2 | 86.5 | 95.2 | 2.60 |
| VGGT | 91.7 | 97.9 | 67.9 | 97.5 | 95.3 | 3.75 |
| DA3 | 95.3 | 97.4 | 75.5 | 98.6 | 95.4 | 2.20 |
| Teacher | 97.2 | 97.9 | 81.4 | 99.8 | 96.6 | 1.00 |

### 5.4 Table 5:NVS 结果(12 输入 context views;目标视图每 8 帧采样、>300 视图;分辨率 270×480;PSNR ↑ / SSIM ↑ / LPIPS ↓)

| Methods | DL3DV (140) | Tanks&Temples (6) | MegaDepth (19) |
|---|---|---|---|
| pixelSplat | 16.55 / 0.456 / 0.480 | 13.81 / 0.347 / 0.558 | 13.87 / 0.367 / 0.561 |
| MVSplat | 18.13 / 0.559 / 0.393 | 14.81 / 0.391 / 0.508 | 14.67 / 0.398 / 0.533 |
| DepthSplat | 19.24 / 0.620 / 0.322 | 15.80 / 0.474 / 0.418 | 15.90 / 0.471 / 0.450 |
| Fast3R(换 backbone) | 19.30 / 0.604 / 0.320 | 16.24 / 0.478 / 0.409 | 16.43 / 0.493 / 0.421 |
| MV-DUSt3R(换 backbone) | 20.01 / 0.645 / 0.294 | 17.04 / 0.529 / 0.370 | 16.20 / 0.484 / 0.437 |
| VGGT(换 backbone) | 20.96 / 0.697 / 0.253 | 17.18 / 0.550 / 0.347 | 16.45 / 0.500 / 0.417 |
| DAv3 (Ours)(原文行名如此) | 21.33 / 0.711 / 0.241 | 18.10 / 0.578 / 0.311 | 17.89 / 0.561 / 0.351 |

注:Table 5 为 pose-conditioned(§5.1)设定;baseline 为 3 个专用 FF-3DGS 模型(pixelSplat、MVSplat、DepthSplat)与 3 个替换 geometry backbone 的版本(Fast3R、MV-DUSt3R、VGGT);全部在 DL3DV-10K 上按统一协议重训(§7.5:8×A100、200K 步、batch 1;pixelSplat 因 epipolar attention 慢只训 100K 步;输出 270×480)。pose-adaptive 版本(§5.2)面向 in-the-wild,正文未给单独数值表【待核实】。

### 5.5 Table 8:参数量与速度(A100 80GB;Max #images 为单卡最多处理图像数;速度为 32 图场景平均每图 FPS;分辨率 504×336;参数列分 Backbone/DualDPT/CameraHead)

| Model | Max #Images | Backbone | DualDPT | CameraHead | Speed |
|---|---|---|---|---|---|
| VGGT (Reference) | 400-500 | 0.91B | 0.064B | 0.22B | 34.1 FPS |
| DA3-Giant | 900-1000 | 1.130B | 0.050B | 0.018B | 37.6 FPS |
| DA3-Large | 1500-1600 | 0.300B | 0.047B | 0.008B | 78.37 FPS |
| DA3-Base | 2100-2200 | 0.086B | 0.015B | 0.004B | 126.5 FPS |
| DA3-Small | 4000-4100 | 0.022B | 0.003B | 0.001B | 160.5 FPS |

注:Table 8 的 Backbone 参数量与 Table 2/3 的 Params 列略有出入(Giant 1.130B vs 1.10B;Large 0.300B vs 0.36B;Base 0.086B vs 0.11B;Small 0.022B vs 0.03B)【待核实】;文中称 intermediate tokens 存 CPU 内存可处理更多图像。

### 5.6 附:Table 10 单目学生(δ1 ↑,ViT-L backbone;§7.3.2)

| Method | KITTI | NYU | SINTEL | ETH3D | DIODE |
|---|---|---|---|---|---|
| DA2 | 94.6 | 97.9 | 77.2 | 86.5 | 95.2 |
| mono-student | 97.1 | 98.0 | 82.3 | 98.8 | 96.5 |

正文:mono-student 全面超 DA2;ETH3D 提升超 10%;SINTEL +5.1%。

### 5.7 附:Table 11 metric depth(δ1 ↑ / AbsRel ↓;§7.4)

| Methods | NYUv2 | KITTI | ETH3D | SUN-RGBD | DIODE |
|---|---|---|---|---|---|
| DepthPro | 0.932 / 0.093 | 0.843 / 0.121 | 0.386 / 0.349 | 0.950 / 0.126 | 0.734 / 0.173 |
| Metric3D v2 | 0.971 / 0.067 | 0.976 / 0.051 | 0.830 / 0.138 | 0.954 / 0.132 | 0.018 / 0.154 |
| UniDepthv1 | 0.980 / 0.061 | 0.978 / 0.051 | 0.234 / 0.464 | 0.971 / 0.113 | 0.570 / 0.266 |
| UniDepthv2 | 0.968 / 0.064 | 0.968 / 0.076 | 0.863 / 0.152 | 0.977 / 0.111 | 0.856 / 0.123 |
| DA3-metric | 0.963 / 0.070 | 0.953 / 0.086 | 0.917 / 0.104 | 0.973 / 0.105 | 0.838 / 0.128 |
| w/ teacher(消融) | 0.966 / 0.073 | 0.947 / 0.086 | 0.906 / 0.105 | 0.973 / 0.104 | 0.824 / 0.132 |
| w/o teacher(消融) | 0.969 / 0.066 | 0.965 / 0.067 | 0.907 / 0.105 | 0.975 / 0.099 | 0.816 / 0.134 |

注:Metric3D v2 的 DIODE δ1=0.018 为原文如此【疑似笔误,待核实】;DA3-metric 在 ETH3D(δ1=0.917, 远超 UniDepthv2 的 0.863)与 SUN-RGBD AbsRel(0.105)最佳,DIODE 第二;去 teacher 监督在 NYU/KITTI 略升,但 Fig. 10 显示 teacher 监督显著提升锐利度。

## 6. 消融(§7.2 及 §7.3.1)

### 6.1 Table 6:预测目标组合(§7.2.1;ViT-L、视图数 10、batch 128、120k 步;无 camera condition token;列:Auc3 ↑ / F1 ↑,DTU 为 Auc3 / CD ↓)

| Methods | HiRoom | ETH3D | DTU | 7Scenes | ScanNet++ |
|---|---|---|---|---|---|
| depth + pcd + cam | 9.1 / 12.8 | 19.0 / 60.4 | 42.3 / 4.918 | 20.8 / 43.4 | 22.0 / 43.0 |
| depth + cam | 10.8 / 16.5 | 9.9 / 48.0 | 23.3 / 5.316 | 13.0 / 38.5 | 13.3 / 41.0 |
| depth + ray | 48.7 / 60.3 | 25.5 / 65.4 | 46.5 / 3.919 | 24.0 / 46.5 | 35.5 / 53.4 |
| depth + ray + cam | 37.2 / 45.4 | 22.3 / 59.4 | 56.3 / 3.066 | 25.7 / 45.6 | 34.1 / 56.5 |

要点:最小 depth+ray 配置在所有数据集与指标上稳定优于 depth+pcd+cam 与 depth+cam;depth+ray 相对 depth+cam 在 Auc3 上近乎翻倍(HiRoom 48.7 vs 10.8);加辅助 cam head 无进一步增益,但因开销可忽略(约为主 backbone 计算量的 0.1%)最终采用 depth+ray+cam。
注:HTML 中表头渲染为 "0pt"、"pcd"、"cam"、"ray",其中 0pt 即 depth【原文如此】。

### 6.2 Table 7:架构设计消融(§7.2.2 / §7.2.3;列同 Table 6;带 * 行为 GT pose fusion 评测)

| Methods | HiRoom | ETH3D | DTU | 7Scenes | ScanNet++ |
|---|---|---|---|---|---|
| a. Proposed Arch. | 39.2 / 47.0 | 21.0 / 55.4 | 45.8 / 3.82 | 26.2 / 47.6 | 30.3 / 51.1 |
| b. VGGT Style | 3.72 / 14.5 | 2.31 / 27.4 | 1.38 / 6.93 | 0.97 / 21.4 | 2.03 / 12.2 |
| c. Full Alt. | 24.7 / 29.3 | 13.1 / 51.9 | 44.6 / 4.23 | 21.1 / 48.6 | 27.7 / 47.5 |
| d. w/o Dual DPT | 5.59 / 11.5 | 13.6 / 33.4 | 21.7 / 5.14 | 14.2 / 49.4 | 26.5 / 46.6 |
| e. w/o Teacher | 11.2 / 16.0 | 16.2 / 57.6 | 52.5 / 3.29 | 23.3 / 40.3 | 26.2 / 47.7 |
| f. w/o Pose Cond.* | (F1/CD) 65.8 | 63.2 | 3.65 | 58.4 | 62.8 |
| g. w/ Pose Cond.* | 73.8 | 70.9 | 2.14 | 46.0 | 65.7 |

要点:
- b(VGGT 式双 transformer,三块数,为公平用更小 ViT-B 使参数与 ViT-L 相近)仅达 baseline 79.8% 性能——归因于本方法 backbone 全量预训练 vs VGGT 三分之二 block 未预训练。
- c Full Alt.(所有层交替 cross/within view,L = L_g)几乎所有指标下降(例外:7Scenes F1 48.6 略高于 a 的 47.6),证明 partial alternation 更优。
- d 去掉 Dual-DPT(两个独立 DPT head)各项指标一致下降。
- e 去掉 teacher 标签:DTU 略升(52.5 / 3.29),但 7Scenes、ScanNet++ 下降,HiRoom 下降显著(39.2→11.2);作者归因 HiRoom 为合成数据、GT 细节丰富,teacher 监督帮助学生捕捉细节;Fig. 8 定性证实。
- f/g pose conditioning 消融(用 GT pose fusion 评测):有 pose cond 在 HiRoom(73.8 vs 65.8)、ETH3D(70.9 vs 63.2)、DTU(2.14 vs 3.65)、ScanNet++(65.7 vs 62.8)全面更好,但 7Scenes 反而更差(46.0 vs 58.4)【原文数字如此;正文声称各配置均一致优于,与 7Scenes 数字矛盾,待核实】。

### 6.3 Table 9:Teacher 消融(§7.3.1;KITTI/NYU/ETH3D/SUN-RGBD/DIODE 平均;AbsRel ↓ / SqRel ↓ / δ1 ↑;ViT-L、batch 64)

三组消融(Data / Geometry / Loss):

| 组 | 变体 | δ1 | AbsRel | SqRel |
|---|---|---|---|---|
| Data | V2 | 0.919 | 0.087 | 0.596 |
| Data | V3 | 0.929 | 0.079 | 0.508 |
| Data | V3 + mr.(多分辨率) | 0.938 | 0.072 | 0.452 |
| Geometry | Disparity | 0.919 | 0.095 | 1.033 |
| Geometry | Pointmap | 0.912 | 0.096 | 0.693 |
| Geometry | Depth | 0.918 | 0.089 | 0.637 |
| Loss | MAE-Loss | 0.918 | 0.089 | 0.637 |
| Loss | w/o Dist. Nor.(无距离加权法线) | 0.918 | 0.087 | 0.600 |
| Loss | Full loss | 0.919 | 0.087 | 0.596 |

要点:V3 数据 + 多分辨率策略最佳;depth 几何表示 AbsRel/SqRel 最优;full teacher loss 最优。

### 6.4 Figure 8:标签监督对比

定性图:teacher 标签监督的深度图细节更丰富、结构更精细(与 Table 7-e 定量呼应)。

## 7. 应用章节(§5):Feed-Forward 3DGS

### 7.1 Pose-Conditioned FF-3DGS(§5.1)

- 微调:在 DA3 backbone 上增加一个 DPT head(GS-DPT)推断像素对齐 3D Gaussians。
- GS-DPT 输出:每像素 camera 空间 3DGS 参数 {σ_i, q_i, s_i, c_i}(不透明度、旋转四元数、缩放、RGB);σ 由 confidence head 预测,其余由 GS-DPT 主头预测;估计深度 unproject 到世界坐标得全局位置 P_i,再按给定相机 pose 光栅化渲染。
- 训练目标:渲染新视图的 photometric 损失(L_MSE + L_LPIPS)+ 观察视图估计深度的 scale-shift-invariant L_D,沿用 teacher-student 范式。

### 7.2 Pose-Adaptive FF-3DGS(§5.2)

- 面向 in-the-wild:与 DA3 使用相同预训练权重,支持有无 pose、可变分辨率、可变输入视图数。
- 两个设计:1) 所有 3DGS 参数在局部 camera 空间预测;2) backbone 无缝处理 posed/unposed 输入(DA3 天然满足)。有 pose 时用 umeyama2002least 做尺度对齐并将预测深度与 camera-space 3DGS unproject 到世界空间;无 pose 时直接用预测 pose。
- 为缓解表面几何精度与渲染质量的权衡,GS-DPT 额外预测一个 depth offset;颜色改为球谐系数(view-dependent),减少与几何冲突。
- 增强训练策略:从预训练 DA3 权重初始化并**冻结 backbone**,只训 GS-DPT head;用可变分辨率与可变 context 视图数训练(高分辨率配少视图、低分辨率配多视图),稳定训练并支持多样评测。

### 7.3 实现细节(§5.3)

- NVS 训练数据:DL3DV 的 10,015 个场景(COLMAP 位姿);评测用 140 个 DL3DV 场景与训练集完全不相交。
- (§7.5 补充)所有对比 FF-3DGS 模型按统一协议重训:12 个 FPS 选取的输入 context views;flash attention、FSDP;所有 baseline 加深度损失;8×A100、200K 步、batch 1(pixelSplat 100K);输出 270×480。

## 8. 评测基准(§6 Visual Geometry Benchmark)

### 8.1 评测管线(§6.1)

- Pose estimation:每场景取全部图像,超限时固定随机种子抽 100 张;前馈模型出 pose+depth 后计算 pose 精度。
- Geometry estimation:同一图集,用预测 pose+depth 重建;用 evo 将预测 pose 对齐到 GT pose 得变换;RANSAC 对齐:随机采 pose 子集重复 evo,以内点数(平移误差低于整体偏差中位数)最多者为准;对齐后点云经 TSDF 融合与 GT 点云比较。
- Visual rendering:每场景约 300-400 图;每 8 张抽 1 张作为新视图目标;其余视图用数据集 COLMAP pose,经考虑平移与旋转距离的 farthest point sampling 选 12 张为输入 context views。DL3DV 用官方 Benchmark 集;Tanks and Temples 用全部 Training Data 场景(除 Courthouse);MegaDepth 选 5000-5018 号场景。

### 8.2 指标(§6.2)

- Pose 指标:沿用 VGGT/PoseDiffusion 协议报 AUC;由 RRA(相对旋转精度)与 RTA(相对平移精度)组成;曲线由 min(RRA, RTA) 在各阈值决定,AUC 为该 accuracy-threshold 曲线积分;主要报阈值 3 与 30(Auc3、Auc30)。
- Reconstruction 指标:accuracy = dist(R→G)、completeness = dist(G→R)(DTU 惯例),CD = 两者均值;precision = |R| 中 dist<d 占比,recall 同;F1 = 2PR/(P+R)。DTU 报 CD(mm),其余报 F1。
- 渲染:PSNR / SSIM / LPIPS。

### 8.3 数据集(§6.3)

5 个数据集、共 89 个场景(HiRoom 29 + ETH3D 11 + DTU 22 + 7Scenes 7 + ScanNet++ 20):

- HiRoom:Blender 渲染合成数据集,30 个室内 living 场景(选 29);F1 阈值 d = 0.05m;TSDF voxel 0.007m。
- ETH3D:室内外高分辨率 + 激光 GT 深度;选 11 场景(courtyard, electro, kicker, pipes, relief, delivery area, facade, office, playground, relief 2, terrains);全部帧评测;d = 0.25;voxel 0.039m。
- DTU:124 物体、每场景 49 视图;评测 22 个 scan(依 MVSNet);RMBG 2.0(BiRefNet)去背景;深度融合沿用 GeoMVSNet 默认策略;全部帧评测。
- 7Scenes:真实室内低分辨率、严重运动模糊;依 NICER-SLAM 融合 RGBD 备 GT;每场景帧数降采样 11 倍;d = 0.05m;voxel 0.007m。
- ScanNet++:高分辨率图像 + iPhone LiDAR 深度 + 激光扫描重建采样深度;选 20 场景;GT 深度默认用激光扫描采样深度(iPhone LiDAR 无有效指示);帧降采样 5 倍;d = 0.05m;voxel 0.02m。
- NVS benchmark:DL3DV 140 场景 + Tanks and Temples 6 场景 + MegaDepth 19 场景,各约 300 采样帧,GT pose 为 COLMAP。

## 9. 局限与讨论(§8)

- §8 为结论与讨论,未单列"局限"小节;明确提到的局限/未来方向:
  1. 未来工作:扩展到动态场景(dynamic scenes)、整合语言与交互线索、更大规模预训练,打通几何理解与可行动 world model 的闭环。
  2. 7Scenes 上 pose conditioning 增益消失/反降(Table 7-g 46.0 vs f 58.4;Table 3 中 DA3-Giant w/ p. 56.5 仅略升),作者解释为该数据集视频设定性能已饱和。
  3. Teacher 监督的 trade-off:metric 模型上去掉 teacher 在 NYUv2/KITTI 指标略升,但牺牲锐利度与细节(Fig. 10)。
  4. 摘要与正文数字口径不一致:摘要称相对 VGGT "平均 44.3%(pose)与 25.1%(geometry)"(abs 页),而全文 HTML 摘要写 "35.7% 与 23.6%";正文 §7.1 为 25.1%/21.5%(geometry)【版本间口径不一致,待核实】。

## 10. 版本历史(abs 页)

- 仅一个版本:[v1] Thu, 13 Nov 2025 18:59:53 UTC(21,837 KB),From: Haotong Lin。
- DOI:https://doi.org/10.48550/arXiv.2511.10647。
