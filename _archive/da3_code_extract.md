# Depth Anything 3 (DA3) 源码审计报告

> 审计对象: `C:/code/media_paper/_archive/da3_src_extract/Depth-Anything-3-main/`
> 所有路径引用均相对 `src/depth_anything_3/`(流式部分相对仓库根 `da3_streaming/`)。

---

## 1. 模型结构

### 1.1 顶层组装:DepthAnything3Net

`model/da3.py:40` 定义 `DepthAnything3Net`,由 4 个可插拔子模块组成(`__init__` 见 `model/da3.py:66-98`):

- `net`: DinoV2 backbone
- `head`: DPT / DualDPT 深度头
- `cam_enc` + `cam_dec`: 可选相机编码器/解码器(仅 any-view 系列)
- `gs_head` + `gs_adapter`: 可选 3DGS 头(仅 da3-giant 配置包含,`configs/da3-giant.yaml`)

`PATCH_SIZE = 14` 硬编码于 `model/da3.py:64`。forward 流程(`model/da3.py:100-153`):

1. 若给定外参/内参 → `cam_enc` 生成 cam token(fp32,`model/da3.py:127-128`)
2. backbone 提特征 `feats, aux_feats = self.backbone(x, cam_token=..., ref_view_strategy=...)`(`model/da3.py:132-134`)
3. depth head 全程 fp32(`model/da3.py:139` `torch.autocast(enabled=False)`)
4. 二选一的位姿来源:`use_ray_pose=True` 走 ray map 解码(`_process_ray_pose_estimation`,`model/da3.py:181-203`),否则走 cam_dec(`_process_camera_estimation`,`model/da3.py:211-228`)
5. 可选 GS 头(`model/da3.py:230-284`),以及天空区域深度后处理(`model/da3.py:155-179`)

### 1.2 DINOv2 变体接入与 cross-view attention

`model/dinov2/dinov2.py:22-64` 是薄封装: `encoder_map` 把 `vits/vitb/vitl/vitg` 映射到 `vision_transformer.py` 中的 `vit_small/base/large/giant2`;固定 `img_size=518, patch_size=14`;`vitg` 使用 `swiglufused` FFN,其余用 MLP(`model/dinov2/dinov2.py:48`)。forward 直接调用 `get_intermediate_layers(x, out_layers, **kwargs)`,把 `cam_token`、`ref_view_strategy` 透传进 backbone。

核心改造在 `model/dinov2/vision_transformer.py:300-349`(`_get_intermediate_layers_not_chunked`):

- **local/global 交替注意力**(即论文的 cross-view attention):层索引 `i >= alt_start` 且 `i % 2 == 1` 时走 `"global"`,否则 `"local"`(`model/dinov2/vision_transformer.py:333-339`)。实现方式是 `process_attention`(`model/dinov2/vision_transformer.py:351-370`):
  - local: `rearrange(x, 'b s n c -> (b s) n c')` —— 每个视图独立自注意力
  - global: `rearrange(x, 'b s n c -> b (s n) c')` —— **把所有视图的 token 拼成一条长序列做标准 full attention,无 attention mask**(`attn_mask` 参数存在但默认 None)
  - 因此 cross-view 层是 `alt_start+1, alt_start+3, ...` 这些奇数层。small/base(12 层, alt_start=4)→ 第 5,7,9,11 层;large(24 层, alt_start=8)→ 9,11,...,23;giant(40 层, alt_start=13)→ 14,16,...,39
