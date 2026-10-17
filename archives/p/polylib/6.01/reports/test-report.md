# polylib 6.01 测试报告

> **项目**: polylib 6.01（PolyLib，IRISA 多面体运算库）
> **测试日期**: 2026-09-18
> **测试环境**: HarmonyOS 设备（aarch64-linux-ohos，clang 15.0.4），ohos-aarch64 profile（Conan 2.29.1）
> **测试类型**: 上游回归套件（`make -C Test check`）+ 消费者测试（test_package）

---

## 一、测试摘要

计数单位：上游「用例」＝ `Test/<子目录>` 的一个 `.in` 输入在某整数表示（32 位、64 位、gmp）
下与仓库内 `.out` 基线 diff 的一次执行；上游对三套整数表示各注册一遍，故注册用例合计 426。
消费者测试按**程序**计（2 个 test_package 程序，含 10 项断言），不计入上游分母。
程序数、用例数、断言数不混加。

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游用例合计 | 426 | 100%（分母） |
| 通过 (PASS) | 426 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |
| 鸿蒙特有消费者测试程序 | 2（10 项断言全过） | 100% |

**上游测试通过率**: 426/426（100%）；**消费者测试通过率**: 2/2（100%，10/10 项断言）

分整数表示的明细（实测）：32 位 134 例、64 位 146 例、gmp 146 例。

---

## 二、测试结论

### 2.1 总体评价

✅ 上游回归套件在适配后于设备原生 aarch64-linux-ohos 环境全量通过；
三种整数表示的库（32 位、64 位、gmp）均编译、链接、运行正常；CLI 工具可执行。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| HMDFS 上 autoconf `config.status` 临时目录不可写（E011/E136） | 阻塞配置阶段 | 🟡（已修复：0003 补丁） |
| NDEBUG 下 pthread 异常栈不初始化（上游代码缺陷） | 回归在首个用例目录即中止（71 次执行全部崩溃、68 例 diff 失败） | 🟡（已修复：0004 补丁） |
| 发布包 config.guess/config.sub 无 HarmonyOS 支持（E007） | 阻塞配置阶段 | 🟡（已修复：0001/0002 补丁） |
| 设备 hnp bash 在 Conan 构建目录内 getcwd 失效（E386） | 阻塞配置阶段 | 🟡（配方按 E232/E386 走能力探针 shell） |

### 2.3 可用功能清单

