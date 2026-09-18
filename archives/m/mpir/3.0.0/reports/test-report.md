# 测试报告 — mpir 3.0.0 OHOS aarch64

> **项目**: mpir
> **测试日期**: 2026-09-17
> **测试环境**: HarmonyOS PC（OHOS 6.0，aarch64，clang 15，原生构建）
> **测试类型**: 官方测试套件（上游 tests/ make check）+ Conan test_package 消费者测试
> **证据原件**: 本目录 w3-local-ci.log（finish W3 端到端单轮，conan create 全程）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 208 | 100% |
| 通过 (PASS) | 208 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

口径：上游 207 个测试程序（make check，conan shared-only 打包下实际附加集合，
含 C 套件 193 与 C++ 接口套件 14）+ 鸿蒙消费者测试 1 项（test_mpir）。
另有 4 个汇编对拍条件程序（st_fat/st_instrument/st_hamdist/st_popcount）仅在
static+shared 同时启用时编译，shared-only 打包不运行，不计入。

## 二、测试结论

### 2.1 总体评价

✅ **通过**。上游全部 9 个套件 Testsuite summary 均 TOTAL=PASS、FAIL=0、SKIP=0、
ERROR=0；W3 门禁 L0/L1/L4/L5 全部 pass（L2 对纯库包 skip，无 bin/ 产物）。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| mpirxx.h 有符号溢出 UB（已修复，见问题1） | C++ 接口 si 极值运算 | 🟢 已解决 |
| autotools 脚本执行位/HMDFS 权限（已按知识 E490 处理） | 构建期 | 🟢 已解决 |

### 2.3 可用功能清单

```
✅ mpz 任意精度整数运算（乘除回代、阶乘、模运算等 67 项套件全过）
✅ mpq 有理数运算（12 项）
✅ mpf 浮点运算（27 项，含 sqrt）
✅ mpn 底层运算（48 项）、fft（20 项）、rand 随机数（7 项）、misc（3 项）
✅ C++ 接口 libmpirxx（14 项，含 t-ops 极值混合运算）
✅ 消费者视角：test_mpir 链接 mpir::mpir 并断言通过（含 LONG_MIN 回归）
```

### 2.4 已知限制

1. aarch64 走 mpn/generic C 路径（上游无 arm64 汇编），性能低于带汇编优化的
   GMP 6；语义一致性由 207 项上游测试保证。
2. 上游 2017 年后停止维护（3.0.0 为最终发布版本）。

## 三、测试详情

### 3.1 通过的测试（按套件，Testsuite summary 实数）

| 套件 | 通过/总数 | 结果 |
|--------|------|------|
| tests 顶层 t-* | 9/9 | ✅ PASS |
| tests/mpn | 48/48 | ✅ PASS |
| tests/fft | 20/20 | ✅ PASS |
| tests/mpz | 67/67 | ✅ PASS |
| tests/mpq | 12/12 | ✅ PASS |
| tests/mpf | 27/27 | ✅ PASS |
| tests/misc | 3/3 | ✅ PASS |
| tests/rand | 7/7 | ✅ PASS |
| tests/cxx | 14/14 | ✅ PASS |
| test_package test_mpir（鸿蒙消费者） | 1/1 | ✅ PASS |

取数命令：`grep -A6 "Testsuite summary" w3-local-ci.log`、
`grep -c "^PASS" w3-local-ci.log`（207）、`test_mpir: all checks passed`。

### 3.2 失败的测试

无。

### 3.3 跳过的测试

无（st_* 4 项条件程序未编译属打包配置口径，非跳过，见上文说明）。

## 四、关键问题分析

### 问题1: tests/cxx/t-ops 极值断言失败（已修复）

**现象**：
```
t-ops.cc:187: GNU MP assertion failed: c == -1
```

**根因分析**：
mpirxx.h 的 __gmpxx_abs_ui / __mpz_set_si_safe 及各运算 si 版 eval 中
`static_cast<mpir_ui>(-l)` 与裸 `-l` 对 mpir_si 最小值（LONG_MIN）是有符号
溢出 UB；clang -O2 常量折叠出垃圾值（探针实测 abs 得 0x5a0a409bc0，
LONG_MIN / 2^63 得 0 而非 -1）。

**解决方案**：
0001 补丁统一改为 `- static_cast<mpir_ui>(l)`（无符号取负，模 2^64 可整除
语义），移植 GMP gmpxx.h 同类修复；补丁后 t-ops 及 cxx 套件 14/14 通过，
并纳入 test_package 消费者回归。

### 问题2: HMDFS 上 autotools 构建环境（已按知识库处理）

**现象**：autoreconf 重新生成的 configure 中 config.status 以
`umask 077 && mktemp -d` 建 0700 临时目录后写入失败（Permission denied）；
profile 的 CONFIG_SHELL（hnp bash）job-control getcwd 偶发失败。

**根因分析**：HMDFS/SELinux 对权限与 getcwd 的平台限制（知识 E490/E011 同族）。

**解决方案**：自举后统一 umask 077→022；配方按 E490 恢复 autotools 辅助脚本
执行位；CONFIG_SHELL 经 recipe buildenv 覆盖为系统 /bin/sh（conanbuildenv
最后加载，覆盖生效）。