- **camera token 注入**:`alt_start != -1` 时创建可学习参数 `camera_token (1, 2, E)`(`model/dinov2/vision_transformer.py:163`);在第 `alt_start` 层把每个视图 token 序列的 0 号位(原 cls 位置)整段替换为 cam token —— 若用户提供了位姿,用 `cam_enc` 的输出,否则用可学习的 ref/src 两个 token(`model/dinov2/vision_transformer.py:323-331`)
- **参考视图选择与重排**:在第 `alt_start-1` 层、且视图数 `S >= THRESH_FOR_REF_SELECTION(=3, utils/constants.py:16)`、且无外部 cam token 时,基于 cls token 特征选出参考视图并移到第 0 位,同时 local 流也重排(`model/dinov2/vision_transformer.py:314-321`);输出时再 `restore_original_order` 还原(`model/dinov2/vision_transformer.py:344-345`)
- **cat_token(双流拼接)**:`cat_token=True` 时,输出层特征 = `torch.cat([local_x, x], dim=-1)`(`model/dinov2/vision_transformer.py:342`),即 local 与 global 双流在通道维拼接,使 head 的 `dim_in = 2 × embed_dim`(这解释了配置里 head dim_in 768/1536/2048/3072 恰好是 embed 的两倍)
- **RoPE 双坐标**:`_prepare_rope` 生成两套坐标 —— `pos`(各视图真实 patch 坐标)与 `pos_nodiff`(全视图共享同一坐标,`model/dinov2/vision_transformer.py:282-298`);global 层用 `pos_nodiff`,local 层用 `pos`(`model/dinov2/vision_transformer.py:308-312`)。即跨视图 attention 不携带视图内位置差异的区分信息【论文对此未明示,属源码细节】

`layers/attention.py` 相对官方 DINOv2 的改动:支持 `qk_norm`(LayerNorm per-head,`layers/attention.py:41-42`)、`rope`、`attn_mask`;默认 `fused_attn=True` 统一走 `F.scaled_dot_product_attention`(`layers/attention.py:56-69`);`MemEffAttention`(xformers)实现已删除。`layers/block.py:29-86` 加了 `qk_norm/rope/ln_eps` 参数,结构本身仍是标准 pre-norm ViT block + LayerScale + DropPath。

### 1.3 Dual-DPT 双分支头

`model/dualdpt.py:30`(`DualDPT`):

- 固定取 4 个中间层(`intermediate_layer_idx = (0,1,2,3)`,`model/dualdpt.py:76`),即 backbone `out_layers` 指定的 4 层
- 每层:LayerNorm → 1x1 conv 投影到 `out_channels` → 空间重采样对齐(×4、×2、×1、÷2,`model/dualdpt.py:86-97`)
- **两套完全独立的 fusion 链**:main 链 `refinenet1-4`(`model/dualdpt.py:103-106`),aux 链 `refinenet1_aux-4_aux`(`model/dualdpt.py:121-124`),注释明确"no sharing"(对应论文 depth-ray 共享 encoder 但解码头分离的设计)
- **main(depth)头**:`features → features//2 → 32 → output_dim=2`(`model/dualdpt.py:108-118`),输出 **1 维 depth(exp 激活)+ 1 维 depth_conf(expp1 激活,即 conf ≥ 1)**,见 `model/dualdpt.py:244-247, 341-364`
- **aux(ray)头**:内部多级金字塔(`aux_pyramid_levels=4`),每级有独立 neck(`_make_aux_out1_block`,默认 5 层 conv,`model/dualdpt.py:321-330`),最终投影输出 **7 通道**(`model/dualdpt.py:146`:6 维 ray = 3 方向 + 3 原点,外加 1 维 ray_conf,expp1 激活),只有最后一级返回(`model/dualdpt.py:249-258`)
- 支持沿帧维度分块省显存(`chunk_size=8`,`model/dualdpt.py:162-202`)
- `model/dpt.py:31` 是单头版本(mono/metric 用),`output_dim=1` 时只有 depth 无 conf,并额外带固定 1 通道的 `sky` 头(`use_sky_head=True`)

### 1.4 camera token 编码与相机解参

**cam_enc**(`model/cam_enc.py:23`):输入外参 → `affine_inverse` 转 c2w(`model/cam_enc.py:70`)→ `extri_intri_to_pose_encoding` 编码为 **9 维 [T(3), quat-xyzw(4), fov_h, fov_w]**(`model/utils/transform.py:19-38`)→ MLP `pose_branch`(9 → dim_out/2 → dim_out)→ 4 层 transformer Block trunk(`model/cam_enc.py:44-54`)→ 输出每视图一个 pose token,注入 backbone 第 `alt_start` 层。