```
✅ 32 位 / 64 位 / gmp 三种整数表示库（默认 `shared=False` 静态交付；`-o polylib/*:shared=True` 可构建共享 `*.so.10`）
✅ 20 个命令行工具（c2p、r2p、findv、pp{32,64,gmp}、ehrhart_*、disjoint_union_* 等）
✅ 公共头文件与 polylibgmp.pc（pkg-config）
✅ 上游回归套件 426 例（Lattice、Zpolytope、Ehrhart、参数化多面体分解等）全部通过
```

### 2.4 已知限制

1. pkg-config 只安装 `polylibgmp.pc`（上游行为：只为主变体生成 .pc 文件）。
2. `Test/ehrhart` 的 `longtest` 为可选长测试，不在默认测试入口内，未计入注册用例。
3. 库内部多线程安全依赖 pthread（构建时 `-DTHREAD_SAFE_POLYLIB`，configure 自动探测成功）。

---

## 三、测试详情

### 3.1 上游测试（设备原生 aarch64 实跑）

入口：`make -C Test check`（顶层 `make check` 只有 `check: all`，不运行用例）。

| 测试目录 | 32 位 | 64 位 | gmp | 说明 |
|----------|------:|------:|----:|------|
| Zpolytest | 71 | 78 | 78 | 格（Lattice）与多面体核心运算 |
| general | 14 | 14 | 14 | 多面体通用运算（polytest） |
| pp | 8 | 8 | 8 | 参数化多面体分解 |
| ehrhart | 38 | 43 | 43 | Ehrhart 多项式（64 位专有 5 例） |
| ehrhart_union | 2 | 2 | 2 | 多面体并集的 Ehrhart 计数 |
| ranking | 1 | 1 | 1 | 顶点排序 |
| **合计** | **134** | **146** | **146** | **426 全部 PASS，0 FAIL 0 SKIP** |

原始日志（逐字副本，含哈希）：`task-data/polylib-6.01/evidence/device-native/explore-6-testcheck.log`
（sha256 `98edc7dfa7f012b99622bf49c8869ca845cda878c71e548277cc12dbf4966f0c`）。

NDEBUG 对照实验（证明 0004 补丁必要）：

| 构建 | 结果 | 日志 |
|------|------|------|
| 无 NDEBUG（默认 configure） | 426/426 通过 | explore-6-testcheck.log |
| `CFLAGS=-g -O2 -DNDEBUG`（未打 0004） | 71 次执行全部崩溃、68 例 diff 失败（首个用例目录中止） | explore-9-testcheck-ndebug.log |
| `CFLAGS=-g -O2 -DNDEBUG`（打 0004 后） | 426/426 通过 | explore-13-testcheck-ndebug-fixed.log |

### 3.2 消费者测试（test_package，随 conan create 运行）

| 测试 | 断言 | 结果 |
|------|------|------|
| `test_polylib.c`（C API） | 6 项：dimension=2、4 facets、无隐式等式、4 顶点/射线、约束往返 4 facets、往返列宽 | ✅ PASS |
| `test_c2p.sh`（CLI） | 4 项：Dimension:2、Constraints/Equations/Rays/Lines 计数、顶点 (0,0)、顶点 (1,1) | ✅ PASS |

配方级 `conan create` 实跑（设备，默认 `shared=False`）：

```
$ conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
（库与 20 个 CLI 工具编译安装；上游回归 426/426）
polylib/6.01 (test package): Running test()
1/1 Test #1: test_polylib .....................   Passed    0.07 sec
100% tests passed, 0 tests failed out of 1
polylib/6.01 (test package): RUN: /system/bin/sh ".../test_c2p.sh" ".../bin/c2p" ".../square.in"
OK: c2p produced the expected unit-square polyhedron
```

原始日志：`task-data/polylib-6.01/evidence/device-native/conan-create-pre-validation.log`
（sha256 `18286a8de6559e33569b89c3a2a2df439cf5bc666fc5a69933fb2dc94259e481`）。

设备人工复核（静态与共享两种链接方式）：消费者测试程序在探索构建产物上分别以静态
（`libpolylibgmp.a`）与共享（`libpolylibgmp.so.10`）链接编译并运行，两种方式均 6/6 断言通过；
日志 `evidence/device-native/consumer-static-shared-run.log`（含两次运行的 stdout 与 exit=0）。

### 3.3 失败的测试

无。

### 3.4 跳过的测试

上游用例 0 SKIP。W3（本地 CI 模拟）中的非阻断警示如实披露如下：

| 项目 | 结论 | 说明 |
|------|------|------|
| L2 smoke（--version/--help） | skip（非阻塞） | PolyLib CLI 工具不解析 `--version/--help`，均为 stdin 交互程序；CLI 的真实功能由消费者测试 `test_c2p.sh` 覆 盖 |
| L4 危险函数扫描 | warn（非阻塞） | 扫描列出的文件是 `0001-config.guess.patch`：纯文本正则（`strcpy/sprintf/gets/strcat`）命中了补丁上下文注释中的 `targets`（子串 `gets`），属已知文本扫描假阳性；四个补丁不含危险函数调用 |
| 上游测试 | L1 pass | W3 日志 `L1_RESULT=pass: upstream tests + test_package executed`；L1e 破坏性负测试确认 test_package 真实依赖被测包 |

---

## 四、关键问题分析

### 问题1: config.status 临时目录在 HMDFS 上不可写（已修复）

**现象**：`./config.status[1025]: can't create ./confy6mA13/subs1.awk: Permission denied` →
`config.status: error: could not setup config files machinery`。

**根因**：autoconf 以 `umask 077` 创建 `./confXXXXXX` 私有目录；HMDFS 上该目录对创建者不可写（E011/E136）。

**解决方案**：0003 补丁将 configure 内两处 `umask 077` 改为 `umask 022`（与仓库内 adns/aespipe/barvinok
先例一致），配置随即成功。

### 问题2: NDEBUG 下回归全量失败（已修复）

**现象**：Conan Release 构建（`-DNDEBUG`）后，上游回归在首个用例目录即中止：71 次执行全部崩溃、68 例 diff 失败（崩溃后输出截断而非全空）。

**根因**：`source/arith/errors.c` 把 `pthread_once`/`pthread_setspecific` 放在 `assert()` 副作用中；
NDEBUG 下这些调用被编译掉，TLS 异常栈永不初始化（上游代码缺陷，非平台专属）。

**解决方案**：0004 补丁将 6 处 assert 副作用显式化为 `if (...) abort()`；NDEBUG 下复测 426/426 通过。
barvinok 0.41.9 内嵌 PolyLib 5.22.5 使用同一修复，互为佐证。

### 问题3: config.guess 老式脚本与官方补丁脚本不匹配（已修复）

**现象**：`./config.guess` 报 `unable to guess system type`；官方 `patch-autotools-ohos.pl` 输出
`HarmonyOS=1` 但脚本仍失败。

**根因**：6.01 自带 config.guess 为 2018-02-24 老式 echo 风格，官方脚本插入的是新版 GUESS 变量风格分支，
赋值后无人输出（grep 校验因此假通过）。

**解决方案**：0001 补丁按文件自身风格重写该分支（`echo "$UNAME_MACHINE"-unknown-linux-ohos; exit`），
并补 `__OHOS__` libc 探针；consolidated 验证 `./config.guess` → `aarch64-unknown-linux-ohos`。

---

## 五、测试环境

```
polylib 6.01（官方 tarball，sha256 ba2f42aa…，与 AUR polylib 6.01 打包校验和一致）
构建: autotools（发布包自带 configure）/ conan 2.29.1 / clang 15.0.4（OHOS aarch64）
profile: ci/conan/profiles/ohos-aarch64（os=OHOS 6.0, arch=armv8, Release）
依赖: gmp/6.3.0.1（OHOS profile binary 01d92cf3…）
补丁: 0001 config.guess（HarmonyOS 三元组）、0002 config.sub（linux-ohos）、
      0003 configure（umask 022）、0004 errors.c（NDEBUG 下异常栈初始化）
测试入口: make -C Test check（上游）；conan create 的 test_package（消费者）
```

---

*报告生成时间: 2026-09-18*
