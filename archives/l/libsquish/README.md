# libsquish

## 简介
libsquish 是一个开源的 DXT/S3TC 纹理压缩库，由 Simon Brown 开发。
支持 DXT1/DXT3/DXT5（BC1/BC2/BC3）以及 BC4/BC5 压缩格式。

## OHOS 适配
- 上游使用原生 CMake 构建，无外部依赖。
- 目标平台为 OpenHarmony aarch64（ARM）：
  - 关闭 x86 专属 SSE2 路径（`BUILD_SQUISH_WITH_SSE2=OFF`）。
  - 关闭 Altivec（`BUILD_SQUISH_WITH_ALTIVEC=OFF`）。
  - 关闭 OpenMP（`BUILD_SQUISH_WITH_OPENMP=OFF`）。
  - 使用纯标量 portable 实现（`simd_float.h`），保证 ARM 平台正确运行。
- 无需补丁，上游 CMakeLists.txt 通过 option 即可关闭 SIMD。

## 依赖
- 无编译依赖、无运行时依赖。

## 功能验证
- test_package 使用真实 squish API：创建 RGBA 像素块 → DXT1 压缩 → 解压 → 校验。
