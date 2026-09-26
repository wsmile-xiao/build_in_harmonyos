# liquid 1.7.0 上游测试验证报告（R51 三步法）

> **项目**: liquid-dsp（归档名 `liquid`）
> **上游版本**: v1.7.0（tag `v1.7.0`）
> **验证日期**: 2026-09-25
> **验证环境**: HarmonyOS / HongMeng Kernel 1.12.0，aarch64（musl），真机原生构建执行
> **测试对象**: 上游官方测试套件（CMake `BUILD_AUTOTESTS` → `xautotest` 聚合程序 + CTest）
> **源码校验**: `33c42ebc2e6088570421e282c6332e899705d42b4f73ebd1212e6a11da714dd4`（与 `conandata.yml` 一致）

---

## 一、第 1 步：上游测试用例清点

上游 v1.7.0 的用例数由**上游自带的 `scripts/autoscript.c`** 在构建期扫描 CMake
`AUTOTESTS` 清单（`CMakeLists.txt:416-575`，158 个 `*_autotest.c`）生成
`autotest_include.h` 的 `NUM_AUTOSCRIPTS` 宏决定，即 CTest 聚合入口实际执行的用例条数。

### 1.1 清点原始输出

```bash
$ grep -n '^option(' CMakeLists.txt
14:option(BUILD_EXAMPLES   "Set to ON to build examples"           ON)
15:option(BUILD_AUTOTESTS  "Set to ON to build autotest program"   ON)
16:option(BUILD_BENCHMARKS "Set to ON to build benchmark program"  ON)
17:option(ENABLE_SIMD      "Set to ON to build SIMD extensions"    ON)
18:option(BUILD_SANDBOX    "Set to ON to build sandbox programs"   OFF)
19:option(BUILD_DOC        "Set to ON to build documentation"      OFF)
20:option(COVERAGE         "Set to ON to build with code coverage" OFF)

$ grep -n 'set(AUTOTESTS' CMakeLists.txt
416:set(AUTOTESTS

$ # CMakeLists.txt:697 构建期由上游 scripts/autoscript.c 扫描 AUTOTESTS 生成：
$ autoscript / autotest ${AUTOTESTS} > autotest_include.h
#define NUM_PACKAGES (156)
#define NUM_AUTOSCRIPTS (1317)

$ find src -path '*/tests/*.c' -not -path '*/data/*' | wc -l    # 测试源文件(非 data)
163

$ grep -rho '^void autotest_' src --include=*.c | wc -l          # 源树内用例函数
1318

$ grep -rho '^void autotest_' . --include=*.c | wc -l            # 全树(含 autotest/ 目录)
1321

$ grep -rn '^void autotest_' autotest/*.c                       # autotest/ 目录明细
autotest/autotest.c:120:void autotest_print_results(void)
autotest/libliquid_autotest.c:27:void autotest_libliquid()
autotest/null_autotest.c:25:void autotest_null()
```

### 1.2 用例清单汇总（合计 1320 项）

| 类别 | 项数 | 证据 |
|------|-----:|------|
| 纳入 CMake `AUTOTESTS` 聚合、构建期登记并实际执行 | 1317 | `autotest_include.h: NUM_AUTOSCRIPTS = 1317`；`NUM_PACKAGES = 156` |
| 源树内存在但上游 CMake 未登记 | 2 | `src/buffer/tests/sbuffer_autotest.c`（同目录 `cbuffer`/`wdelay`/`buffer_window` 已登记） |
| `autotest/` 目录内的库版本自检用例 | 1 | `autotest/libliquid_autotest.c:27 → autotest_libliquid()` |
| **合计** | **1320** | 框架函数 `autotest/autotest.c:120 → autotest_print_results()` 不计入用例 |

> 校验等式：1317（聚合登记，含 `autotest_null`）+ 2（未登记的 `sbuffer_autotest.c`）
> + 1（`autotest_libliquid`）= 1320。

---

## 二、第 2 步：在可运行环境实际执行

构建期运行 `autoscript` 需要执行 target 代码，交叉编译下不可用；本报告在
**HarmonyOS aarch64 真机**上原生构建上游 `xautotest` 并实际执行，属 R51 要求的
「可运行环境实际运行（真机/CI）」。

### 2.1 配置与构建

```bash
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_AUTOTESTS=ON -DBUILD_BENCHMARKS=OFF -DBUILD_EXAMPLES=OFF \
  -DBUILD_SANDBOX=OFF -DBUILD_DOC=OFF -DENABLE_SIMD=OFF -DCOVERAGE=OFF
ninja xautotest
```

```bash
$ file xautotest
xautotest: ELF 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

### 2.2 执行上游聚合程序

```bash
$ LD_LIBRARY_PATH=$PWD ./xautotest -o upstream-autotest-1.7.0.json
```

原始输出（末尾）：

```
autotest seed: 1790338242
==================================
 WARNINGS : 57
==================================
 PASSED ALL 716451 CHECKS
