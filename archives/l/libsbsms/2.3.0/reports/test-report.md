# 测试报告 — libsbsms 2.3.0

> **项目**: libsbsms 2.3.0
> **测试日期**: 2026-09-15
> **测试环境**: HarmonyOS / OpenHarmony PC（HongMeng Kernel），aarch64，clang 15.0.4（OHOS SDK 26.0.0.18）
> **测试类型**: 上游测试套件（无）+ test_package 消费者 API 往返测试（鸿蒙特有）
> **被测 SHA**: `c9c5fb32714eb222b399d53483a386a1654a9e72`（分支 `feat/libsbsms-2.3.0`）
> **验证形态**: 采信轮 = 清缓存干净轮（`tools/conan_verify_round.sh` → `conan-verify`），
> 其后 `finish` 内嵌 W3 本地 CI 模拟；两轮独立构建的 **8 个交付产物与整树逐字节一致**
> （两轮包目录分别取 `…/p/b/libsb698b9c997c655/p` 与 `…/p/b/libsbf2cff71db885c/p`，
> 命令行见 `reports/conan-verify-supplement.md` §5.3）

---

## 一、测试摘要

### 1.1 上游测试（清点口径）

上游 2.3.0 **不随源码提供任何测试**（清点证据逐条见 `upstream-test-inventory.md`：
`tar tzf` 72 项无测试目录、`find . -iname '*test*'` 零命中、`src/` 无 `main()`、
`Makefile.am` 无 `TESTS`/`check-local`、`CMakeLists.txt` 无 `enable_testing()`）。

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 0 | — |
| 通过 (PASS) | 0 | — |
| 失败 (FAIL) | 0 | — |
| 跳过 (SKIP) | 0 | — |
| 未运行 (NOT_RUN) | 0 | — |

上游测试通过率 0/0（上游未提供任何测试入口，N 取源码宏数与框架注册数两个口径的最大值，均为 0）

### 1.2 鸿蒙特有测试（test_package 消费者断言）

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 26 | 100% |
| 通过 (PASS) | 26 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |
| 未运行 (NOT_RUN) | 0 | 0% |

鸿蒙特有测试通过率 26/26（100%）

### 1.3 适配后合计

上游合计 + 鸿蒙行：0 + 26 = 26；通过 26，失败 0。
适配后合计通过率 26/26（100%）

取数命令（`checks=` 行由 `test_sbsms.cpp` 的断言计数器直接打印）：

```console
$ cd archives/l/libsbsms/2.3.0/test_package && ./test_sbsms | tail -2
checks=26 failed=0
RESULT: PASS
```

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。库在 OHOS aarch64 上完成分析+合成的真实往返：以 440 Hz 单音为输入，
identity 组输出主频 439.4 Hz、`pitch x2` 组 879.8 Hz、`rate x2` 组 439.6 Hz，
幅度与能量均在理论值附近，全部输出样本有限（无 NaN/Inf）。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 上游无测试套件 | 无法用上游用例证明功能；改由消费者断言覆盖 | 🟡 |
| 共享库缺 DT_SONAME（适配中已修） | 下游无法按 SONAME 寻址 | 🟢（已修复，见 §四） |

### 2.3 可用功能清单

```
✅ 时间伸缩（Slide/rate）：速率 x2 时输出长度减半且音高保持
✅ 音高平移（Slide/pitch）：x2 时输出频率翻倍
✅ 立体声/多声道接口：SBSMS(channels) 支持 1–2 声道（本次以 mono 实测）
✅ 流式输入接口：SBSMSInterfaceSliding 的 samples() 回调契约
✅ 质量参数：SBSMSQualityStandard（bands=8、H=3、frameSize=384、maxPresamples=19584）
⚠️ 渲染器接口 SBSMSRenderer / renderFrame：未在本次消费者测试中覆盖（无上游用例可依）
❌ 命令行工具：上游不提供（库类型，无 commands.json）
```

### 2.4 已知限制

1. `SBSMS::read()` 输出无限补零、永不返回 0，消费者必须自行按 `getSamplesToOutput()` 停止。
2. 上游 2.3.0 无测试，`N(上游)=0`；功能覆盖完全依赖本归档的 26 条消费者断言，
   未覆盖 `SBSMSRenderer`/`renderFrame` 面。
3. main 分支 `example/` 中的 `SBSMSQualityStandard` 参数表**不适用于 2.3.0**
   （实测直接崩溃），消费者必须使用库自带的 `SBSMSQualityStandard`。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| 出厂 quality 表指纹（bands/H/N[0]/N2[0]/res[0]） | 确认链接到真实的 2.3.0 库 | ✅ PASS |
| `getFrameSize()` / `getMaxPresamples()` | 质量参数派生值 | ✅ PASS |
| `SlideIdentity` 的 `getTotalStretch()` / `getRate()` | Slide 语义 | ✅ PASS |
| identity 往返：长度、有限性、非静音、峰值、主频 | 变速变调核心 | ✅ PASS |
| pitch x2：长度不变、主频翻倍 | 音高平移 | ✅ PASS |
| rate x2：长度减半、主频保持 | 时间伸缩 | ✅ PASS |