**cam_dec**(`model/cam_dec.py:19`):输入为最后一层 out_layer 的 **camera token**(`feats[-1][1]`,`model/da3.py:216`,维度 = 2×embed,因为 cat_token 拼接)→ 2 层 MLP → 三个并头 `fc_t`(3 平移)/`fc_qvec`(4 四元数)/`fc_fov`(2 视场角,`model/cam_dec.py:29-31`)→ 拼成 9 维 pose encoding → `pose_encoding_to_extri_intri` 转 c2w 外参 + 内参(`model/da3.py:224`,`model/utils/transform.py:41-65`;注意主点被硬设为图像中心 `W/2, H/2`,`transform.py:55-56`),再取逆得到 w2c(`model/da3.py:225`)。

**ray map 解相机**(`use_ray_pose` 路径,`model/da3.py:181-203` + `utils/ray_utils.py:435-523`):把 aux 头输出的每 patch 6 维 camray 与单位焦距相机平面做**置信度加权 RANSAC 单应估计**,再经 QL 分解得到旋转 R、焦距、主点(`utils/ray_utils.py:21-91`);平移 = ray 原点的置信度加权平均(`utils/ray_utils.py:495-498`);内参按 `f/2×W` 还原(`model/da3.py:195-198`,归一化约定"图像宽=2")。

### 1.5 各规格配置一览

| 配置 | backbone | out_layers | alt/qknorm/rope_start | head dim_in | features | out_channels | cam_enc dim_out | cam_dec dim_in | README 参数量 |
|---|---|---|---|---|---|---|---|---|---|
| da3-small | vits (E=384, L=12, H=6) | [5,7,9,11] | 4 | 768 (=2×384) | 64 | [48,96,192,384] | 384 | 768 | 0.08B |
| da3-base | vitb (E=768, L=12, H=12) | [5,7,9,11] | 4 | 1536 | 128 | [96,192,384,768] | 768 | 1536 | 0.12B |
| da3-large | vitl (E=1024, L=24, H=16) | [11,15,19,23] | 8 | 2048 | 256 | [256,512,1024,1024] | 1024 | 2048 | 0.35B |
| da3-giant | vitg (E=1536, L=40, H=24, SwiGLU) | [19,27,33,39] | 13 | 3072 | 256 | [256,512,1024,1024] | 1536 | 3072 | 1.15B |
| da3metric-large | vitl | [4,11,17,23] | **-1(全关)** | 1024 (cat_token=False) | 256 | [256,512,1024,1024] | 无 | 无 | 0.35B |
| da3mono-large | vitl | [4,11,17,23] | -1 | 1024 | 256 | [256,512,1024,1024] | 无 | 无 | 0.35B |

- 出处:`configs/da3-small.yaml`、`da3-base.yaml`、`da3-large.yaml`、`da3-giant.yaml`、`da3metric-large.yaml`、`da3mono-large.yaml`
- da3-giant 额外含 `gs_head`(output_dim 38)+ `gs_adapter`(sh_degree 2)
- `da3nested-giant-large.yaml`:`NestedDepthAnything3Net`(`model/da3.py:308`),`anyview` 继承 da3-giant、`metric` 继承 da3metric-large(cfg 支持 `__inherit__` 递归解析,`cfg.py:74-90`),合计 README 标 1.40B
- 输入分辨率:默认 `process_res=504`(`api.py:145`),边界缩放后强制 14 整除(`utils/io/input_processor.py:44-57, 415-416`);backbone 位置编码 bicubic 插值、`interpolate_offset=0.1`(`model/dinov2/vision_transformer.py:106, 220-254`)

---

## 2. 推理入口

### 2.1 api.py(主 API)

`api.py:48` `DepthAnything3(nn.Module, PyTorchModelHubMixin)`,`from_pretrained` 从 HF Hub 拉取 `model.safetensors`+`config.json`。`inference()`(`api.py:133-273`)流程:

