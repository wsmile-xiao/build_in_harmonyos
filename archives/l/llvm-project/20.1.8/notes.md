# llvm-project 20.1.8 适配笔记（HarmonyOS PC · 标准 Conan cmake）

## Summary

- 上游：**llvm-project 20.1.8**（tag `llvmorg-20.1.8`，commit `023ec9011c9a92cfa8922030eb266d66a10f78f8`）
- 归档：官方发布 tarball `llvm-project-20.1.8.src.tar.xz`
  （sha256 `6898f963c8e938981e6c4a302e83ec5beb4630147c7311183cf61069af16333d`，实测下载复核与仓内 `clang/20.1.8` conandata 一致）
- 产物：**单包同时提供 LLVM 20.1.8 与 Clang 20.1.8 的开发面**（LLVMConfig + ClangConfig/ClangTargets +
  LLVM/Clang 组件静态库 + libLLVM.so + 头文件 + llvm-config/FileCheck/llvm-lit 工具），
  三元组 `aarch64-unknown-linux-ohos`，后端 **AArch64 + ARM + X86**，RTTI 开
- 状态：built（编译通过 + conan-verify G0–G4 通过 + test_package 通过）

### 为什么有这一单（依赖项任务的根因）

下游 `ispc 1.28.2` 的 CMake 同时消费 LLVM 与 Clang 的开发面：

```
ispc/cmake/FindLLVM.cmake : find_program(llvm-config) → LLVM_DIR=<bin>/../lib/cmake/llvm
                            run_llvm_config(--libdir/--includedir/--libfiles/--targets-built/--system-libs)
ispc/CMakeLists.txt:411   : set(CLANG_LIBRARY_LIST clangFrontend clangBasic clangEdit clangLex
                                              clangSupport clangASTMatchers)
ispc/CMakeLists.txt:818   : find_library(<lib>Path NAMES lib<lib>.a clang-cpp HINTS ${LLVM_LIBRARY_DIRS})
```

库中现状（编排方实测）：

| 现有包 | 缺口 |
|---|---|
| `llvm/20.1.0`（ohpcd, OHOS armv8） | 只有 LLVM（`lib/cmake/llvm` + `include/llvm` + 组件静态库），**无 Clang** ⇒ ispc configure 得 `clangFrontendPath-NOTFOUND` |
| `clang/20.1.8`（ohpcd） | 远端包**损坏**（`conan download` 报 `Recipe clang/20.1.8:6b129b06… is corrupted in the server, it doesn't contain a conan_package.t file`），不可用 |
| `clang/22.1.8`（ohpcd） | 完整 Clang dev，但是 **LLVM 22**，超出 ispc 1.28.2 目标区间 |

## 编译环境

- 构建系统：CMake 4.1.2 + Ninja 1.13.1（Release）
- 编译器：设备 hnp 工具链（`tools.build:compiler_executables` 的 `c/cpp`，即
  `/data/service/hnp/bin/clang`、`/data/service/hnp/bin/clang++`，clang 15.0.4，Target `aarch64-unknown-linux-ohos`）
- 目标三元组：`aarch64-unknown-linux-ohos`（`LLVM_HOST_TRIPLE` = `LLVM_DEFAULT_TARGET_TRIPLE`）
- 构建形态：**鸿蒙 PC 真机原生编译**（aarch64→aarch64），不设 `CMAKE_SYSTEM_NAME`

## 编译步骤

1. `conan source` 下载并解压 `llvm-project-20.1.8.src.tar.xz`（sha256 校验）
2. `build()` 内覆盖 `llvm/cmake/config.guess` 为 stub：`#!/bin/sh` + `echo aarch64-unknown-linux-ohos`
3. `build()` 内生成 `Platform/HarmonyOS.cmake`（内容 `include(Platform/Linux)`）并挂到 `CMAKE_MODULE_PATH`
4. cmake 配置：`LLVM_ENABLE_PROJECTS=clang`、`LLVM_TARGETS_TO_BUILD="AArch64;ARM;X86"`、Release、断言关、
   `LLVM_INCLUDE_TESTS=OFF`、关 zlib/zstd/libxml2/terminfo/libedit/libpfm、`LLVM_PARALLEL_LINK_JOBS=4`
5. `cmake --build`（`-j6` 防 OOM）→ `cmake --install` → 补 `llvm-lit`/`clang-diff`/`clang-fuzzer-dictionary`
   → 捆绑 SDK 运行资源 → 统一代码签名

## 关键适配点

### 1. 后端必须是 AArch64 + ARM + X86（与三个参考配方的 AArch64-only 不同）

`ispc/cmake/FindLLVM.cmake`：

