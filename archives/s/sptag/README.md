# sptag — OpenHarmony 编译记录

## 基本信息
- 软件: sptag
- 版本: 0.0-git20230612.2ffaec6（上游 commit 2ffaec6，2023-06-12）
- 构建系统: cmake
- 目标: ohos-aarch64

## 编译指导
- 依赖先行：boost1.84 系列组件包 + libomp/15.0.4 必须已发布（R36）。
- ThirdParty/zstd 是 git submodule，source() 阶段自动补 vendor，无需手动处理。
- 上游测试：build() 直接运行 `Release/SPTAGTest --log_level=test_suite`（39 cases）。
- 详见版本目录 notes.md。

## 补丁清单
- 0001-top-cmake-clang-conan-boost.patch：Clang 支持 + Conan 工具链标志保留 + Boost 注入
- 0002-annservice-x86-only-simd-flags.patch：-mavx2 等标志仅限 x86
- 0003-common-portable-alloc-prefetch.patch：可移植对齐分配/prefetch/ACCESSPERMS
- 0004-instructionutils-arm-fallback.patch：非 x86 的 cpuid 检测桩
- 0005-simdutils-arm-fallback.patch：SIMD 求和核标量兜底
- 0006-distanceutils-arm-fallback.patch：SIMD 距离核标量兜底
- 0007-test-headeronly-boost.patch：Boost.Test header-only + 去测试二进制安装

## 已知限制
- Python/Java/C# 绑定与 GPU 加速在 OHOS 包中关闭（无 swig/JDK/CUDA）。
- aarch64 上距离/求和核走标量实现（精度一致，速度低于 x86 SIMD）。

## 功能验证
- `conan create` 跑通 SPTAGTest（39 cases）与 test_package（12 断言）后更新此处。