1. `InputProcessor`:读图 → 边界 resize(upper/lower bound,保长宽比)→ 14 对齐(resize 系四舍五入、crop 系中心裁)→ ImageNet 归一化 → 堆叠 `(1, N, 3, H, W)`(`utils/io/input_processor.py:35-54`)
2. 外参归一化:以第 0 帧为参考系,平移按相机到参考帧距离中位数缩放(clamp ≥ 0.1,`api.py:327-339`)
3. `forward`:`torch.inference_mode` + autocast(bf16 优先否则 fp16,`api.py:126-131`)
4. 输出转 `Prediction`(`specs.py:25-45`):`depth[N,H,W]`、`conf`、`sky`、`extrinsics[N,3,4]`(OpenCV w2c / COLMAP 格式)、`intrinsics[N,3,3]`、`gaussians`(可选)、`aux`、`scale_factor`
5. 可选把预测位姿 Umeyama 对齐回输入位姿(≥10 视图时 RANSAC,`api.py:341-365`,`utils/pose_align.py`)
6. 导出:`mini_npz / npz / glb / ply / gs / gs_video / colmap / feat_vis`(`utils/export/`)

### 2.2 cli.py

typer app(`pyproject.toml` 注册 `da3 = depth_anything_3.cli:app`),子命令:`auto`(:112)、`image`(:316)、`images`(:392)、`colmap`(:471)、`video`(:558)、`backend`(:640,常驻 GPU 缓存模型)、`gradio`(:707)、`gallery`(:787)。`video` 支持 ffmpeg 抽帧、`--export-feat "11,21,31"` 导出中间层特征可视化(README:140-147)。

### 2.3 3DGS 头(gsdpt.py + gs_adapter.py)

- `model/gsdpt.py:24` `GSDPT(DPT)`:`head_name="raw_gs"`、`activation="linear"`、`conf_activation="sigmoid"`;独有 `images_merger`(3 层 conv,RGB 3ch → features/2)把原图信息加进融合特征(`model/gsdpt.py:64-71, 109`)
- 输出维度:`output_dim = gs_adapter.d_in + 1`(`model/da3.py:88`),da3-giant 配置 = 38
- `model/gs_adapter.py:188-200` `d_in = 2(xy 偏移)+3(scale)+4(quat)+3×d_sh+1(depth 偏移)`;`sh_degree=2, pred_color=false` → `d_sh=(2+1)²=9`(`model/gs_adapter.py:184-186`),即 **每像素 37 维高斯参数 + 1 维 opacity 密度**
- SH 处理:`sh_mask` 把高阶系数初始缩放 `0.1×0.25^degree`(`model/gs_adapter.py:49-56`);SH 系数随相机旋转到世界系(`model/gs_adapter.py:153-158`,基于 `utils/sh_helpers.rotate_sh`)
- 几何:世界坐标 = 射线原点 + 方向 ×(深度 + 可预测 offset,`model/gs_adapter.py:103-118`);尺度经 sigmoid 钳到 [1e-5, 30] 后乘深度与内参 multiplier(分辨率不变性,`model/gs_adapter.py:124-131`);四元数按 xyzw 输入、归一化后旋转到世界系 wxyz(`model/gs_adapter.py:133-146`)
- 若给 GT 位姿,Umeyama 对齐尺度并 clamp 到 [1/3, 3](`model/gs_adapter.py:89-101`);GS 分支强制用**预测位姿**对齐 GS(`model/da3.py:245-252` 注释)
- opacity = `map_pdf_to_opacity(densities)`(`model/da3.py:277`,`utils/geometry.py:333-348`)

### 2.4 reference_view_selector

`model/reference_view_selector.py:29-112`:多视图(S≥3)时在 backbone 中部选"参考视图"并排到第 0 位。4 种策略:`first`、`middle`、`saddle_balanced`(对相似度得分/特征范数/特征方差三个指标归一化后取最接近中位数的视图)、`saddle_sim_range`(与其他视图相似度跨度最大的视图)。默认 `saddle_balanced`;评测固定用 `first` 保证可复现(`utils/constants.py:28`)。对应论文中"first frame as reference"的实现细节补充。