```cmake
run_llvm_config(LLVM_TARGETS_BUILT "--targets-built")
set(LLVM_SUPPORTS_ARM ON)
if (NOT LLVM_TARGETS_BUILT MATCHES "AArch64" OR NOT LLVM_TARGETS_BUILT MATCHES "ARM")
    set(LLVM_SUPPORTS_ARM OFF)          # ← AArch64-only 时命中
endif()
option(ARM_ENABLED "Enable ARM support" ${LLVM_SUPPORTS_ARM})
```

aarch64 宿主上 `X86_ENABLED = X86_HOST = OFF`；ARM 再被上面判 OFF ⇒
`ispc/CMakeLists.txt:357`：

```cmake
if (NOT X86_ENABLED AND NOT ARM_ENABLED AND NOT WASM_ENABLED AND NOT XE_ENABLED)
    message( FATAL_ERROR "Either X86, ARM, WASM or XE targets need to be enabled.")
endif ()
```

即 **AArch64-only 的 LLVM 对 ispc 是 configure 级不可用**（不只是版本区间问题）。
X86 另有两个硬用途：`X86_ENABLED=ON` 时 ispc 用
`clang++ -x c -I… --target=x86_64-unknown-unknown -march=core2 -O2 -emit-llvm …` 生成 dispatch bitcode
（`cmake/GenerateBuiltins.cmake:113`），并为 x86 目标生成 builtins（`:299`）；且 ispc 自身 lit 套件有
167 个 `REQUIRES: X86_ENABLED` 用例（下游 ≥90% 通过率门禁）。故本包
`-DLLVM_TARGETS_TO_BUILD="AArch64;ARM;X86"`。

### 2. `config.guess` stub（设备 `uname -s = HarmonyOS`）

LLVM 的 `config-ix.cmake` 无条件调用 `get_host_triple()`，其内部跑 `cmake/config.guess`；
设备上该脚本不认 `HarmonyOS` → 非零退出 → FATAL（`-DLLVM_HOST_TRIPLE` 挡不住）。
`build()` 内用 stub 覆盖它，直接输出 `aarch64-unknown-linux-ohos`（与 `llvm/20.1.0`、`clang/20.1.8`、
`clang/22.1.8` 同族策略）。

### 3. `Platform/HarmonyOS.cmake` 垫片

cmake 无 `Platform/HarmonyOS` 模块 ⇒ `UNIX` 变量未置 ⇒ `HandleLLVMOptions` 报
"Unable to determine platform" FATAL。提供 `include(Platform/Linux)` 垫片挂到 `CMAKE_MODULE_PATH`。
**不设** `CMAKE_SYSTEM_NAME` ⇒ `CMAKE_CROSSCOMPILING=FALSE` ⇒ `llvm-tblgen`/`clang-tblgen` 原生编+跑，
彻底绕开交叉编译的 tblgen 主机版难题（这正是选择真机原生而非交叉的核心收益）。

### 4. 动态聚合库瘦身 + 组件静态库全留

`LLVM_BUILD_LLVM_DYLIB=ON` + `LLVM_LINK_LLVM_DYLIB=ON`：bin/ 工具链 `libLLVM.so` 而非静态内嵌，
避免单文件超制品仓上限。**组件静态库仍全部安装**——下游 ispc 用 `llvm-config --libfiles` 取它们的全路径。

### 5. 运行资源从 SDK 捆绑（不源码构建 runtimes）

`LLVM_ENABLE_RUNTIMES=""`：SDK 的 libc++ 15 头与 clang 20 不兼容、compiler-rt 交叉链接失败。
`package()` 内从设备 SDK 复制 `clang_rt` crt/builtins、`libunwind.a`、`libc++abi.a` 到包内
resource-dir `lib/clang/20/lib/aarch64-linux-ohos`。**R26 合规**：不复制 SDK 的
`libc++.so`/`libc++_shared.so` 等系统同名动态库，只复制 `.a`/`.o`。

### 6. ELF 代码签名

OHOS XPM 要求 dlopen 的 `.so` 与被 exec 的可执行文件都代码签名，否则 `Permission denied`。
`package()` 内对 `lib/**/*.so*` 与 `bin/` 下所有真实 ELF（跳过软链）统一
`llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`。

### 7. `package_info()`：一次挂两个 cmake config 目录

```python
self.cpp_info.set_property("cmake_file_name", "LLVM")
self.cpp_info.set_property("cmake_find_mode", "none")
self.cpp_info.builddirs = ["lib/cmake/llvm", "lib/cmake/clang"]
```

`cmake_find_mode="none"` ⇒ Conan 不生成 find 文件；`builddirs` 经 CMakeToolchain 进
`CMAKE_PREFIX_PATH`（`blocks.py` FindFiles：host 依赖的 builddirs 全部前置），于是
`find_package(LLVM)` 与 `find_package(Clang)` 都直接命中包内原生 config
（`ClangConfig.cmake` 内部还会 `find_package(LLVM <ver> EXACT … HINTS <prefix>/lib/cmake/llvm)` 拿组件图）。

