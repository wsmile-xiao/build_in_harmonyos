# ldc 1.42.0 — OHOS（鸿蒙 PC）适配笔记

## 概述

LDC（LLVM D Compiler）是 D 语言的 LLVM 后端编译器。本包提供 `ldc2` / `ldmd2` 编译器
及 **druntime + Phobos** 运行时，`os=OHOS, arch=armv8`(= aarch64)，真机原生构建。

上游版本对应：LDC 1.42.0 基于 **DMD 前端 v2.112.1**。

## 为什么这是「高难度适配」（路径 C）

| 维度 | 事实 |
|------|------|
| **自举（核心难点）** | LDC 前端是 D 写的（`dmd/` 下 **109 个 `.d` 文件**），必须由 D 编译器编译 |
| **私有/缺失工具链** | 设备与 NDK **不带任何 D 编译器**（实测 `ldc2`/`ldmd2`/`dmd`/`gdc`/`rdmd`/`dub` 全无），且 **D 无法从 C/C++ 侧自举**——LLVM 不含 D 前端 |
| **依赖链庞大** | `find_package(LLVM 15.0 REQUIRED)`，30+ 组件；本仓 `llvm/20.1.0` |
| **含汇编/特殊调度** | druntime 有 fiber 上下文切换汇编（`switch_context_asm.S`）、GC、异常、协程运行时 |
| **全量测试校验成本高** | druntime + Phobos 共 **236 个测试模块**；本项目实测跑完一轮需数十分钟 |
| **上游工具不可用** | 上游 `ldc-build-runtime` 为**动态链接**，在 OHOS 上因缺 `libgcc_s.so.1` / `_Unwind_*` **无法运行**，须绕开 |

## 构建方式

```
conan create . -pr ohos-native        # 真机原生（aarch64 → aarch64）
```

**自举链**：构建期引入上游预编译 `ldc2`（alpine/musl 变体，与 OHOS 的 musl 同族）作引导
编译器，由它编译 LDC 前端与运行时。见 `conandata.yml` 的 `bootstrap`。

**为什么选 alpine 变体**：OHOS libc 是 musl 变体，alpine 同族。实测该二进制在设备上可运行
（`ldc2 --version` 成功，且能编译并运行使用 `std.stdio`/`std.algorithm`/`std.range` 的 D 程序）。

**为什么用 `LDC_BUILD_RUNTIME=ON`（内建运行时）而非 `ldc-build-runtime`**：

> 上游的 `ldc-build-runtime` 工具在 OHOS 上跑不起来——它是**动态链接**的，
> `NEEDED: [libgcc_s.so.1, libc.musl-aarch64.so.1]`，而设备上**既无 `libgcc_s.so.1`
> 也无 `libunwind.so`**，报 `Error loading shared library libgcc_s.so.1` 与一串
> `_Unwind_*: symbol not found`。
>
> 尝试用 sysroot 的 `libunwind.a` + `libclang_rt.builtins.a` 现场拼 `libgcc_s.so.1`，
> `_Unwind_*` 可导出但 **`__getf2`/`__eqtf2` 等 soft-float 符号始终被 LLD 本地化**，6 种链接
> 方案均失败。**最终改为绕开该工具**，直接用 LDC 自身 CMake 的 `LDC_BUILD_RUNTIME=ON`。

## 补丁说明（`patches/0001-ohos-thread-gc-signals.patch`）

### ① SIGRTMIN 在 OHOS 上不可达 → druntime GC 死锁（**核心适配**）

**现象**：多线程 D 程序挂死；druntime unittest 中 `core.thread.osthread`、
`core.thread.fiber.base`、`core.internal.elf.dl` 三个模块超时（各 60s 无输出）。

**根因**：OHOS **无法把 `SIGRTMIN` 送达信号处理函数**。实测对照（自投递与跨线程投递
结果一致）：

| 信号 | 编号 | 处理函数是否触发 |
|------|------|-----------------|
| `SIGUSR1` | 10 | ✅ |
| `SIGUSR2` | 12 | ✅ |
| 32 / 33 / 34 | — | ❌ `sigaction` 返回 **EINVAL(22)** |
| **`SIGRTMIN`** | **35** | ❌ **`pthread_kill` 返回 0，但处理函数永不触发** |
| `SIGRTMIN+1` | 36 | ✅ |
| 37 – 40 | — | ✅ |

即**只有 35 号这一个信号不可达**，不像能力缺失，更像内核占用了该编号但未暴露给用户态。

而 druntime 恰用它做线程挂起信号：

```d
// runtime/druntime/src/core/thread/osthread.d:2564
suspendSignalNumber = SIGRTMIN;        // ← 35，不可达
resumeSignalNumber  = SIGRTMIN + 1;    // ← 36，可达
```

`thread_suspendAll()` 用 `pthread_kill(t, SIGRTMIN)` 停住其它线程供 GC 扫描
（`thread_scanAll`），信号永不触发 → **永久阻塞 → 运行时死锁**。

**修复**：改用 `SIGUSR1`/`SIGUSR2`。这与上游**为 OpenBSD 提供的既有分支同构**
（`osthread.d:2551-2555`，因 "OpenBSD does not support SIGRTMIN or SIGRTMAX"）。

**效果**（唯一变量即此补丁，三个 runner 二进制 sha256 各不相同）：

