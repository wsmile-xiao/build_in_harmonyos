# ffnvcodec-headers 13.0.19.0 — 编译笔记

## 基本信息
- 软件: ffnvcodec-headers (NVIDIA Video Codec SDK 头文件)
- 版本: 13.0.19.0
- 构建系统: makefile (header-only)
- 编译器: clang 15.0.4
- 平台: HarmonyOS aarch64

## 编译过程

### 构建步骤
1. `make PREFIX=$DEFAULT_PREFIX all` — 生成 ffnvcodec.pc (sed 替换前缀)
2. `make PREFIX=$DEFAULT_PREFIX install DESTDIR=$TEST_PREFIX` — 安装头文件和 pkg-config 文件

### 补丁
无需源码修改（纯头文件包）

### 验证
- Staging 验证: ✅ PASS
  - 头文件: 5 个 (dynlink_cuda.h, dynlink_cuviddec.h, dynlink_loader.h, dynlink_nvcuvid.h, nvEncodeAPI.h)
  - pkg-config: ffnvcodec.pc (版本 13.0.19.0)

## 适配说明
- ffnvcodec-headers 是 NVIDIA 视频编解码 SDK 的头文件包
- 无需编译步骤，仅安装头文件和 pkg-config 元数据
- FFmpeg 编译时通过 pkg-config 查找此包以启用 NVENC/NVDEC 支持