**下游须知**：`package_type="library"` ⇒ `bindirs` 不进 PATH。ispc 的 `find_program(llvm-config)` 必须
由 ispc 配方显式传 `-DLLVM_CONFIG_EXECUTABLE=<pkg>/bin/llvm-config`（或把
`self.dependencies["llvm-project"].cpp_info.bindirs[0]` 前置进 PATH），否则 `FindLLVM.cmake` FATAL
"Failed to find llvm-config"。

## 源码修改（0 个 patch）

本包**不改上游源码**：两处平台适配（config.guess stub、Platform/HarmonyOS.cmake 垫片）都在 `build()` 内
生成临时文件，不落 `patches/`（与 `llvm/20.1.0`、`clang/22.1.8` 同族策略；`clang/20.1.8` 的两个补丁是
lit 测试环境补丁，本包不在 CI 跑 lit 全量套件，不需要）。`conandata.yml` 的 `patches: {}`。

## 交付面自证（下游 ispc 的验收判据，逐项 ls 证据）

> 读数取自 `conan cache path llvm-project/20.1.8:01d92cf349a0dd98ff915f4bd99a04430171517f` 指向的包目录
> （本机 `conan create` 实测）。逐项原始输出留档 `$TASK_DIR/devface-evidence.txt`（仓库外）。

| 判据 | 实测 |
|---|---|
| `lib/cmake/llvm/LLVMConfig.cmake` | ✅ 14067 B（+ `LLVMConfigVersion.cmake` 447 B、`LLVMExports.cmake` 41418 B） |
| `lib/cmake/clang/ClangConfig.cmake` | ✅ 2220 B（+ `ClangConfigVersion.cmake`、`ClangTargets.cmake` 17554 B、`ClangTargets-release.cmake` 30046 B） |
| ispc 的 6 个 clang 组件静态库 | ✅ `libclangFrontend.a` 4977204 B / `libclangBasic.a` 11852794 B / `libclangEdit.a` 96952 B / `libclangLex.a` 1795506 B / `libclangSupport.a` 67362 B / `libclangASTMatchers.a` 1597496 B |
| clang 组件静态库总数 | 43 |
| LLVM 组件静态库总数 | 115（含 ispc `LLVM_COMPONENTS` 全项：ipo/bitreader/bitwriter/instrumentation/linker/option/frontendopenmp/passes/windowsdriver/orcjit/engine 与 ARM/X86/AArch64 三后端） |
| `libLLVM.so` | ✅ `libLLVM.so -> libLLVM.so.20.1`（95332928 B） |
| 头文件 | `include/llvm` 2076 文件、`include/llvm-c` 29、`include/clang` 825、`include/clang-c` 13 |
| 工具 | ✅ `bin/llvm-config`、`FileCheck`、`llvm-lit`、`llvm-as`、`clang`、`clang++`、`llc`、`opt`、`not`、`count`、`split-file`（`bin/` 共 122 项） |
| R26（系统同名动态库） | ✅ 包内无 `libc++.so*` / `libc++_shared.so*` / `libc++abi.so*`（只复制了 `.a`/`.o`） |
| ELF 代码签名 | ✅ 抽查 `bin/llvm-config`、`lib/libLLVM.so` 的 `.codesign` 段均在 |
| 包体积 / 最大单文件 | 839 MB / 95 MB（< 制品仓 408 MB 单文件上限） |

## 测试验证

### 1. 上游测试清点（N，R51 / E328 候选数法取最大值）

口径 = 「lit 框架可发现的测试文件数」，只统计本包实际启用的两个 project（`llvm/test`、`clang/test`；
`LLVM_ENABLE_PROJECTS` 未启用 mlir/flang/lld/lldb/… 的套件，故不计入）。清点规则：取两个套件顶层
`config.suffixes` 与**全部 502 个 `lit.local.cfg` 追加后缀的并集**，再按 lit 的 `config.excludes`
排除 `Inputs`/`CMakeLists.txt`/`README.txt`/`LICENSE.txt`。可复算命令见
`test_package/MANIFEST.yml` 的 `upstream_test_count` 段。

| 候选口径 | `llvm/test` | `clang/test` | 合计 |
|---|---|---|---|
| lit 框架注册口径（后缀并集 + excludes） | 55394 | 20847 | **76241** |
| 全文件数上限（排除 excludes 目录后的一切文件） | 56044 | 20962 | **77006** |

**N 取候选数法最大值 77006**（差额 765 = 非测试辅助文件：`.gitignore`/`.py` 工具脚本/README 等无
`RUN:` 行者，逐项归因；四口径不得混用）。

### 2. 上游测试实跑（N′，手工有界子集，非 CI）

