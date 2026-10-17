# vvenc - Fraunhofer Versatile Video Encoder (H.266/VVC)

## 简介

VVenC（Fraunhofer Versatile Video Encoder）是 H.266/VVC 的开源高效软件编码器实现，
由 Fraunhofer HHI 主导开发。主要特性：

- 易用的编码器接口，内置五档质量/速度预设（faster / fast / medium / slow / slower）
- 基于 XPSNR 视觉模型的可感知质量优化
- 帧级与任务级并行，良好的多线程扩展性
- 支持单遍与两遍码率控制（VBR）

本适配提供 `libvvenc` 共享库、`vvencapp` 命令行编码器与 `vvencFFapp` 全特性编码器。

## 版本

- 已适配版本：1.14.0

## 构建信息

- 构建系统：CMake（`cmake_minimum_required 3.13`）
- 编译器：Clang 15.0.4（OHOS SDK）
- 目标平台：OpenHarmony / HarmonyOS PC (aarch64)
- 交叉三元组：`aarch64-linux-ohos`

## 依赖

无外部第三方依赖。x86 SIMD 由内置 `thirdparty/simde`（SIMD Everywhere）实现；
`nlohmann_json` 为源码内自带（`VVENC_ENABLE_THIRDPARTY_JSON=ON` 默认）；
线程库由 OHOS sysroot 提供。

## 用法

```bash
vvencapp --help
vvencapp --preset medium -s 832x480 -r 30 -i input.yuv -o output.vvc
```

CMake 消费：

```cmake
find_package(vvenc REQUIRED)
target_link_libraries(myapp PRIVATE vvenc::vvenc)
```

## 许可

The Clear BSD License（SPDX: `BSD-3-Clause-Clear`）