==================================
output JSON results written to upstream-autotest-1.7.0.json
```

### 2.3 执行上游 CTest 入口

```bash
$ LD_LIBRARY_PATH=$PWD ctest --output-on-failure
Test project build-ohos
    Start 1: test
1/1 Test #1: test .............................   Passed  127.66 sec

100% tests passed, 0 tests failed out of 1

Total Test time (real) = 127.68 sec
```

---

## 三、第 3 步：测试结果回填

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游用例清单（申报 N） | 1320 | 100% |
| 实际执行用例数（聚合登记 N′） | 1317 | 100% |
| 通过 (PASS) | 1317 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |
| 断言检查数（`num_checks`） | 716451 | 100% |
| 警告（`num_warnings`） | 57 | — |

**核心功能通过率**: ✅ **100%**（1317/1317，`rc=0`）

机器可读结果：`upstream-autotest-1.7.0.json`（`pass: true`、`num_failed: 0`、
`num_checks: 716451`、`num_warnings: 57`、`run-mode: RUN_ALL`，
`tests` 数组 1317 条全部 `pass`）。

---

## 四、结论与说明

### 4.1 总体评价

✅ **上游 v1.7.0 官方测试套件在 HarmonyOS aarch64 上全量通过**
（1317/1317 用例、716451 条断言、0 失败、`rc=0`）。

### 4.2 关于 57 条警告

57 条 warning 全部来自上游**刻意构造的非法配置用例**（例如
`agc_crcf_set_bandwidth()` 传入非正带宽、`cvsd_create()` 传入非法位宽），
用于验证入参校验路径按预期报错；上游测试自身打印
`warning: ignore potential errors here; checking for invalid configurations`
予以标注。这属于**预期行为，非缺陷**，全部 57 条对应用例均为 `pass: true`。

### 4.3 为什么上游测试不在 conan 包内执行

上游 `CMakeLists.txt:697` 在构建期**执行** `autoscript` 生成 `autotest_include.h`，
并在 `xautotest` 构建完成后由 CTest 运行。交叉编译产出的 target 二进制无法在构建
host 上执行，因此 conan 配方关闭 `BUILD_AUTOTESTS` 以保持构建可复现。

这**不等于跳过或缩圈上游测试**：上游测试按 R51 在真机全量实跑，实测值已如实回填
（`notes.md` 申报表 + 本报告 + JSON 结果）。

### 4.4 SIMD 探测在交叉编译下的行为（已实测）

`cmake/FindSIMD.cmake:101` 使用 `CHECK_C_SOURCE_RUNS()`（即 `try_run`）探测 SIMD 支持。
交叉编译模式下 CMake 实测输出：

```
CMake Error: try_run() invoked in cross-compiling mode, please set the following cache variables appropriately:
FOO_CODE=PLEASE_FILL_OUT-FAILED_TO_RUN
```

即探测值退化为占位符、SIMD 结论不可用，故配方显式设置 `ENABLE_SIMD=OFF`
（`CMakeLists.txt:269` 的 `if (C_NEON_FOUND AND ENABLE_SIMD)` 分支因此不启用）。

### 4.5 已知限制

1. SIMD 优化关闭：交叉编译下 SIMD 探测不可用，DSP 运算使用通用 C 实现，性能低于
   SIMD 优化版本。本报告的真机原生构建中 `try_run` 可正常执行、`autoscript` 亦正常生成，
   说明该限制源于构建方式而非平台能力。
2. 上游 3 项未纳入聚合的用例（`sbuffer_autotest.c` 2 项 + `autotest_libliquid` 1 项）
   不在上游 CTest 聚合执行范围内，随上游原样保留、未做修改。

---

## 五、验证环境

```
OS       : HarmonyOS / HongMeng Kernel 1.12.0 #1 SMP aarch64 (Toybox)
Toolchain: clang 15.0.4 (Target: aarch64-unknown-linux-ohos)
CMake    : 4.1.2    Generator: Ninja
Runtime  : /lib/ld-musl-aarch64.so.1
源码      : https://github.com/jgaeddert/liquid-dsp/archive/refs/tags/v1.7.0.tar.gz
SHA256   : 33c42ebc2e6088570421e282c6332e899705d42b4f73ebd1212e6a11da714dd4
```

### 复现命令

```bash
curl -sSL -o v1.7.0.tar.gz https://github.com/jgaeddert/liquid-dsp/archive/refs/tags/v1.7.0.tar.gz
tar xzf v1.7.0.tar.gz && cd liquid-dsp-1.7.0 && mkdir build && cd build
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_AUTOTESTS=ON \
  -DBUILD_BENCHMARKS=OFF -DBUILD_EXAMPLES=OFF -DBUILD_SANDBOX=OFF \
  -DBUILD_DOC=OFF -DENABLE_SIMD=OFF -DCOVERAGE=OFF
ninja xautotest
LD_LIBRARY_PATH=$PWD ./xautotest -o upstream-autotest-1.7.0.json
LD_LIBRARY_PATH=$PWD ctest --output-on-failure
```

---

*报告生成时间: 2026-09-25*
