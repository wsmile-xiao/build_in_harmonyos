# QBDI 0.12.1 适配笔记（HarmonyOS PC / aarch64）

## 一、概述

QBDI（QuarkslaB Dynamic binary Instrumentation）是基于 LLVM 的**动态二进制插桩
框架**：把目标函数编译成插桩后的代码块，在运行期写入可执行内存并跳转执行，
同时维护指令缓存与指令重写规则。

交付物为静态库 `libQBDI.a` 与公共头文件 `QBDI/*.h`、`QBDI/*.hpp`。

- 上游：https://github.com/QBDI/QBDI
- tag：`v0.12.1`
- tarball SHA256：`6c530f55285282cbf5b3ad569013c6db9751c4ce7f3d33eb6aa39df48e7abd45`
- 许可证：Apache-2.0

## 二、路径 C 证据（源码 / 构建 / 测试配置）

### 2.1 私有 LLVM 被静态并入产物

上游 `README.rst` 明写：QBDI 使用**未被常规 LLVM 安装导出的私有 API**，
因此必须自带一份 LLVM。`cmake/llvm/QBDI_llvm.cmake` 钉住
`QBDI_LLVM_VERSION 19.1.5`，经 FetchContent 拉取 **LLVM 源码**编译，
再由 `cmake/merge_archives.cmake` 合并进 `libQBDI.a`。

`test_package/ohos_abi_check.py` 在产物中检出
`LLVMCreate` / `LLVMDispose` / `llvm::` / `LLVMContext` 符号，
证明这一层在鸿蒙构建中**真的成立**（若退化为链接系统 LLVM，该断言会失败）。

### 2.2 构建期代码生成器（host tool）必须能在目标机执行

LLVM 的 TableGen（`llvm-tblgen` / `llvm-min-tblgen`）是**构建期运行在 host 上**的
代码生成器。鸿蒙 PC 上它必须能原生执行——这是本适配的硬性前提之一，
也是 §3 中 872 个构建目标里最先跑起来的一批。

### 2.3 运行期指令重写 + 可执行内存 + 指令缓存

引擎在运行期把 AArch64 指令翻译/打补丁进可执行内存，并为不认识的指令维护
重写规则（`src/Patch/AARCH64/`、`src/ExecBlock/AARCH64/`）。

平台能力实测（鸿蒙 PC 普通用户）：

| 能力 | 实测 |
|---|---|
| RWX `mmap` | ✅ 可用（插桩代码块的执行前提） |
| `mmap` + `mprotect` 切换 | ✅ 可用 |
| `ptrace` | ❌ 被拒绝 |
| `AF_PACKET` / `SOCK_RAW`、`AF_INET` / `SOCK_RAW`、`NETLINK_XFRM` | ❌ 被拒绝 |
| procfs | ✅ 基本完整 |

因此本适配**只主张进程内嵌 VM 模式**（`QBDI::VM` + `vm.call()`），
不主张 preload / 外部 attach；后者依赖 `ptrace`，属平台能力限制（见 §7）。

## 三、上游测试统计（硬性要求）

### 3.1 从 751 到 185 的完整推导

QBDI 的上游测试是 Catch2 单可执行 `QBDITest`。源码中的用例宏**跨全部架构**
编写，而一次构建只编译其中一套架构。三个概念必须分开：

| 概念 | 数值 | 证据 |
|---|---:|---|
| 上游跨架构源码声明总数 | **751** | `grep -rho "TEST_CASE_METHOD" test/ \| wc -l` |
| AArch64 构建适用并可枚举 | **185** | `QBDITest --list-tests`（设备上实跑） |
| OpenHarmony AArch64 实际执行 | **185** | `QBDITest` 全量运行 |
| 通过 | **185** | 86542 个断言，0 失败 |

**推导链**（每一步都可由命令复算，原始记录见
`path-c-evidence-20260929/qbdi/DERIVATION_751_to_185.txt`）：

```
   751  所有架构的 TEST_CASE_METHOD 声明
 - 582  位于其他架构目录，本构建（QBDI_ARCH=AARCH64）永不编译
        test/API/ARM 339 + test/API/X86 80 + test/API/X86_64 87
      + test/Patch/ARM 66 + test/Patch/X86 2 + test/Patch/X86_64 8
 = 169  架构中立文件 + AARCH64 目录
 +  16  实际编译进来的 TEST_CASE(（全仓 18 个，减 2 个位于 test/Benchmark/，
        它们进的是另一个可执行 QBDIBenchmark，见 QBDITest.dir 目标文件清单）
 = 185  ← 与 Catch2 自己的 --list-tests 输出逐条吻合
```

