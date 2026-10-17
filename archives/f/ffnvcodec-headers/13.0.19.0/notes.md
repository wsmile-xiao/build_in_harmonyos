# ffnvcodec-headers 13.0.19.0 — 编译笔记

## 基本信息
- 软件: ffnvcodec-headers (NVIDIA Video Codec SDK 头文件)
- 版本: 13.0.19.0
- 构建系统: makefile (header-only)
- 编译器: clang 15.0.4
- 平台: HarmonyOS aarch64

## 编译过程

### 构建步骤
1. `make PREFIX=$PACKAGE_FOLDER all` — 生成 ffnvcodec.pc (sed 替换前缀)
2. `copy *.h` → `include/ffnvcodec/` (Conan package() 手动复制头文件)
3. `copy ffnvcodec.pc` → `lib/pkgconfig/` (Conan package() 手动复制 pkg-config 文件)

### 补丁
无需源码修改（纯头文件包）

### 验证
- Staging 验证: ✅ PASS
  - 头文件: 5 个 (dynlink_cuda.h, dynlink_cuviddec.h, dynlink_loader.h, dynlink_nvcuvid.h, nvEncodeAPI.h)
  - pkg-config: ffnvcodec.pc (版本 13.0.19.0)
- Conan create: ✅ PASS (G2 干净构建通过)
- W3 本地 CI 模拟: ✅ PASS (L0-L5 全部通过)
- test_package: ✅ PASS (NV_ENC_SUCCESS=0 验证通过)

## 适配说明
- ffnvcodec-headers 是 NVIDIA 视频编解码 SDK 的头文件包
- 无需编译步骤，仅安装头文件和 pkg-config 元数据
- FFmpeg 编译时通过 pkg-config 查找此包以启用 NVENC/NVDEC 支持
- Conan 配方类型: header-library (无 shared/static 选项)
- 构建命令: make -C {source_folder} PREFIX={package_folder} all

## 结束
编译完成，状态: built (conan-verify 通过，待 CI upload 后改为 published)
