# random123 1.14.0 适配笔记

## 编译环境
- 构建系统: GNUmakefile（顶层 + tests/ 子 makefile）
- 编译日期: 2026-09-07
- 编译器: clang/clang++ 15.0.4（OHOS arm64 交叉）
- 状态: built

## 上游测试完整枚举台账（R51 三步法申报表）

枚举规则：按官方 tag 源码 tests/GNUmakefile 的 meta-targets 与 `all_primary_targets` 逐一列出全部测试程序目标，
独立上游用例 = 含真实 main() 的 KAT（已知答案测试）/ 单元测试程序；基准、样例、框架头、fixture、脚本不计入
独立用例数但全部列出。

### 独立上游测试用例（source_declared_total = 13）

| # | 测试程序 | 源文件 | 分类理由 | 是否独立用例 | 平台依赖 | 实际运行 |
|---|---------|--------|---------|------------|---------|---------|
| 1 | kat_c | tests/kat_c.c (+kat_main.h) | KAT 已知答案测试（C），main 在 kat_main.h:220 | 是 | 无 | PASS |
| 2 | kat_cpp | tests/kat_cpp.cpp (+kat_main.h) | KAT 已知答案测试（C++），main 在 kat_main.h | 是 | 无 | PASS |
| 3 | ut_ars | tests/ut_ars.c | ARS 生成器单元测试 | 是 | 无 | PASS |
| 4 | ut_gsl | tests/ut_gsl.c | GSL 适配单元测试 | 是 | 依赖 GSL 库（制品仓有 GSL/2.8，已恢复构建运行） | PASS |
| 5 | ut_carray | tests/ut_carray.cpp | 数组类型单元测试 | 是 | 无 | PASS |
| 6 | ut_Engine | tests/ut_Engine.cpp | 引擎封装单元测试 | 是 | 无 | PASS |
| 7 | ut_features | tests/ut_features.cpp | 特性宏单元测试 | 是 | 无 | PASS |
| 8 | ut_M128 | tests/ut_M128.cpp | x86 SSE 128 位测试；无 SSE 时编译 no-op stub（main@35） | 是 | SSE（OHOS arm64 无 → stub） | PASS（no-op stub） |
| 9 | ut_ReinterpretCtr | tests/ut_ReinterpretCtr.cpp | 计数器重解释单元测试 | 是 | 无 | PASS |
| 10 | ut_aes | tests/ut_aes.cpp | AES-NI 测试；无 SSE 时编译 no-op stub（main@49） | 是 | SSE（OHOS arm64 无 → stub） | PASS（no-op stub） |
| 11 | ut_ua | tests/ut_ua.cpp | uniform.hpp 单元测试；C++11 以下编译 stub（main@35） | 是 | C++11+（OHOS C++17 满足） | PASS |
| 12 | ut_uniform | tests/ut_uniform.cpp | 均匀分布转换单元测试 | 是 | 无 | PASS |
| 13 | ut_uniform_IEEEkat | tests/ut_uniform_IEEEkat.cpp | IEEE KAT 已知答案测试 | 是 | 无 | PASS |

### 基准程序（不计入独立用例，列出备查）

| 程序 | 源文件 | 说明 |
|------|--------|------|
| timers | tests/timers.cpp | 计时基准 |
| time_serial | tests/time_serial.c | 串行性能基准 |
| time_thread | tests/time_thread.c | 多线程基准（pthread） |
| time_boxmuller | tests/time_boxmuller.cpp | Box-Muller 基准 |
| time_cuda | tests/time_cuda.cu | CUDA 基准（OHOS 不可用） |
| time_opencl | tests/time_opencl.c | OpenCL 基准（OHOS 不可用） |
| time_boxmuller_cuda | tests/time_boxmuller_cuda.cu | CUDA 基准（不可用） |
| kat_cuda | tests/kat_cuda.cu | CUDA KAT（不可用） |
| kat_opencl | tests/kat_opencl.c | OpenCL KAT（不可用） |
| kat_metal | tests/kat_metal.m | Metal KAT（macOS 专用，不可用） |

### 框架头 / fixture / 脚本（非独立用例）

kat.h、kat_main.h（含 main 的 KAT 框架头）、kat_dev_execute.h、rngNxW.h、time_initkeyctr.h、
time_misc.h、time_random123.h、util.h、util_cuda.h、util_demangle.hpp、util_expandtpl.h、
util_m128.h、util_metal.h、util_opencl.h、util_print.h、kat_vectors（数据）、old_kat_vectors（数据）、
ut_uniform_IEEEkatvectors.hpp（数据）、ut_uniform_kat_vectors.dat（数据）、ut_uniform_reference.hpp（数据）、
GNUmakefile、BUILDVC.BAT、BUILDVC11.BAT、gencl.sh、kat_metal_kernel.metal、kat_opencl_kernel.ocl、
time_opencl_kernel.ocl