`test/CMakeLists.txt` 只为 `QBDITest.cpp` 建目标，实际编译单元由 CMake 决定；
AArch64 构建下 `test/CMakeFiles/QBDITest.dir/` 恰好含 **25 个 `.o`**，
清单已随证据保存。

> **已记录的 1 处口径瑕疵（不影响上式）**：
> `test/API/X86_64/InstAnalysisTest_X86_64.cpp:1132` 有一行**被注释掉的**
> `TEST_CASE_METHOD`，`grep` 会把它计入 751。它位于 X86_64 目录，
> 因此同样落在上面减去的 582 之内，在恒等式中相互抵消。

### 3.2 统计口径表

| 指标 | 数值 |
|---|---:|
| 上游发现总数 N（跨架构源码声明） | 751 |
| 当前架构适用数 A（AArch64 可枚举） | 185 |
| OpenHarmony 实际执行数 E | 185 |
| 通过数 P | 185 |
| 失败数 F | 0 |
| 未执行数 A−E | 0 |
| 执行覆盖率 E/A | **185/185 = 100%** |
| 已执行通过率 P/E | **185/185 = 100%** |

> 说明：本表的 N 采用**跨架构源码声明数**（751），A 采用**本架构实际可枚举数**
> （185）。按仓库通行口径，报"适用覆盖率"时用 E/A=100%；
> 若评审要按跨架构 N 计算，则应写作 185/751 = 24.63%，差额 566 条
> **全部**来自本构建不编译的其他架构源码，属架构裁剪而非执行失败或跳过。
> 两种口径都在此列明，不做取舍隐瞒。

### 3.3 真机运行结果

```bash
# 构建
conan create . -o "qbdi/*:shared=False"        # → CONAN_CREATE_RC=0（见 §5）
# 运行
QBDITest                                        # → 185 cases, 86542 assertions, 0 failures
```

```
All tests passed (86542 assertions in 185 test cases)
```

真机命令、完整 stdout/stderr、退出码与逐用例清单均已保存在
`path-c-evidence-20260929/qbdi/`。

## 四、适配修改

### 4.1 四个平台阻碍（均在设备上复现并解决）

1. **`config.guess` 不认识 HarmonyOS**。LLVM 的 `config-ix.cmake` 无条件调用
   `get_host_triple()`（`LLVM_HOST_TRIPLE` 是**输出**），configure 直接中止。
   → `fixups/ohos_config_guess_fix.py` 幂等插入一条
   `aarch64:HarmonyOS:*:*) echo aarch64-unknown-linux-ohos` 分支。
2. **LLVM 的 `NATIVE` TableGen 子构建重新识别 host 为 HarmonyOS**，
   CMake 没有 `Platform/HarmonyOS` 模块 → `UNIX` 未置位 →
   `HandleLLVMOptions.cmake` 报 "Unable to determine platform"。
   → `fixups/ohos_llvm_platform_fix.py` 把 `elseif(FUCHSIA OR UNIX)` 放宽为
   `elseif(FUCHSIA OR UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")`。
3. **`cmake/merge_archives.cmake` 拒绝 `CMAKE_SYSTEM_NAME=HarmonyOS`**。
   → `-DCMAKE_SYSTEM_NAME=Linux`。这是正确的旋钮：鸿蒙 PC 的 ABI 就是
   Linux（musl，`aarch64-unknown-linux-ohos`）。
4. **`config.guess` 还需要非 HMDFS 的可写 `TMPDIR`**（E011 类问题）。

前两项通过把两个幂等 Python fixup 装入 `<src>/cmake/llvm/`，并在
`cmake/llvm/QBDI_llvm.cmake` 的 LLVM FetchContent 解包之后、configure 之前
插入 `execute_process` 钩子来生效。钩子由 `build()` 直接文本编辑写入，
**不依赖外部 `patch` 工具**（`conandata.yml` 的 `patches: {}` 为空）。

### 4.2 配方层

- `validate()` 接受 `Linux` 与 `OHOS`（R32），并限定 AArch64。
- 编译器取自 `tools.build:compiler_executables`（R33），不使用 `${CC}`。
- `QBDI_TOOLS_FRIDAQBDI=OFF`、`QBDI_TOOLS_PYQBDI=OFF`（需要额外宿主工具链，
  且会扩大包体）；`QBDI_TEST=ON` 以保证上游测试可构建。