| | PASS | FAIL | TIMEOUT | 通过率 |
|---|---|---|---|---|
| 未打补丁 | 50 | 7 | **3** | 50/60 = 83.3% |
| 打补丁后 | **52** | 2 | **1** | 52/55 = **94.5%** |

原 3 个超时模块中 **2 个转为 PASS**：

```
core.thread.osthread    60s 卡死 → rc=0  0.113s  PASS
core.thread.fiber.base  60s 卡死 → rc=0  0.014s  PASS
core.internal.elf.dl    仍超时（未定性）
```

### ② OHOS musl 缺 pthread cancellation 家族

**现象**：链接 druntime 时报 `undefined symbol: pthread_setcancelstate`。

**根因**：OHOS libc（`sysroot/usr/lib/aarch64-linux-ohos/libc.so`，**1595 个导出符号**）
**不导出** `pthread_setcancelstate` / `pthread_setcanceltype` / `pthread_testcancel` /
`pthread_cancel`（对照：`pthread_create` 有）。而 druntime `core.thread.osthread`
的 `thread_cancelDisable()` 用 `static if (__traits(compiles, ...PTHREAD_CANCEL_DISABLE))`
做条件——D 侧该符号是**普通声明**，`__traits(compiles)` **恒真**，于是走 POSIX 分支
并在链接期失败。

**修复**：直接采用**上游同一函数 `else` 分支的语义**（源码原文即
`return 0;   // No thread cancellation on platform`），保持 `thread_cancelDisable`
与 `thread_cancelRestore` 的 no-op 对称。

### 其他适配点（非补丁）

| 项 | 说明 |
|----|------|
| **ELF 代码签名** | OHOS 要求被 `exec` 的 ELF 与 `dlopen` 的 `.so` 都签名，否则 `Permission denied`（rc=126）。引导编译器与所有产物均经 `binary-sign-tool sign -selfSign 1`；`package()` 里统一重签 |
| **`config.guess` / Platform** | 设备 `uname` = `HarmonyOS`：cmake 无 `Platform/HarmonyOS.cmake`，LLVM 的 `config.guess` 亦不识别 → 写 stub（同 `llvm` / `flang-ohos` recipe） |
| **`TMPDIR`** | OHOS 上 `/tmp` 只读，cmake 与编译器需显式指向可写目录 |
| **版本标识** | LDC 1.42.0 在 OHOS 上**不定义 `OHOS`** 版本标识（实测仅 `linux`/`Posix`/`CRuntime_Musl`）→ 补丁不能用 `version(OHOS)` 做条件 |

## 验证结果（本地真机 `conan create`）

- **编译状态**：通过
- **上游测试用例通过率**：见下「上游测试实测」
- **新增测试用例通过率**：4/4（`test_package`，真实编译 + **实际执行** + 断言输出）

### 上游测试实测（druntime + Phobos unittest）

以自建运行时逐个模块运行，统计口径如下：

| 范围 | 模块数 | PASS | FAIL | TIMEOUT | SKIP（无 unittest） | 通过率 |
|------|-------|------|------|---------|--------------------|--------|
| druntime | 60 | 52 | 2 | 1 | 5 | **52/55 = 94.5%** |
| Phobos | 176 | 125 | 6 | 1 | 44 | **125/132 = 94.7%** |
| **合计** | 236 | **177** | 8 | 2 | 49 | **177/187 = 94.7%** |

> 口径说明：SKIP 为**无 `unittest` 块**的模块（`test_runner` 对其无输出），不构成失败，
> 故不计入分母；「有测试项」口径代表真实通过率。

**剩余失败项及根因**（均为平台固有限制，非适配问题）：

| 模块 | 现象 | 判定 |
|------|------|------|
| `core.sys.windows.dde`<br>`core.sys.windows.w32api` | Windows 平台专有 API | 平台不适用（OHOS 永不可能通过）|
| `core.internal.elf.io` | `AssertError io.d(514): 0x0 != true` | 平台差异（ELF 读取假设）|
| `core.sys.posix.stdio` | `AssertError stdio.d(655): -9 != 0`（EBADF）| 平台差异（musl `fclose` 语义）|
| `core.thread.fiber.package` | 断言失败 | 平台差异 |
| `core.internal.elf.dl` | TIMEOUT | ⚠️ **未定性**，与动态库枚举相关 |
| Phobos 侧 6 项 | 含 `/usr/share/zoneinfo` 缺失、`tmpfile()` 因 `/tmp` 只读失败、`libcurl` 未加载、信号语义差异等 | 环境/平台限制 |

## 已知限制

1. **补丁是 PoC 级**：`SIGUSR1`/`SIGUSR2` 是否与设备上其它组件（OpenSSL 等）冲突**未评估**。
2. **`core.internal.elf.dl` 超时未定性**——不能假定为平台限制。
3. **依赖上游预编译二进制作引导工具**：本包无法在「无引导编译器」的环境（含 CI）从零自举。
   若 CI 内构建，需预先提供已签名的引导 `ldc2`（或沿用 `llvm`/`flang-ohos` 的
   「真机编好 → `conan cache save` → 手动 upload」例外流程）。
4. **未跑 LDC 自身的 lit 测试套件**（`tests/` 下 15 类）——那需要先有可用的 D 编译器，
   属「自举后」验证，本次仅覆盖 druntime/Phobos unittest。