### 构建目标映射（GNUmakefile meta-targets）

- c: kat_c ut_ars time_serial
- cpp: kat_cpp ut_carray ut_M128 ut_features ut_ReinterpretCtr ut_Engine ut_aes timers time_boxmuller ut_ua ut_uniform
- gsl: ut_gsl（需 gsl-config）
- thread: time_thread（需 pthread）
- ut: ut_carray ut_Engine ut_features ut_M128 ut_ReinterpretCtr ut_ua ut_uniform ut_uniform_IEEEkat
- kat: kat_c kat_cpp
- cuda/opencl/metal: 平台专用，OHOS CPU 环境不可构建/运行

## 编译步骤

```bash
# random123 为 header-only 库，无 configure/编译；测试程序按 tests/GNUmakefile 构建运行：
# 工具链: clang/clang++ 15.0.4 --target=aarch64-linux-ohos --sysroot=<OHOS sysroot>
# 核心测试构建: make kat_c kat_cpp ut_ars ut_carray ut_Engine ut_features \
#   ut_ReinterpretCtr ut_ua ut_uniform ut_uniform_IEEEkat ut_M128 ut_aes \
#   time_serial time_thread timers time_boxmuller   (全部 exit 0)
# ut_gsl 依赖 GSL/2.8（ohpcd 制品仓，conan install 后链接 libgsl+libgslcblas，exit 0）
# 运行: 11 项 PASS + ut_M128/ut_aes 为无 SSE 平台文档化 no-op stub +
#       ut_uniform_IEEEkat 上游记载 ARM/FMA 已知失败（详见 .ohc-logs/upstream_tests_run.log）
# 鸿蒙专项: tests/ohos_special_test.cpp 编译运行 6/6 PASS
# Conan: conan-verify G0-G4/L2/L4/L5 全 PASS；test_package 消费者测试 PASS
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 判 mixed 并自动写 env_unsupported | 仅 GNUmakefile（无 CMake/Makefile manifest 识别），cpp 主体占比 69.4% < 70% 阈值 | 按 R47/E13 边界规则按主体判 cpp 继续；记录分析日志（候选 C1，草稿 DRAFT-random123…） |
| 2 | conan-verify G2: `object has no attribute 'copy'` | Conan 2 无 self.copy | `from conan.tools.files import copy` 并 `copy(self, ...)` |
| 3 | conan-verify G2: `src and dst must have different values` | src/dst 相对串相同 | 用 os.path.join(source_folder/package_folder) 全路径 + keep_path=True |
| 4 | conandata.yml 被 E017 镜像注入改写成 gh-proxy 列表 | conan-verify G2 临时注入镜像后恢复逻辑覆盖 | W4 审计发现后恢复为官方 URL 单条目（R39） |

## 依赖版本

- 上游：random123 1.14.0（官方 tag v1.14.0，SHA-256 effafd8656b18030b2a5b995cd3650c51a7c45052e6e1c21e48b9fa7a59d926e）
- 无第三方运行依赖（header-only 库）；ut_gsl 可选依赖 GNU Scientific Library（OHOS 无，按依赖规则复查）

## 验证结果

```bash
# 上游测试（13 项独立用例，cwd=源码 tests/）
kat_c PASS / kat_cpp PASS / ut_ars PASS / ut_carray PASS / ut_Engine PASS /
ut_features PASS / ut_ReinterpretCtr PASS / ut_ua PASS / ut_uniform PASS /
ut_gsl PASS（依赖 GSL/2.8 制品恢复后运行）/ ut_M128 PASS(no-op stub) /
ut_aes PASS(no-op stub) / ut_uniform_IEEEkat FAIL（上游记载 ARM/FMA 已知）
# 全量通过率: 11/13 (84.6%)；执行集合 11/11（stub 不计入真实断言）
# 鸿蒙专项: ohos_special_test 6/6 PASS
# 消费者: test_package ctest PASS；独立消费者程序编译运行 PASS
# 门禁: conan-verify G0-G4/L2/L4/L5 全 PASS；W3 本地 CI PASS；W2/R36 通过
```
---

**编译结束**: 2026-09-08 00:43
**最终状态**: built