`LLVM_INCLUDE_TESTS=OFF`（CI 内不构建 lit 套件）。为给出真读数，另起一个 **configure-only** 的
`LLVM_INCLUDE_TESTS=ON -DLLVM_BUILD_TESTS=OFF -DCLANG_INCLUDE_TESTS=ON` 构建目录生成
`lit.site.cfg.py`，把 `llvm_tools_dir`/`llvm_libs_dir` 指回真实构建树后，用**真实构建出来的
`bin/llvm-lit`** 跑两个有界子集（`-j4`）：

| 子集 | 发现用例 | Passed | Failed | Unsupported | XFAIL | 用时 |
|---|---|---|---|---|---|---|
| `llvm/test/{Assembler,Bitcode,Verifier,Transforms/InstSimplify}` | 1351 | 1324 (98.00%) | 0 | 26 | 1 | 83.5 s |
| `llvm/test/{MC/{AArch64,ARM,X86},CodeGen/{AArch64,ARM,X86}}` | 13662 | 13414 (98.18%) | 8 (0.06%) | 222 | 18 | 1349.7 s |
| **合计** | **15013** | **14738 (98.17%)** | **8** | **248** | **19** | — |

`TOTAL = PASS + FAIL + SKIP + NOT_RUN` 口径：本子集 `15013 = 14738 + 8 + 248 + 19`；
相对声明 N=77006，**NOT_RUN = 61993**（未跑的其余 lit 用例，按下方豁免五条原因整体申报）。

**8 个 FAIL 的形态与归因**（原始日志 `$TASK_DIR/lit-run2.log`，仓库外）：

- 7 项是 `CHECK-NEXT/CHECK-ERROR-NEXT: is not on the line after the previous match`
  （`MC/AArch64/armv8.4a-dit.s`、`armv8.4a-ldst-error.s`、`armv8.4a-ldst.s`、`armv8.8a-nmi-error.s`、
  `armv8a-fpmul-error.s`、`armv8r-unsupported-inst.s`、`MC/ARM/bfloat16-a32-errors2.s`）；
- 1 项是 `CHECK: expected string not found`（`CodeGen/X86/early-ifcvt-remarks.ll`）。

这 8 项的共同形态是**对 `2>&1` 合并流做逐行相邻匹配**：`llvm-mc -show-encoding` 把编码写 stdout、
诊断写 stderr，两者合并后**行序/行数**与上游期望不同（FileCheck 的 input dump 中多出一行空行，
使后续 `CHECK-NEXT` 全部错位）。同一条命令单独复现时 stderr 本身**没有**空行、诊断列号自洽
（`<stdin>:7:10` + caret 落在第 10 列），说明差异出在**流的缓冲与交错**而非诊断内容。
这与已登记的同类非适配失败一致：`archives/c/clang/22.1.8/notes.md` 记「4 个最终未通过均为编译器
行为演进（模块名大小写、**输出缓冲**、MC/DC 警告）或系统固有限制（只读 /tmp），非适配缺陷」。
本包**没有**任何编码/目标/链接层面的失败（三后端 MC/CodeGen 其余全部通过）。

> 诚实边界：以上归因定位到「合并流的行对齐」这一层，未逐项追到单一上游 commit；未通过的 8 项与
> 未跑的 61993 项均按 NOT_RUN/FAIL 如实计数，未计入 PASS。

### 3. test_package（鸿蒙特有测试，7/7）

按下游 ispc 1.28.2 的**真实消费姿势**验证（R34 反空壳），本机 `conan test` 实测 **rc=0**：

1. `find_package(LLVM REQUIRED CONFIG)` → `LLVM_PACKAGE_VERSION=20.1.8`、
   `LLVM_LIBRARY_DIRS=<pkg>/lib`、`LLVM_INCLUDE_DIRS=<pkg>/include`；
2. `find_package(Clang REQUIRED CONFIG)` → `CLANG_INCLUDE_DIRS=<pkg>/include`；
3. 用 ispc 的原判据 `find_library(<lib> NAMES lib<lib>.a clang-cpp HINTS ${LLVM_LIBRARY_DIRS})`
   逐项命中 6 个 clang 组件静态库（配置期断言，缺一即 FATAL）；
4. 链接 6 个 clang 组件静态库 + `libLLVM.so` 并**真实运行**探针：逐库调用真实导出符号
   （`clangBasic::getClangFullVersion`、`clangFrontend::CompilerInstance`、
   `clangASTMatchers::MatchFinder`、`clangSupport::RISCV::LMULType`、`clangEdit::EditedSource`、
   `clangLex::Lexer::getLocForEndOfToken`、`LLVM::sys::getDefaultTargetTriple`）→
   输出 `llvm-project devface probe OK: clang clang version 20.1.8, 7 component checks, host triple aarch64-unknown-linux-ohos`；
5. `bin/llvm-config --version` → `20.1.8`；`--libdir`/`--includedir` → 包内路径；
   `--libfiles aarch64 arm x86` → `<pkg>/lib/libLLVM-20.so`；
6. `bin/llvm-config --targets-built` 断言同时含 `AArch64`/`ARM`/`X86`（ispc `LLVM_SUPPORTS_ARM`
   与 `X86_ENABLED` 判据）；