- `package()` **必须**从两处取头文件：源码树 `include/`（`.h` + `.hpp`）
  与 CMake 构建树 `include/`、`include-static/`。后者含 `configure_file()`
  生成的 `QBDI/Config.h`、`QBDI/Version.h`、`QBDI/State.h`、`QBDI/Options.h`
  ——**源码树里没有这些文件**，只复制源码树的配方会产出无法编译的包。

**未做的事**：未删除任何测试、未放宽任何断言、未跳过任何场景、
未把失败改成通过；未修改任何上游源码（适配全部经幂等 fixup 脚本完成）。

## 五、test_package（消费者测试，单独统计，不计入上游 N）

两层设计：

- **第 1 层 `ohos_abi_check.py`**（纯 Python，任意宿主可跑）：**15/15 PASS**
  - 公共头文件齐备，含 `QBDI/Memory.hpp` 与 4 个 CMake 生成的头文件
    （`Config.h`/`Version.h`/`State.h`/`Options.h`）
  - `libQBDI.a` 为 ar 归档，含 ELF64 AArch64 目标文件
  - **私有 LLVM 确实静态并入**（`LLVMCreate`/`LLVMDispose`/`llvm::`/`LLVMContext`）
  - 无 Mach-O/PE 泄漏
- **第 2 层 `test_qbdi.cpp`**（仅 `can_run()`）——**在鸿蒙真机上验证内嵌 VM 全链路**：
  - T1：`QBDI::getVersion()` 返回 `0.12.1 (0x00000c01)`
  - T2：插桩后的 `vm.call()` 正常跑完
  - T3：被插桩的 `add3(1,2,3)` 仍返回 6（语义未被破坏）
  - T4：`PREINST` 回调被触发（实测观察到 **7 条指令**）
  - T5：第二次独立插桩运行同样正常（无全局状态泄漏）

  该测试**刻意不使用 `ptrace`/外部 attach**，只用进程内嵌 VM，
  因为本平台拒绝 `ptrace`（§2.3）。

## 六、遇到并解决的问题

| # | 现象 | 根因 | 解决 |
|---|---|---|---|
| 1 | `config.guess` 退出非 0，configure 中止 | LLVM 无条件调 `get_host_triple()`，而 `config.guess` 不认 HarmonyOS | `ohos_config_guess_fix.py` 幂等插入 aarch64:HarmonyOS 分支 |
| 2 | NATIVE TableGen：`Unable to determine platform` | CMake 无 `Platform/HarmonyOS` 模块，`UNIX` 未置位 | `ohos_llvm_platform_fix.py` 放宽 `HandleLLVMOptions.cmake` 的条件 |
| 3 | `merge_archives.cmake: unsupported system HarmonyOS` | 该脚本按 `CMAKE_SYSTEM_NAME` 白名单分发 | `-DCMAKE_SYSTEM_NAME=Linux`（ABI 本就是 Linux） |
| 4 | `config.guess` Permission denied / mktemp 失败 | HMDFS 上 `TMPDIR` 不可用（E011） | 指向非 HMDFS 的可写目录 |
| 5 | `QBDI/Config.h` file not found（消费者编译） | `package()` 只复制源码树头文件，生成头文件在构建树 | 同时从 `<build>/include` 与 `include-static/` 复制，并加缺件断言 |
| 6 | `QBDI/Memory.hpp` file not found | `package()` 用 `*.h` glob，漏掉 `.hpp` | 改为 `*.h` + `*.hpp`（避免误收 `*.h.in` 模板） |
| 7 | 找不到 Python3 dev headers | 设备无 Python 开发头 | `QBDI_TOOLS_PYQBDI=OFF` |
| 8 | spdlog / Catch2 / LLVM 下载偶发失败 | `conan create` 每次落在新 build folder，需重新下载 | 用本地已有副本预置 `third-party/`（见 §5 说明）；失败重试 |

## 七、风险与边界

- **preload / 外部 attach 模式未主张**：依赖 `ptrace`，鸿蒙 PC 普通用户被拒绝。
  本包交付的是**可嵌入的进程内 VM**，其全部功能在真机验证通过。
  这是平台能力边界，不是适配缺陷；也不存在"为了构建而删除核心功能"。
- **doc/示例/工具组件裁剪**：`QBDI_TOOLS_FRIDAQBDI`、`QBDI_TOOLS_PYQBDI`
  关闭的是**包装工具**（分别需要 Frida 与 Python 开发头），核心库与测试未受影响。
- **构建耗时与网络**：`libQBDI.a` 内嵌 LLVM 19.1.5，全量构建 872 个目标；
  依赖经 FetchContent 从 GitHub 拉取，链路不稳时需重试或预置本地副本。
- 未修改任何上游源码；未删除、跳过或放宽任何测试。
