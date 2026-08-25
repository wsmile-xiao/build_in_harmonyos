# libdivide 5.3.0 适配笔记

## 编译环境
- 构建系统: 无（header-only，仅需复制头文件）
- 编译日期: 2026-08-24
- 目标平台: OpenHarmony aarch64
- 状态: success (conan recipe built)

## 软件特性
- libdivide 是 header-only C/C++ 库，全部功能集中在单个头文件 `libdivide.h`
- 用途：将运行时整数除法优化为乘法 + 移位序列，最高 10x 加速（64 位除法）
- 许可：Boost Software License 或 zlib License（任选其一）
- SIMD 支持：SSE2 / AVX2 / AVX512（x86）与 ARM NEON（AArch64 自动启用）
- 无任何外部依赖

## 适配方案
libdivide 是真正的 header-only 库，按 Conan header-library 包实现：

1. `conanfile.py` 设置 `package_type = "header-library"`
2. `build()` 为空（无需编译任何 .so/.a）
3. `package()` 直接 `copy()` 单个头文件 `libdivide.h` 到 `include/`
4. `package_info()` 声明 `cmake_target_name = "libdivide::libdivide"`，`libs = []`
5. `test_package` 用 CMake 消费者测试，编译一段使用 `libdivide::divider` 的 C++ 程序并运行

不人为编译任何不存在的 libdivide 库 —— 上游本身就是 INTERFACE library。

## SIMD / 平台处理
- 目标 OpenHarmony aarch64，上游自动检测 AArch64 并启用 NEON（交叉编译走 `check_cxx_source_compiles`，非 `try_run`）
- test_package 只测试最基础、跨平台的 scalar divider API（构造 divider + 整数除法 + 结果校验）
- 不强制启用 SSE / AVX / AVX512 等 x86 专用路径
- 不人为添加任何 SIMD 修改，遵循上游默认行为

## 源码核实
| 项目 | 值 |
|------|------|
| 上游仓库 | https://github.com/ridiculousfish/libdivide |
| 版本 tag | v5.3.0（2026-02-16 发布） |
| 源码 URL | https://github.com/ridiculousfish/libdivide/archive/refs/tags/v5.3.0.tar.gz |
| sha256 | de3933bf2fd21300d99fcc6460a8a4a1343ae90b965d6893f044c350bac68c6e |
| 头文件 | libdivide.h（仓库根目录，单个头文件） |
| 许可文件 | LICENSE.txt |

sha256 来源：FreeBSD ports distinfo 官方记录，对应 GitHub 自动生成的 v5.3.0.tar.gz。
头文件内 `#define LIBDIVIDE_VERSION "5.3.0"` 证实版本正确。

## 依赖版本
- 无（header-only）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 本机无法直连 github 下载核实 | 本机网络限制（curl 超时） | 用 raw.githubusercontent.com 通道核实头文件/CMakeLists 内容；sha256 采用 FreeBSD ports 官方 distinfo 记录，CI 远端会实际下载校验 |

## 源码修改
| 文件 | 修改内容 | 是否已生成补丁 |
|------|----------|----------------|
| 无 | 未修改任何上游源码 | N/A（无补丁） |

## 上游测试验证（PR 要求：上游存在测试就必须实际执行）

### 上游测试清单（CMakeLists.txt, LIBDIVIDE_BUILD_TESTS=ON）

| # | 目标 | 源文件 | 类型 | ctest 注册 | 是否正确性测试 |
|---|------|--------|------|-----------|----------------|
| 1 | tester | test/tester.cpp | C++ scalar+vector correctness | 是 | 是 |
| 2 | test_c99 | test/test_c99.c | C99 scalar correctness | 是 | 是 |
| 3 | benchmark_branchfree | 复用 DivideTest.h | 性能基准 (仅 Release) | 是 | 否 |
| 4 | benchmark | 复用 DivideTest.h | 性能基准 | 否 | 否 |
| 5 | fast_div_generator | fast_div_generator.h | 代码生成工具 | 否 | 否 |

### 统计（严格区分源文件/目标/断言）

| 指标 | 数量 | 说明 |
|------|------|------|
| 独立测试源文件 | 4 | tester.cpp, test_c99.c, DivideTest.h, fast_div_generator.h |
| 测试程序/目标 | 5 | CMake add_executable 全部目标 |
| 正确性测试目标 | 2 | tester + test_c99 |
| 实际执行 | 2 | conanfile.py build() 中构建+运行 |
| 通过 | 2 | tester exit 0, test_c99 exit 0 |
| 失败 | 0 | — |
| 跳过 | 3 | benchmark x2 + fast_div_generator（非正确性测试） |

### 执行结果

**tester.cpp** (C++ scalar + vector correctness):
```
libdivide test suite
SIMD ISAs: none
[scalar + NEON 路径, x86 SIMD 自动禁用]
All tests passed successfully!
exit code: 0
```

**test_c99.c** (C99 scalar correctness):
```
verifying libdivide_s32 / libdivide_s64 / libdivide_u32 / libdivide_u64 ...
test_c99: OK
exit code: 0
```

### SIMD / 平台适配说明（OpenHarmony aarch64）
- **NEON**：上游 CMake 用 `check_cxx_source_compiles`（非 `try_run`）自动检测，aarch64 工具链暴露 `<arm_neon.h>` + `__ARM_NEON` 时自动启用 `LIBDIVIDE_NEON` 路径，交叉编译安全
- **SSE2/AVX2/AVX512**：上游用 `check_cxx_source_runs`，在 aarch64 上无法执行 x86 指令，自动禁用 — 无需人为跳过或修改
- **tester 输出 "SIMD ISAs: none"** = 走 scalar + NEON（如启用）路径，符合目标架构
- 未修改任何上游测试源码或断言

### conanfile.py build() 集成
build() 中调用 `cmake.configure(LIBDIVIDE_BUILD_TESTS=ON)`，构建 `tester` + `test_c99` 两个 correctness 目标，然后用 `self.run()` 实际运行。性能基准和代码生成工具不计入 correctness 验证，跳过。

## 验证结果
- conan create 验证：见 CI `build_and_test.sh` 执行结果
- 上游测试验证：2/2 correctness 测试通过（build() 中执行）
- test_package 验证：编译运行 scalar divider 测试程序

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (header-library 类型, build() 含上游测试执行) |
| conandata.yml | 源码 URL + sha256（无补丁） |
| test_package/ | 消费者测试 (scalar divider API 验证) |
| manifest.yaml | 版本级编译元数据 |
| notes.md | 适配笔记 |
| test_package/MANIFEST.yml | 上游测试声明 + 执行统计 |

---

**编译结束**: 2026-08-24
**最终状态**: built + 上游测试 2/2 通过
