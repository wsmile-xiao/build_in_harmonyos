# mmc 1.0 适配笔记

## 软件
- **名称**: mmc (Mesh-based Monte Carlo)
- **版本**: 1.0（上游 tag `v1.0` = "MMC 1.0 Final (v2018 - Sachima)", 2018-08-26）
- **语言**: C（`src/*.c`；`src/mmclab.cpp` 为可选 MATLAB/Octave mex，默认不构建）
- **许可**: GPL-3.0-or-later
- **源码**: <https://github.com/fangq/mmc/archive/refs/tags/v1.0.tar.gz>
- **SHA256**: `e4ff912263074bef983638bafee2f57a8f73468c6cb43888a317c45e64a8b773`

## 编译环境
- 构建系统: make（上游自带 GNU Makefile：`src/Makefile` + `commons/Makefile_common.mk`）
- 编译日期: 2026-09-29
- 编译器: clang 15.0.4 / clang++（target `aarch64-unknown-linux-ohos`，musl libc）
- 平台: HarmonyOS PC (OpenHarmony, aarch64)
- 状态: built

## 编译步骤

```bash
# 上游 Makefile 硬编码 CXX := g++，必须命令行覆盖 CC/CXX
cd src
make CC=clang CXX=clang++ -j1 release     # 产物 src/bin/mmc
```

- **上游默认目标为 `sse`**（`commons/Makefile_common.mk:181` `.DEFAULT_GOAL := sse`），
  会注入 `-DMMC_USE_SSE -DHAVE_SSE2 -msse4`；aarch64 上不可用（见下）。
- 选用上游 `README.txt` 记录的 `release` 目标（"create a single-threaded optimized binary"）。
- `make omp`（OpenMP 多线程）实测亦可编译，但**产物 RUNPATH 指向构建机 SDK 路径**，不可移植。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make`（默认 `sse` 目标）编译失败：`smmintrin.h:14:2: error: "This header is only meant to be used on x86 and x64 architecture"`（20 errors） | `.DEFAULT_GOAL := sse` 注入 x86 专属 `-msse4`/`-DMMC_USE_SSE`，`src/simpmesh.h:40` 随即 `#include <smmintrin.h>` | 改用 `make release`（无 SSE/OpenMP） |
| 2 | `make release` 失败：`simpmesh.h:186:5: error: use of unknown builtin '__builtin_sincosf'` | `mmc_sincosf()` 守卫为 `defined(__GNUC__) && defined(__linux__)`，clang 亦定义 `__GNUC__`/`__linux__`，但 clang 未实现 GCC/ICC 专有内建 `__builtin_sincosf` | 补丁：守卫追加 `&& !defined(__clang__)`，clang 走 `sinf/cosf` 回退分支 |
| 3 | `rngtest_log`（`examples/rngtest/makefile_logistic`）编译失败：`logistic_rand.c:108:80: error: unknown type name 'uint'` | musl libc 不提供 BSD 遗留类型 `uint`（glibc 在 `__USE_MISC` 下提供）；该 RNG 亦为产品 `-DMMC_LOGISTIC` 可选构型 | 补丁：`logistic_rand.{c,h}` 中 5 处 `uint` → `unsigned int` |
| 4 | `make omp` 产物带 `RUNPATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib` | clang `-fopenmp` 会链接 SDK 的 `libomp.so`，并把构建机绝对路径写入 RUNPATH | 不采用 `omp` 构型；`release` 产物仅 `NEEDED libc.so`，可移植 |
| 5 | 上游样例多为 FEM 网格驱动，缺 `node_<id>.dat` 报 `Mesh error: can not open node file` | 网格由 `examples/*/createmesh.m` 用 MATLAB/Octave + iso2mesh（`genT5mesh`/`meshreorient`/`tsearchn`）生成，未随源码发布 | 测试侧用 Python 复现上游 `genT5mesh.m` 纯格点算法生成 node/elem/velem/facenb（面编号约定用随包 `onecube/facenb_onecube.dat` 反推验证，6/6 一致；定向须为**负体积**） |

> 注意：`MESH_ERROR` 仅打印错误，进程仍返回 0；上游 `run_test.sh` 又多用管道（`| sed`），
> 退出码会被 `sed` 覆盖 —— 判定样例成败必须扫描输出内容（`Mesh error` / 产物文件），不能只看 `$?`。

## 源码修改（patches/0001-clang-ohos-portability.patch）

| 文件 | 修改内容 |
|------|----------|
| `src/simpmesh.h` | `mmc_sincosf()` 守卫 `#if defined(__GNUC__) && defined(__linux__)` → 追加 `&& !defined(__clang__)` |
| `src/logistic_rand.c` | 5 处 BSD 类型 `uint` → `unsigned int`（函数签名 2 处、局部变量 1 处、强制转换 2 处） |
| `src/logistic_rand.h` | 2 处函数原型 `uint` → `unsigned int` |

补丁仅改可移植性，不含平台宏（无 `__OHOS__`），不改变算法行为。

## 依赖版本

**强制第三方依赖 = 0**。默认 `release` 构型仅链接 `-lm`（系统 libc）；`src/SFMT`、`src/cjson`、
`src/sse_math`、`src/waitmex` 均为随源码内置。构建工具链：clang/clang++（ohpcd `gcc/9.5.0` 亦可，
本机为 clang 15）、GNU make 4.4.1。

可选构型（默认关闭）：OpenCL（`src/tictoc.c` `#ifdef MCX_OPENCL`，被默认 `-DUSE_OS_TIMER` 关闭）、
CUDA（同处 `#else` 分支）、MATLAB/Octave `mmclab`（`make mex`/`make oct`）。

## 验证结果

```bash
# 1) 编译
cd src && make CC=clang CXX=clang++ -j1 release      # rc=0 -> src/bin/mmc (ELF64 AArch64, NEEDED libc.so)

# 2) 上游样例（examples/）
sh examples/onecube/run_test.sh        # rc=0, 产出 mov.txt/ad.txt
sh examples/reftest/run_test.sh        # rc=0, 产出 mov.txt/ad.txt
sh examples/validation/benchspeed.sh   # rc=0, 100000 光子, ~9.7s, flux 输出
# 3) 上游测试程序
examples/rngtest: rngtest / rngtest_sfmt / rngtest_log  各打印 1000 行随机数，rc=0
src/cjson/test.c: cJSON parse/print 往返，rc=0

# 4) 消费者测试
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 注意事项

- **不要用默认 `make`**：`sse` 目标在 aarch64 必然失败。
- `Makefile` 硬编码 `CXX := g++`，任何环境（含 CI）都必须在命令行覆盖 `CC`/`CXX`。
- 二进制为动态链接（musl），仅依赖 `libc.so`，无 RUNPATH/RPATH。
- 上游 `examples/` 中依赖 MATLAB/iso2mesh 生成网格的样例（colin27、meshtest、replaywide、
  sfdi2layer、widedet 等）在本环境不可直接运行；依赖外部 MCX 程序的 `examples/mcxsph` 同理。
---

**编译结束**: 2026-09-29 00:45
**最终状态**: built