逐组实测输出（设备原生构建，`CMAKE_SYSTEM_NAME=OHOS`）：

```console
[1] shipped quality table / API values     bands=8 H=3 N[0]=512 N2[0]=512 res[0]=1
                                           getFrameSize()=384 getMaxPresamples()=19584
[2] identity      want=44100 produced=44160 peak=0.50414 energy=5468.46  estHz=439.402
[3] pitch x2      want=44100 produced=44160 peak=0.50004 energy=5458.03  estHz=879.803
[4] rate  x2      want=22050 produced=22272 peak=0.50004 energy=2728.65  estHz=439.574
checks=26 failed=0
RESULT: PASS
```

同一程序在**采信轮干净轮内**由 Conan 构建并执行，输出与上表一致（见
`reports/conan-create.log` 的 `Testing the package: Executing test` 段第 240–277 行，
即入库转写件 `reports/conan-create-log.md` 的对应围栏块——转写件在块前另有约 17 行表头，
按 `.md` 行号需相应后移；末两行即 `checks=26 failed=0` / `RESULT: PASS`）；W3 侧另有破坏性
反向测试确认该测试真实依赖被测包（`L1e: Negative test confirmed`，见
`reports/w3-local-ci.log` / 入库转写件 `reports/w3-local-ci-log.md`）。

`produced > want` 是预期行为：消费者按 `getFrameSize()=384` 分块读，
`44100` 不足 115 块（`115 × 384 = 44160`），故实际产出向上取整到块边界；
rate x2 组同理（`58 × 384 = 22272`）。

### 3.2 失败的测试

无。

### 3.3 跳过的测试

无（上游无测试可跳过）。

---

## 四、关键问题分析

### 问题1: 共享库无 DT_SONAME（已在配方中修复）

**现象**：

```
System is unknown to cmake, create: Platform/HarmonyOS
$ readelf -d libsbsms.so | grep SONAME
（无输出）
```

**根因分析**：Conan 把 `os=OHOS` 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`，而 CMake
按 `Modules/Platform/<SYSTEM_NAME>.cmake` 查找平台模块，不存在
`Platform/HarmonyOS.cmake`；`CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` 本应由
`Platform/Linux.cmake` 提供，链路断裂后保持未定义，于是 CMake 不向链接器传
`-Wl,-soname`，`SOVERSION`/`VERSION` 被静默丢弃。

**解决方案**：配方 `generate()` 中显式设 `CMAKE_SYSTEM_NAME=OHOS` +
`CMAKE_SYSTEM_PROCESSOR=aarch64`。worker CMake 4.1.2 与 OHOS SDK CMake 3.28
都自带 `Modules/Platform/OHOS.cmake`（全文为 `include(Platform/Linux)`），
平台模块因此被加载。

**修复验证**：

```console
$ readelf -d libsbsms.so | grep SONAME
 0x000000000000000e (SONAME)             Library soname: [libsbsms.so.2]
$ ls -l libsbsms.so*
libsbsms.so -> libsbsms.so.2
libsbsms.so.2 -> libsbsms.so.2.3.0
libsbsms.so.2.3.0
```

同一修复还顺带恢复了 `check_function_exists(lrint)`（未设平台名时只检出
`lrintf`，设 `OHOS` 后 `lrint` 与 `lrintf` 均检出）。

---

## 五、测试环境

```
被测: libsbsms/2.3.0
源码: https://github.com/claytonotey/libsbsms/archive/refs/tags/2.3.0.tar.gz
      sha256 4f88d152bc06fedbda9d5d65517d40254a7310c9050601a93122309d45afd2c9
构建: CMake 4.1.2 + clang/clang++ 15.0.4（OHOS SDK 26.0.0.18）
目标: os=OHOS os.version=6.0 arch=armv8 compiler=clang 15 libc++ cppstd=17 Release
配置: BUILD_SHARED_LIBS=ON, CMAKE_POLICY_VERSION_MINIMUM=3.5,
      CMAKE_SYSTEM_NAME=OHOS, CMAKE_SYSTEM_PROCESSOR=aarch64, CMAKE_INSTALL_LIBDIR=lib
并发: 两轮 Conan 构建均用 Conan 默认并发（`cmake --build … -- -j20`，见 `reports/conan-create-log.md`
      与 `reports/w3-local-ci-log.md` 的 RUN 行、以及生成的 CMakePresets.json 中 `jobs=20`）；
      原生探索构建为 `cmake --build --parallel 2`（`os.cpu_count()=20` 但 `sched_getaffinity`=8、
      `MemFree` 约 0.9 GB，故探索轮显式限并发）
```

---

*报告生成时间: 2026-09-15*