7. `bin/FileCheck` 真实执行一次 CHECK 匹配（rc=0）。

> 运行环境要点（已写进 `test_package/conanfile.py` 注释）：`package_type="library"` + `shared=True`
> ⇒ Conan 判定 traits = `shared-library` ⇒ `run=True` ⇒ `VirtualRunEnv` 把本包 `lib/` 放进
> `LD_LIBRARY_PATH`。**必须用 `env="conanrun"` 运行**，否则 profile buildenv 的
> OHOS SDK `llvm/lib`（内含 SDK 的 `libLLVM.so` 15.x）会遮蔽本包的 `libLLVM.so.20.1`，
> 运行期报 `Error relocating … symbol not found`（本任务实测踩过一次）。

### 4. 采信轮 / conan-verify

**结论：rc=1（结构性不可达），根因是框架已知未修缺陷，不是本包配方问题。**

- 2026-10-11 01:33:38 按固序启动
  `sh tools/conan_verify_round.sh llvm-project 20.1.8 --repo … --task-dir … --timeout 14400`（分离式、rc 落盘）。
  步骤 [0]–[0c] 全过：inode 充足、`HEAD` 已冻结、受跟踪脏文件 0 个、三点 diff 13 文件（已导出 `JUNK_PR_DIFF`）；
  G0 PASS、G1 PASS；`[E017] 未注入（镜像 https://ghfast.top 不可达，改走官方源）`（故 `conandata.yml` 未被改写）。
- **G2 实测在启动后第 3600 秒整被杀**（`02:33:38`），产物即缺陷记录描述的那个形态：

  ```
  $ ls -l archives/l/llvm-project/20.1.8/reports/conan-create.log
  -rw-r----- 1 … 7 2026-10-11 02:33 conan-create.log
  $ od -c archives/l/llvm-project/20.1.8/reports/conan-create.log
  0000000   T   I   M   E   O   U   T
  0000007
  ```

  ⇒ `capture_evidence.py` 干净轮标志计数 0/0/0，判 `cached/missing` ⇒ **采信轮 rc=1**
  ⇒ 按 AGENTS §3.3「rc=1 不要进 finish」链尾断。同一轮里 G4/L2/L4/L5 因 G2 失败被跳过（实跑 0/4、跳过 4/4）。
  附带：知识图谱引擎把该失败误命中为 **E017（GitHub 网络超时）**，与本轮真实根因无关
  （E017 探测行自己打印「未注入」，且 `conan create` 的源码下载阶段早已成功完成——本机实测官方源
  147.2 MB 下载约 30 s）。
- **不可达的机械原因**（读码确认）：`scripts/ohc/conan_verify.py:751` 的
  `rc, output = self._run(cmd, timeout=3600, cwd=…)` 是**字面量**，
  `framework/overlay/scripts/ohc/conan_verify.py` 副本同样保留；`_run()` 在 `TimeoutExpired` 时
  **直接 `return 1, "TIMEOUT"`（不重试）**，并把 `reports/conan-create.log` 整文件覆盖成 7 字节。
  `tools/conan_verify_round.sh --timeout` 只包外层 `timeout`；`OHC_W3_TIMEOUT` 与
  `ci/config/build_timeouts.txt` 只被 `finish` 的 W3 步骤（`scripts/ohc/build_timeout.py`）消费。
  本包本机干净构建实测 **4201 个 ninja 步骤 / 约 2h40m**（22:01→00:44，`-j6`），必然超窗。
  容器层自己已把该缺陷登记为**未修**并写明后果：「重型包（clang/llvm/qt/casacore 等已登记 7200–14400s 的包）
  在采信轮路径上**没有可用超时入口**」（`notes/defects/conan-verify-and-recipe.md`「采信轮 `conan create`
  的三个硬缺陷」①）。
- **已排除的绕行**（逐条读码/实测确认，均不可接受）：
  ① `--skip-clean`：`conan-verify` 仍会跑 `conan create`；且 G2 的 create 带
     `--user=ohpcd --channel=stable`，与本机手工构建的裸 ref **不同名**，缓存不可能命中 ⇒ 仍 rc=1；
  ② `--timeout` / `OHC_W3_TIMEOUT`：改不了 G2 内层超时（见上）；
  ③ 手工预热 build 目录 / 复用旧构建树：把「干净轮」做成增量轮，判为**假绿**，不做；
  ④ 改 worktree 内 `scripts/ohc/conan_verify.py`：污染 PR 提交面，不做；
  ⑤ 引入 ccache 把二次构建压进 3600s：设备未安装 `ccache`（`command -v ccache` rc=1），
     且属「为绕工具缺陷改配方」，不做。
