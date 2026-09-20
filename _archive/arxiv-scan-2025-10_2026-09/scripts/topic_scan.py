# -*- coding: utf-8 -*-
"""主题矩阵筛选：对全量 listing 索引跑多组 AND/OR 条件，输出分主题候选清单。

用法:
  python topic_scan.py                     # 全部主题，全部月份
  python topic_scan.py 2026-05 2026-06     # 限定月份
  python topic_scan.py all T1              # 只跑某主题
输出:
  .tmp_scan/topics/<T>_<range>.txt  可读清单
  终端汇总每主题命中数
"""
import json, os, re, sys, glob

ROOT = r'C:\code\media_paper\.tmp_scan'
RAW = os.path.join(ROOT, 'list_raw2')
OUT = os.path.join(ROOT, 'topics')
os.makedirs(OUT, exist_ok=True)

# 每个主题: (说明, [OR组1, OR组2, ...])  组间 AND
TOPICS = {
 'T1_long_video_consistency': ('长程/世界一致视频生成（Lyra2/OctWorld 主线）', [
   'world model|long video|long-form video|long-term video|long-range|long horizon|autoregressive|minute-long|infinite video|explorable|persistent|world-consistent',
   'consisten|memory|forget|drift|revisit|loop closure|scene memory|coherent|3d'],
 ),
 'T2_video_diff_to_3d': ('视频/图像扩散蒸馏成 3D 表示', [
   'diffusion|distill|generative|feed-forward|feedforward|amortized|video model|latent|prior|pretrained|diffusion model|prior',
   '3d gaussian|gaussian splatting|3dgs|3d representation|3d asset|scene representation|3d scene|geometry|reconstruction|splatting|3d |3d'],
 ),
 'T3_feedforward_recon': ('前馈/生成式 3D 场景重建', [
   'feed-forward|feedforward|single image|single-view|few-shot|sparse view|uncalibrated|pose-free',
   '3d reconstruction|scene reconstruction|3d generation|novel view|gaussian|point cloud|mesh'],
 ),
 'T4_4d_dynamic': ('4D / 动态高斯 / 时序重建', [
   '4d |4d-|dynamic scene|dynamic gaussian|spacetime|space-time|deformable|temporal|dynamic',
   'gaussian|reconstruction|avatar|human|scene|splatting'],
 ),
 'T5_human_avatar': ('人体/人脸重建与 avatar（vggt_human 相关）', [
   'human|face|head|body|avatar|character|person',
   'reconstruction|mesh|gaussian|smpl|3dmm|animation|gaussian splatting|digit'],
 ),
 'T6_geometry_prior': ('几何先验注入生成（一致性/相机控制）', [
   'geometry|geometric|depth|camera|epipolar|multi-view',
   'prior|consistency|consistent|control|condition|guidance',
   'diffusion|generation|video|3d'],
 ),
 'T7_memory_mapping': ('场景记忆 / 长时程建图 / 世界状态', [
   'memory|map|mapping|slam|octree|voxel|tsdf|keyframe|cache',
   '3d|gaussian|scene|spatial|video|long|persistent'],
 ),
 'T8_surface_mesh': ('表面重建 / 网格提取', [
   'surface reconstruction|mesh extraction|mesh generation|signed distance|sdf|tsdf|marching cubes|occupancy|mesh|surface',
   'gaussian|3d|scene|neural|real-time|editable|reconstruction|generation'],
 ),
 'T9_wide_catchall': ('宽口径兜底（任一核心词命中；高召回高噪声，用于量化主矩阵漏检）', [
   '3d gaussian|gaussian splatting|3dgs|splatting|gaussian|3d reconstruction|scene reconstruction|3d generation|scene generation|3d scene|feed-forward|feedforward|novel view|sparse|multi-view|multiview|unposed|uncalibrated|pose-free|world model|video diffusion|4d|avatar|human reconstruction|point cloud|nerf|radiance field|depth estimation|octree|voxel|tsdf|distillation|consistency|temporal|occupancy|relight|geometry|surface reconstruction|splat|mesh'],
 ),
}

STRONG = ['3d gaussian', 'gaussian splatting', '3dgs', 'splatting', 'world model',
          'video diffusion', 'feed-forward', 'feedforward', 'self-distill', 'distill',
          '4d', 'avatar', 'scene generation', '3d reconstruction', 'novel view',
          'scene memory', 'spatial memory', 'long video', 'autoregressive', 'octree',
          'surface reconstruction', 'human', 'gaussian']


def load(months=None):
    rows = []
    for p in sorted(glob.glob(os.path.join(RAW, '*.jsonl'))):
        ym = os.path.basename(p).split('_')[-1].replace('.jsonl', '')
        if months and ym not in months:
            continue
        for line in open(p, encoding='utf-8'):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    # 去重（同一 id 可能在 cs.CV 与 cs.GR 都出现）
    seen, uniq = set(), []
    for r in rows:
        if r['id'] in seen:
            continue
        seen.add(r['id'])
        uniq.append(r)
    return uniq


def blob(r):
    return (r['title'] + ' ' + r.get('comment', '') + ' ' + r.get('subjects', '')).lower()


def score(r):
    b = blob(r)
    return sum(1 for w in STRONG if w in b)


def run(rows, only=None):
    summary = []
    for tname, (desc, groups) in TOPICS.items():
        if only and tname != only:
            continue
        hits = []
        for r in rows:
            b = blob(r)
            if all(any(alt.strip().lower() in b for alt in g.split('|')) for g in groups):
                hits.append(r)
        hits.sort(key=lambda r: (-score(r), r['id']))
        summary.append((tname, desc, len(hits)))
        with open(os.path.join(OUT, '%s.txt' % tname), 'w', encoding='utf-8') as f:
            f.write('# %s — %s\n# %d hits\n\n' % (tname, desc, len(hits)))
            for r in hits:
                c = ('  [' + r['comment'][:70] + ']') if r.get('comment') else ''
                f.write('%s  s=%2d  %s%s\n' % (r['id'], score(r), r['title'], c))
    return summary


def main():
    args = sys.argv[1:]
    months = None
    only = None
    for a in args:
        if re.match(r'^\d{4}-\d{2}$', a):
            months = (months or []) + [a]
        elif a.startswith('T'):
            only = a
    rows = load(months)
    print('loaded %d unique entries  months=%s' % (len(rows), months or 'ALL'))
    s = run(rows, only)
    print()
    for t, d, n in s:
        print('  %-30s %6d   %s' % (t, n, d))
    # 主题并集
    if not only:
        union = set()
        for tname, (desc, groups) in TOPICS.items():
            p = os.path.join(OUT, '%s.txt' % tname)
            for line in open(p, encoding='utf-8'):
                m = re.match(r'^(\d{4}\.\d{4,5})', line)
                if m:
                    union.add(m.group(1))
        print('\n  union(all topics): %d unique papers' % len(union))


if __name__ == '__main__':
    main()
