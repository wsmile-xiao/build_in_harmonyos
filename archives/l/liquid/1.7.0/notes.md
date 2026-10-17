# liquid 1.7.0 适配笔记

## 上游信息

- **项目**: liquid-dsp — 软件定义无线电 DSP 库
- **仓库**: https://github.com/jgaeddert/liquid-dsp
- **版本**: v1.7.0
- **许可证**: MIT
- **源码 SHA256**: `33c42ebc2e6088570421e282c6332e899705d42b4f73ebd1212e6a11da714dd4`

## 构建系统

CMake 3.10+，C99 强制，单 shared library 目标（`liquid`）。

## 依赖拓扑

liquid 仅依赖 libc + libm，无强制第三方依赖。

v1.7.0 的 CMakeLists 中 **未集成 FFTW**（`CMakeLists.txt:47` 仅遗留注释
`# TODO: check for FFTW`），既不查找也不链接 FFTW，因此不存在 FFTW 开关，
也无 GPL 许可污染问题。

- **R36**: 不阻塞，零强制外部依赖

## 适配改动

上游 v1.7.0 的 `CMakeLists.txt:14-20` 只声明以下选项，配方仅设置这些真实存在的变量：

| 项 | 上游默认 | 适配后 | 原因 |
|---|---|---|---|
| ENABLE_SIMD | ON | OFF | `cmake/FindSIMD.cmake` 用 `CHECK_C_SOURCE_RUNS()`（`try_run`）探测 SIMD；交叉编译下无法执行 target 探针，构建 host 不可复现 |
| BUILD_AUTOTESTS | ON | OFF | 聚合目标需在构建期运行 `autoscript` 代码生成器并执行 `xautotest`，交叉编译下不可复现；上游测试按 R51 在真机独立执行（见下） |
| BUILD_BENCHMARKS | ON | OFF | 非交付目标 |
| BUILD_EXAMPLES | ON | OFF | 非交付目标 |
| BUILD_SANDBOX | OFF | OFF | 默认即关闭 |
| BUILD_DOC | OFF | OFF | 默认即关闭 |
| COVERAGE | OFF | OFF | 默认即关闭 |

> 说明：`FIND_SIMD`、`FIND_FFTW`、`ENABLE_STRICT` 并非 v1.7.0 的 CMake 选项，
> 传入会触发 CMake `Manually-specified variables were not used by the project`
> 警告，配方与 manifest 均已移除。

## 上游测试（R51 三步法）

### 1. 清点

上游用例数由 `scripts/autoscript.c` 在构建期扫描 CMake `AUTOTESTS` 清单
（`CMakeLists.txt:416-575`，158 个 `*_autotest.c`）生成 `autotest_include.h` 决定：

```
#define NUM_PACKAGES (156)
#define NUM_AUTOSCRIPTS (1317)
```

| 类别 | 项数 |
|------|-----:|
| 纳入 CMake `AUTOTESTS` 聚合、构建期登记并实际执行 | 1317 |
| 源树内但上游 CMake 未登记（`src/buffer/tests/sbuffer_autotest.c`） | 2 |
| `autotest/` 目录库版本自检（`autotest_libliquid`） | 1 |
| **合计** | **1320** |

清点原始输出：`reports/upstream-autotest-1.7.0.md`

### 2. 实际运行（真机，非交叉编译）

在 HarmonyOS aarch64 真机原生构建上游 `xautotest`（`-DBUILD_AUTOTESTS=ON`）并执行：

```bash
ninja xautotest
LD_LIBRARY_PATH=$PWD ./xautotest -o upstream-autotest-1.7.0.json
LD_LIBRARY_PATH=$PWD ctest --output-on-failure
```

### 3. 结果回填

- **上游用例清单 N = 1320**；**聚合登记并执行 N′ = 1317**
- **通过 1317 / 失败 0 / 跳过 0（100%）**，`rc=0`
- 断言检查 `716451` 条全部通过；警告 57 条（均为上游刻意构造的非法配置用例，预期行为）
- 上游 CTest 入口：`1/1` 通过（`test`，127.66s）

完整报告：`reports/upstream-autotest-1.7.0.md`；机器可读结果：`reports/upstream-autotest-1.7.0.json`

## 其他门禁

- L5 SONAME 闸（W3）失败为非阻塞：上游 `SOVERSION=1` 导致包内只有 `libliquid.so`，
  而消费者 `DT_NEEDED` 记录 `libliquid.so.1`；OHOS conanrun 通过 `LD_LIBRARY_PATH`
  注入可正常加载，上游 SONAME 本为 unset（fix 后仍保持默认）
- test_package：L1 链接测试（`test_liquid`）+ 鸿蒙消费者用例（`liquid_ohos_consumer`，
  `resamp_crcf` 端到端）

## 编译结束

时间: 2026-09-23
**编译结束**: 2026-09-23 13:06
**最终状态**: built