- **处置**：已两次上报编排方裁决，请其在三条中择一：**(A)** 授权修正
  `framework/overlay/scripts/ohc/conan_verify.py` 的 G2 超时为 `build_timeout.get_timeout(pkg/ver)`
  （正是该缺陷记录给出的修法；`framework/` 在 worktree 之外、不进 PR 提交面），随后正常重跑采信轮；
  **(B)** 授权以 CI 官方入口 `ci/conan/build_and_test.sh`（超时取自 `ci/config/build_timeouts.txt` = 14400s）
  的干净构建作为本轮干净轮证据，并把采信轮 rc=1 作为**工具缺陷**单列；
  **(C)** 判阻塞止损。本任务书明令「不改 `tools/`、`framework/`」，故未擅自修改；裁决到位后按裁决续跑。
- 本轮证据：`$TASK_DIR/verify-round-20261011-013253.log`（完整轮日志）、
  `archives/l/llvm-project/20.1.8/reports/conan-create.log`（7 字节 `TIMEOUT`，mtime 02:33）、
  `archives/l/llvm-project/20.1.8/reports/conan-verify-report.md`（G2 FAIL 报告）。

### 5. 处置执行记录：按编排方裁决 B 的干净轮（2026-10-11）

> 本节是 §4 的续记。**下列任何一句都不得读成「采信轮 rc=0」**——采信轮结论仍是 **rc=1（工具缺陷）**。

- **裁决**（`$TASK_DIR/ORCHESTRATOR-RULING-2026-10-10-clean-round-path-B.md`）：**B** —— 采信轮 rc=1
  如实登记为**工具缺陷**（G2 内层 3600s 硬编码，`scripts/ohc/conan_verify.py:751`，官方副本
  `scripts/ohc/conan_verify.py:587`），干净轮改用重包可用的超时入口；**A（改 `framework/overlay`）
  归维护轮，不混入本软件 PR**；C（止损）否决。
- **清缓存（唯一清净判据）**：`sh tools/clean_conan_cache.sh llvm-project` → rc=0，回查
  `recipes: []` / `packages: []`；`conan list "llvm-project/*"` = 0 条。另删上一轮遗留的
  `test_package/build/`（防 test_package 增量轮）。
- **干净轮 = 真实冷构建（G2 的同一条命令行）**，外层 `timeout` 取 `ci/config/build_timeouts.txt`
  登记的 14400s 量级兜底（即缺陷建议修法 `OHC_W3_TIMEOUT > build_timeouts > 3600` 的命令行等价物）：

  ```
  timeout -s KILL -k 60 18000 conan create <包目录> \
    -pr:h=<仓库内 ci/conan/profiles/ohos-aarch64 绝对路径> -pr:b=<同> \
    --build=missing --user=ohpcd --channel=stable
  ```

  读数：**rc=0 / 耗时 9616s（2h40m）/ ninja 4201-4201 / `error:` 0 次**；干净轮标志
  `run_make(RUN:)=239`、`calling_build=2`、`apply_patch=0`；包目录
  `…/.conan2/p/b/llvm-fc53b442a7a86/p`。唯一 1 处 `Already installed!` 出现在
  `======== Launching test_package ========` **之后**的 test_package 依赖图解析（不是本轮构建的缓存命中；
  主 `Installing packages` 段是 `Building from source` + 4201 步）。日志：
  `$TASK_DIR/clean-round-g2-20261011-025325.log`（941257 B / 9294 行）。
  `test_package` 真实执行：`clang_devface_probe OK: clang clang version 20.1.8, 7 component checks,
  host triple aarch64-unknown-linux-ohos`、`llvm-config --version`=20.1.8、
  `--libfiles aarch64 arm x86`→`lib/libLLVM-20.so`、`FileCheck` 实跑通过。
- **官方入口 `ci/conan/build_and_test.sh` 仍被真实执行**：`finish` 第 5 步（W3，
  `scripts/ohc/workflow_checks.py:run_local_ci`）以 `CI_PACKAGES=archives/l/llvm-project/20.1.8`
  跑该脚本，**超时预算 14400s**（读自同一份 `build_timeouts.txt`），全文进
  `reports/w3-local-ci.log`（949119 B）与 `.ci_logs/conan_build_llvm-project_20.1.8.log`；
  其判定行：`G0_RESULT=pass`、`JC_RESULT=pass`、`L0_RESULT=pass: all checks passed`、
  `L1_RESULT=pass: upstream tests + test_package executed`、`L2_RESULT=pass`、
  `L4_RESULT=pass: patches clean`、`L5_RESULT=pass: bin/ has content`。