---

## 3. 流式推理(da3_streaming/)

主 README News(README.md:43)宣称"<12GB GPU memory"。实现机制(**不改模型任何层**):

- **滑窗分块**:`chunk_size=120, overlap=60`(半窗重叠,`da3_streaming/configs/base_config.yaml`),每块独立跑完整 DA3 推理(`da3_streaming/da3_streaming.py:253-306`)
- **块间对齐**:重叠区点云 + 置信度加权 Sim3 对齐(`align_2pcds`,`da3_streaming/da3_streaming.py:322-364`;可选 sim3/se3/scale+se3,IRLS 加权)
- **回环闭合**:SALAD(DINO 全局描述子)检索回环(相似度阈值 0.85),`Sim3LoopOptimizer` 全局优化(`da3_streaming/loop_utils/`)
- **落盘 + 清理**:每块预测存 `_tmp_results_*.npy`,用完即删(`delete_temp_files`),配合 `torch.cuda.empty_cache()`(`da3_streaming/da3_streaming.py:267-283`)
- 省显存证据见 README 表格(da3_streaming/README.md:147-152):KITTI 504x154 chunk 30 → **峰值 11.5GB**,chunk 120 → 15.9GB;TUM 504x378 chunk 30 → 18.7GB。"<12GB"对应小 chunk + 窄分辨率(KITTI 154px 高)场景
- 模型侧的省显存手段只有 DualDPT 的帧分块(`chunk_size=8`,`model/dualdpt.py:162`)
- 另注意 streaming 里 `predictions.conf -= 1.0`(`da3_streaming/da3_streaming.py:276`)—— 因为 depth_conf 是 expp1 激活(≥1)
- 速度:A100 约 8.51 FPS(da3_streaming/README.md:124-130)

---

## 4. 超参与依赖

- `requirements.txt` / `pyproject.toml`:`torch>=2`、torchvision、xformers、numpy<2、einops、huggingface_hub、opencv-python、open3d、typer(≥0.9)、omegaconf、addict(隐式)、e3nn、evo、moviepy==1.0.3、plyfile、pillow_heif、safetensors、pycolmap;Python ≥3.9,≤3.13
- gsplat 固定 commit:`git+...@0b4dddf04cb687367602c01196913cde6a743d70`(pyproject `[gs]` extra)
- 流式额外依赖:`faiss-gpu、pandas、numba、pypose`(`da3_streaming/requirements.txt`)
- 权重(HF `depth-anything/` 命名空间,README.md:213-230):
  | 仓库 | 参数量 | 许可 |
  |---|---|---|
  | DA3-SMALL | 0.08B | Apache 2.0 |
  | DA3-BASE | 0.12B | Apache 2.0 |
  | DA3-LARGE(-1.1) | 0.35B | CC BY-NC 4.0 |
  | DA3-GIANT(-1.1) | 1.15B | CC BY-NC 4.0 |
  | DA3METRIC-LARGE | 0.35B | Apache 2.0 |
  | DA3MONO-LARGE | 0.35B | Apache 2.0 |
  | DA3NESTED-GIANT-LARGE(-1.1) | 1.40B | CC BY-NC 4.0 |
- `-1.1` 后缀为修复训练 bug 后重训版,官方推荐(README.md:211);代码仓库本身 Apache-2.0(LICENSE)

---

## 5. README 关键信息

- 快速开始:`pip install xformers torch>=2 torchvision; pip install -e .`(README.md:88-94);`DepthAnything3.from_pretrained("depth-anything/DA3NESTED-GIANT-LARGE")` → `model.inference(images)`(README.md:100-121)
- 权重下载:HF Hub 自动下载,镜像 `HF_ENDPOINT=https://hf-mirror.com`(README.md:127)
- **纯推理仓库,无训练代码**;评测基准在 `bench/`(evaluator + 5 数据集 DTU/DTU64/ETH3D/7Scenes/ScanNet++/HiRoom,`bench/evaluator.py`、`utils/constants.py:34-200`),数据托管 `depth-anything/DA3-BENCH`(docs/BENCHMARK.md)
- 单目 metric 换算公式:`metric_depth = focal × net_output / 300.`(README.md:235),NESTED 输出已是米制
- 引用 BibTeX:arXiv:2511.10647(README.md:321-328)

