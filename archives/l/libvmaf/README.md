# libvmaf - Video Multi-Method Assessment Fusion Library

libvmaf 是 Netflix 开发的视频质量评估库，用于客观评估视频质量。

## 功能特性

- 多方法融合评估（VMAF）
- 支持多种特征提取器（PSNR、SSIM、MS-SSIM、ADM 等）
- 提供 C/C++ API 和命令行工具
- 支持自定义 model 配置

## 编译说明

本版本编译时禁用了 built-in models，用户需单独配置 model 路径。

## 使用示例

```bash
# 计算 VMAF 分数
vmaf --reference ref.yuv --distorted dist.yuv \
  --width 1920 --height 1080 \
  --model path=/path/to/vmaf_model.json
```

## API 示例

```c
#include <libvmaf/libvmaf.h>

VmafContext *vmaf;
VmafConfiguration cfg = {
    .n_threads = 4,
    .n_subsample = 1,
};

vmaf_init(&vmaf, cfg);
vmaf_read_pictures(vmaf, &ref, &dist, frame_index);
vmaf_score_at_index(vmaf, model, &score, frame_index);
vmaf_close(vmaf);
```

## 相关资源

- 官方仓库: https://github.com/Netflix/vmaf
- 文档: https://netflix.github.io/vmaf-doc/