- **证据副本三份 + 干净轮判读（finish 之前）**：`python3 tools/capture_evidence.py --package-dir <包目录>
  --task-dir $TASK_DIR --sha 7635d1bf077c2edc4cd0a2b12c1ba4abe46e7be4` → **rc=0**，
  `conan-create.log 941257 B / conan-verify-report.md 19020 B`，
  `✅ clean：构建标志计数 {'run_make': 239, 'calling_build': 2, 'apply_patch': 0}`，
  安装树 `…/p/b/llvm-fc53b442a7a86/p`（来源 `conan-create.log:Package folder`）lib/bin/include 全 True；
  索引 `$TASK_DIR/evidence-index.json`。7 字节 `TIMEOUT` 原件另存
  `$TASK_DIR/defect-evidence/conan-create.log.TIMEOUT-7B`（sha256
  `ab5b50c3846ccfef52997e6e153b187022cde34b543019aa4feaf1f732feff50`，**未删、未改写**）。
- **finish 实跑**：`finish llvm-project 20.1.8 built`（overlay 入口）→ **rc=1，失败步骤仅 `step7`**
  （W2 原子性对陈旧 `origin/main` 基线的误报：把 `knowledge/graph/index.tsv` 等算作「配方文件变更
  36266 个」，属容器层已登记的三项结构性噪声之一，非本包问题）；实质产出全部到位：
  `status: built`、`.ci-result.json`、`.build-closed`、`test-report.md`、Step 4 的
  `G1/G0/G2/G3/G4/L2/L4/L5 全 ✅`、Step 5（W3）✅、Step 10 submit 就绪 ✅。总耗时 9909s。
- **收尾副作用还原**：`tools/finish_restore.sh --apply` → rc=0，逐条还原被 finish 改写的受跟踪文件
  （`SUMMARY.md` 被整文件重建、`conandata.yml` 被改写成含 `gh-proxy.com` 的镜像**列表**、`notes.md` 追加 4 行）
  并清除工具残留（`feedback/SKILL_FEEDBACK_*.md`、`.build-cache/predl_cache/*`）；`git status --short` 复原为空。
  随后 `capture_evidence.py --restore` + `--verify` → **rc=0**（`conan-create.log`/`conan-verify-report.md`
  按 capture 权威回拷、`w3-local-ci.log` 按 post-capture 刷新，改写史逐条留痕，未静默覆盖）。
- **结构性事实（主干净轮日志为何取自 G2 同命令）**：官方入口按 CI 语义建**裸 ref**
  `llvm-project/20.1.8`（`ci/conan/build_and_test.sh:309-310` `unset CONAN_USER CONAN_CHANNEL`），
  而 `finish` 第 4 步恒定要 `@ohpcd/stable`（`conan_verify.py:747`，内层 3600s 字面量）；两个 ref 是
  两套缓存——本轮 cache 里同时出现 `p/b/llvm-fc53b442a7a86/p`（@ohpcd/stable，干净轮）与
  `p/b/llvm-a4635c5fa43c9/p`（裸 ref，W3 官方入口所建），即直接观测到该分裂；同设备最小配方实测见
  `$TASK_DIR/refsplit-evidence.txt`。⇒ 官方入口的构建**无法**被 finish 第 4 步复用；若只跑官方入口，
  该步必然冷重建并在第 3600 秒被杀、把 `status: built` 翻成 `failed`。同一原因使 W3
  （`build_and_test.sh:1364` 的 `--build="llvm-project/*"` 强制重建）与该步的构建无法合并，
  一轮完整 finish 对重包至少 2 次全量编译。该分裂已登记反馈
  `feedback/pending/2026-10-10-llvm-project-20.1.8.md` F5。
- **conan-verify 预览（finish 前先跑，确认第 4 步会过）**：`OHC_E017_MIRROR=off python3
  framework/run-ohc.py conan-verify llvm-project 20.1.8 --project-dir <worktree>` → **rc=0 / Verdict PASS**
  （实跑 G4/L2/L4/L5 = 4/4；G4：`bin/` 122、`lib/` 159 `.a` + 12 `.so`、`include/` 2769 头文件；
  L5 首次基线 3641 文件）。两处工具侧读数按容器层口径解读（**均为工具缺陷面，非本包问题**）：
  ① L4 的 114 条 `NX=disabled` 是已知解析假阳性（`readelf -l` 折行致 `GNU_STACK` flags 落下一行）——
     本任务用包内真产物反证：`llvm-readelf -lW` 与 GNU `readelf -lW` 对 `bin/clang`、`bin/llvm-config`、
     `bin/FileCheck`、`lib/libLLVM-20.so` 均输出 `GNU_STACK … RW 0x0`（无 E 位 = 栈不可执行，NX 实际开启）；
  ② L2 的「14 个二进制无法运行」为探针只试 `--version/--help/-V/-h`，命中对象是上游内部/测试辅助目标
     （`llvm-lit`、`c-index-test`、`diagtool`、`hmaptool`、`UnicodeNameMappingGenerator`、
     `llvm-jitlink-executor`、`lli-child-target` 等，不实现这些开关）；`llvm-lit` 的可用性另由
     `test_package` 与手册 lit 子集实跑覆盖。两项工具读数都判 ✅ PASS（按其分级非阻断）。