---

## 6. 与论文宣称的出入

论文称 "single plain transformer, no architectural specialization"(README.md:22-24)。源码实情:

1. **Block 级确实无专用结构** —— `layers/block.py` 就是标准 pre-norm ViT block(LayerScale + DropPath + MLP/SwiGLU),与官方 DINOv2 基本一致
2. **但调度与 token 级有明显改造**(均在 `model/dinov2/vision_transformer.py`):
   - local/global 交替注意力(`alt_start` 机制,:333-339)——官方 DINOv2 无此概念
   - camera token 参数与注入(:163, :323-331)
   - 参考视图选择 + 视图重排(:314-321,依赖新增的 `model/reference_view_selector.py`)
   - cat_token 双流特征拼接(:342, :383-398)
   - qk_norm / rope_start 开关、RoPE 的 pos/pos_nodiff 双坐标(:282-298)
   - `layers/attention.py` 增加 qk_norm/rope/attn_mask;删除 MemEffAttention
   - `layers/rope.py` 与官方 dinov2 rope 实现同源(注释引用 rope-vit),但 pos_nodiff 的用法是 DA3 特有
3. **monocular/metric 变体 = 同代码、配置开关**:da3metric/da3mono 把 `alt_start/qknorm_start/rope_start` 全部设为 -1、`cat_token=False`,backbone 即退回原版 DINOv2 行为(无 camera token、无跨视图 attention),head 换成单头 DPT + sky 头 —— 这佐证了"单模型覆盖单目/多目"的说法
4. 深度头是 **exp 激活直接回归深度**(非 disparity),`model/dualdpt.py:50, 349-350`,README 亦强调 "directly predicts depth"(README.md:63)

---

## 7. 论文未写、读源码才发现的工程细节

1. **dtype 双轨策略**:backbone 在 autocast(bf16/fp16)里跑,但 `cam_enc`、depth head、相机解码全程强制 fp32(`model/da3.py:127, 139`;`model/cam_dec.py:37-40` 的 `.float()`)—— 几何量对精度敏感
2. **置信度定义**:`expp1` 激活 ⇒ depth_conf/ray_conf ≥ 1(`model/dualdpt.py:51, 353-354`),streaming 中需 `conf -= 1.0` 归零(`da3_streaming/da3_streaming.py:276`)
3. **天空后处理**:mono 模型的 sky 头置信阈值 0.3,天空像素深度直接设为非天空深度的 0.99 分位数(nested 还封顶 200m,`model/da3.py:155-179, 418-442`),置信度随之置高
4. **位姿归一化约定**:输入外参先归一化到"第 0 帧参考系 + 平移按中位距离缩放"(`api.py:327-339`);ray 解码的内参用"图像宽高=2"的归一化约定(`model/da3.py:195-198`)
5. **cam_dec 主点硬编码为图像中心**(`model/utils/transform.py:55-56`),四元数顺序 xyzw(scalar-last),而 GS 内部注释承认"历史问题"用 xyzw 输入、输出转 wxyz(`model/gs_adapter.py:134`)
6. **GS 尺度分辨率不变性**:scale 乘以内参逆×像素尺寸的 multiplier(`model/gs_adapter.py:171-182`),保证不同输入分辨率下高斯大小一致
7. **全局层 RoPE 用共享坐标**(pos_nodiff):跨视图 attention 中所有视图共享同一组 patch 坐标,不注入视图序号信息(`model/dinov2/vision_transformer.py:290-297, 308-312`)

---

*报告完。审计中未找到训练代码;`notebooks/da3.ipynb` 为演示 notebook。*
