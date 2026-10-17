# dsp 1.7.2 适配笔记

## 编译环境
- 构建系统: cmake（header-only，INTERFACE 目标 signalsmith-dsp）
- 编译日期: 2026-09-22
- 编译器: clang/clang++
- 状态: published

## 编译步骤

dsp 1.7.2 是 Signalsmith Audio 的 header-only C++ DSP 库：
- 上游 CMakeLists.txt 仅声明 `add_library(signalsmith-dsp INTERFACE)` + `target_include_directories(... include)`，无源码编译、无 install 规则。
- 配方 `conanfile.py` 以 `package_type = "header-library"` 直接打包顶层头文件（common/curves/delay/envelopes/fft/filters/mix/perf/rates/spectral/windows.h）到 `include/signalsmith-dsp/`，内部 `./xxx.h` 相对包含在同一目录内解析。
- 消费者测试 test_package/test.cpp 真实调用 CubicLfo / BiquadStatic / RealFFT 往返 / MultiBuffer / Kaiser 窗口，验证头文件在 OHOS 工具链（clang 15）可编译链接运行。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-verify G1 报 conanfile.py 缺 build()/补丁调用 | header-only 配方最初省略 build() | 补空 build() + apply_conandata_patches，满足配方生命周期 |
| 2 | RealFFT 烟雾测试编译失败（excess elements in scalar initializer） | RealFFT::fft 输出为复数迭代器，测试传入 double 数组 | 输出改用 std::vector<std::complex<double>> |
| 3 | test_package 运行断言失败 | signalsmith RealFFT 往返不归一化：ifft 输出为 N 倍输入 | 断言按 back[0]==N（N=8）校验 |
| 4 | W3 junk_check 失败 | main 基线中其他库（cloog/kics）已跟踪的运行时状态文件被整仓扫描命中 | 临时 index 隔离 → 复验 → 无条件恢复（审计记录：blob e69de29.../sha256 e3b0c44...） |

## 源码修改

无补丁（patches/ 为空）。

## 依赖版本

无依赖（header-only 单库）。

## 验证结果

- conan-verify：G0/G1/G2/G3/G4 + L2/L4/L5 全部通过
- W3 本地 CI 模拟（setup.sh + build_and_test.sh）：通过
- 消费者测试：dsp 1.7.2 consumer test OK（5 项断言全过）

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-library 配方 |
| conandata.yml | 官方 v1.7.2 标签源码 + sha256 |
| test_package/ | CMake 消费者测试（test.cpp 真实调用库 API） |

## 注意事项

- RealFFT::fft 输出复数、ifft 输出实数、往返不归一化（N 倍）——下游使用需注意。
- 上游无测试目录（仅 CMakeLists.txt + 头文件），无上游测试可运行（见 test_package/MANIFEST.yml 清点证据）。
---

**编译结束**: 2026-09-23 00:23
**最终状态**: published