## 已知问题 / 待办

1. **采信轮对 LLVM 级重包结构性跑不通（框架已知未修缺陷，非本包配方问题）**：
   `scripts/ohc/conan_verify.py`（G2 的 `conan create`）内层超时**硬编码 3600s**，无任何环境变量/参数
   入口，`framework/overlay` 副本同样保留；`tools/conan_verify_round.sh --timeout` 只包外层。
   容器层自己已登记该缺陷（`notes/defects/conan-verify-and-recipe.md` §「采信轮 conan create 的三个
   硬缺陷」①）并写明「重型包（clang/llvm/qt/casacore 等已登记 7200–14400s 的包）在采信轮路径上
   **没有可用超时入口**」。本包本机干净构建实测约 2h40m（4201 个 ninja 步骤，`-j6`），必然在
   3600s 整被杀，且超时会把 `reports/conan-create.log` 整文件覆盖成 7 字节 `TIMEOUT`（同缺陷③），
   `capture_evidence.py` 判 `cached/missing` ⇒ 采信轮 rc=1。**处置已按编排方裁决 B 执行完毕，
   见上文「5. 处置执行记录」**：本包交付所依据的干净轮是清缓存后的真实冷构建（G2 同命令 + 14400s
   量级外层兜底，rc=0 / 4201-4201 步），官方入口在 `finish` 的 W3 步以 14400s 真实执行并全绿；
   采信轮路径的 rc=1 保持**工具缺陷**定性，等待维护轮修 `conan_verify.py:751` 后重跑。
2. 全量 lit 未在 CI 运行（豁免理由见 `test_package/MANIFEST.yml`）；手工子集 8 项 FAIL 的根因
   定位到「合并流行对齐」层，未追到单一上游 commit。
3. 包内 `bin/clang` 单独编译 C/C++ 需外部 `--sysroot=<OHOS SDK sysroot>`（hnp clang 驱动按
   `<prefix>/../sysroot` 推导，conan 缓存内不存在）；下游 ispc 只用它 `--emit-llvm` 生成 bitcode，
   不需要 sysroot。

## 合并 main 解决 `ci/config/build_timeouts.txt` add/add 冲突（收尾轮）

PR 交付后 `upstream/main` 前进（`ff1dce4f967c1f56051cbd1f0839f2612389f710` → `7f8e84a6491cba831b98ebaa9aac3073d0644baa`），
平台侧报「存在 1 项冲突」，冲突文件 `ci/config/build_timeouts.txt`（add/add：双方都在**同一位置**追加行）。
本分支以**两父合并提交**（非 rebase、非 force push、不改写历史）解决：

- 合并提交：`a29162c7fb6f8299e27ec8e615b31bdf55f466b8`，父 = `e654d801c41d0c68212de2c3ed60213a2ecbd171`（本分支）
  + `7f8e84a6491cba831b98ebaa9aac3073d0644baa`（`upstream/main`）。
- 解决口径：**保留 main 侧全部内容**（`alacritty/0.17.0 10800` 及其 6 行注释块，逐字不动）；
  保留我方那一行 `llvm-project/20.1.8 14400`（**单行、无多余注释、不重复**），并把它从**文件尾部**
  移到 llvm/clang 同族条目之后（`llvm/15.0.4 10500` 的下一行），避免下次 main 在尾部追加新条目时
  重现 add/add 冲突。全文无冲突标记。
- **包面未变**：`git diff e654d801c41d0c68212de2c3ed60213a2ecbd171..a29162c7fb6f8299e27ec8e615b31bdf55f466b8
  -- archives/l/llvm-project` 实测**无输出**；`git diff upstream/main...HEAD --stat` 仍为本任务 **13 文件**。
- **H11 已按新 HEAD 重绑定**：合并后 HEAD 前移，故按 AGENTS §3.3 H11 重派 W4 独立审计，
  `head_sha` = 新 HEAD，结论落 `reports/audit-result.json`（ignored，不入库）。
- 另注（T1 文档 delta）：本节文字本身是 `notes.md`（T1，不进 `conan create` 构建输入）的文档增量，
  提交在合并提交之上；因此「包面未变」的自证以**合并提交**为基准，最终 HEAD 相对 `e654d801` 的
  `archives/l/llvm-project` 差异**仅 `notes.md` 一个文件**（配方/正文/测试等构建与交付面仍逐字节未变）。

---

**编译结束**：2026-10-11 00:44（首次本机 `conan create`，4201/4201 ninja 步骤 + `cmake --install` + 签名）
**交付依据的干净轮**：2026-10-11 02:53–05:14，清缓存后 G2 同命令真实冷构建 rc=0 / 9616s / 4201-4201 步
（`$TASK_DIR/clean-round-g2-20261011-025325.log`）；`finish`（含 W3 官方入口 14400s 全量重建）rc=1 仅 `step7` 噪声
**最终状态**：built
