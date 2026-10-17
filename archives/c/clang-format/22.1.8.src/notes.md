# clang-format 22.1.8.src 适配笔记（HarmonyOS PC · aarch64）

## Summary

- 将 LLVM clang-format 22.1.8（clang-format 代码格式化 CLI 工具）从官方 llvm-project 源码
  构建为鸿蒙 PC aarch64 原生可执行文件。
- 上游版本：22.1.8（release tag `llvmorg-22.1.8`）
- 上游仓库：https://github.com/llvm/llvm-project （官方 release tarball，
  `llvm-project-22.1.8.src.tar.xz`，sha256 `922f1817a0df7b1489272d18134ee0087a8b068828f87ac63b9861b1a9965888`）
- 构建方式与 clang/22.1.8、clang-format-11/11.1.0 同族：鸿蒙 PC 真机原生编译，不设
  CMAKE_SYSTEM_NAME → 不触发交叉编译 → llvm-tblgen/clang-tblgen 原生编+跑。

## 编译环境

- 构建系统: CMake 4.1.2 + Ninja 1.13.1（Release，仅 AArch64 target）
- 编译器: /data/service/hnp/bin/clang / clang++（设备 hnp 工具链，clang 15.0.4）
- 目标三元组: aarch64-unknown-linux-ohos
- 状态: built（conan create + test_package 通过）

## 上游测试清点（R51 第一步）

llvm-project 22.1.8 单仓内与 clang-format 相关的上游测试分两类：

| 类别 | 位置 | 形态 | 清点数 |
|------|------|------|--------|
| 单元测试 (gtest) | `clang/unittests/Format/` | CMakeLists 把 36 个 `.cpp` 注册进 `FormatTests` 目标（其中 21 个为 `*Test.cpp`） | 实测运行 **1244** 个 gtest 用例 / 39 test suites |
| lit 测试 | `clang/test/Format/` | `.cpp/.h/.m/.test` 文件（`lit.local.cfg` 定义后缀） | 实测 **32** 个 lit 用例 |

清点命令（源码树内）：
```
ls clang/unittests/Format/*Test.cpp | wc -l                       # 21 个 *Test.cpp
grep -oE '[A-Za-z0-9_]+\.cpp' clang/unittests/Format/CMakeLists.txt | sort -u | wc -l   # 36（FormatTests 注册的 .cpp）
ls clang/test/Format/ | grep -v lit.local.cfg | wc -l             # 32 个 lit 用例
```
两类测试全部为本机可运行，已 **100% 真实运行**（见下）。

## 编译步骤

1. 解压 `llvm-project-22.1.8.src.tar.xz`（源码树顶层含 `llvm/ clang/ clang-tools-extra/ ...`）。
2. `cmake -S llvm -B build-ohos`（LLVM 布局：clang-format 在 `clang/tools/clang-format`，
   `LLVM_ENABLE_PROJECTS=clang` 即可），配置参数见 manifest.yaml。
3. `cmake --build build-ohos --target clang-format FileCheck FormatTests count not llvm-config -j 4`。
4. 上游测试实跑（R51）：单测 `FormatTests` + lit `clang/test/Format`。
5. 打包：收全上游 clang-format 组件的交付物（对齐 `clang/tools/clang-format/CMakeLists.txt`
   的 `install()` 规则）：`bin/clang-format`（add_clang_tool）+ `bin/git-clang-format`
   （install(PROGRAMS)）+ `share/clang/*`（clang-format-diff.py / clang-format.py /
   clang-format-sublime.py / clang-format.el / clang-format-bbedit.applescript）+
   `licenses/LICENSE.TXT`（application，bindirs=bin）。上游 `clang-format-fuzzer` 为
   `EXCLUDE_FROM_ALL` 且无 install 规则，不属于交付物。

## LLVM 22 相对 LLVM 11 的差异（本次逐一核对源码树后修正）

| # | 项 | LLVM 11（先例） | LLVM 22（本版） | 影响 |
|---|----|----------------|----------------|------|
| 1 | clang-format 位置 | `clang/tools/clang-format` | `clang/tools/clang-format`（同） | `-DLLVM_ENABLE_PROJECTS=clang` 仍然足够 |
| 2 | googletest 位置 | `llvm/utils/unittest/googletest` | `third-party/unittest/googletest` | 已迁移；`LLVM_INCLUDE_TESTS=ON` 下 CMake 自动处理，无需额外开关 |
| 3 | cmake 最低版本 | 3.4.x（旧 policy） | 3.20.0 | cmake 4.1.2 无 policy 报错 → **移除** `CMAKE_POLICY_VERSION_MINIMUM` |
| 4 | lit 工具解析 | `use_llvm_tool` 回退搜 PATH（命中 hnp clang） | **不再回退搜 PATH**（`use_installed=False`） | `clang/test/lit.cfg.py` 的 `use_clang(required=True)` 必须靠 `CLANG` 环境变量提供 clang，否则 `llvm-lit` 首行 fatal（0 通过） |
| 5 | lit 汇总行格式 | `  Passed: N` / `  Unexpectedly Failed: M` | `  Passed: N (100.00%)`（带百分比）/ 失败标签 `Failed` | 朴素正则（尾锚 + `Unexpectedly Failed`）无法解析 → 改为无尾锚 + 新标签 + 汇总多类失败标签 |
| 6 | gtest CapturedStream 临时文件 | 同 | 硬编码 `/tmp/gtest_captured_stream.XXXXXX` | 鸿蒙 `/tmp` 只读（E002）→ gtest FATAL/SIGABRT，整轮单测中止（0 结果）；见下 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config-ix.cmake` 无条件调用 `config.guess` 报 "unable to guess system type"（FATAL） | 设备 `uname -s=HarmonyOS`，LLVM 的 config.guess 不认 | build() 覆盖 `llvm/cmake/config.guess` 为 stub：`#!/bin/sh\necho aarch64-unknown-linux-ohos` |
| 2 | cmake 提示 "System is unknown to cmake, create Platform/HarmonyOS" | cmake 无 HarmonyOS 平台模块，UNIX 变量未置 | 提供 `Platform/HarmonyOS.cmake`（`include(Platform/Linux)`）挂到 `CMAKE_MODULE_PATH`，保持 native（不设 CMAKE_SYSTEM_NAME） |
| 3 | `llvm-lit` 首行 fatal（0 通过） | LLVM 22 的 `lit.llvm.use_llvm_tool` 不再回退搜 PATH，`use_clang(required=True)` 找不到 clang | build() 运行 lit 前设 `os.environ["CLANG"]=<tools.build:compiler_executables.c>`（lit 的 `search_env` 覆盖项），工具链 clang 被 lit 接受；`clang/test/Format` 全部用例只调 clang-format，不使用 `%clang`，结果不受影响 |
| 4 | 单测 `FormatTests` 运行到 `ConfigParseTest.GetStyleOutput` 时 `[ FATAL ] gtest-port.cc:1126` + `Signal 6`，整轮 0 结果 | 鸿蒙 `/tmp` 只读，而 llvm 内置 googletest 的 CapturedStream 把临时文件硬编码到 `/tmp/gtest_captured_stream.XXXXXX`（无环境变量开关） | build() 编译一个 20 行 LD_PRELOAD 垫片（拦截 `mkstemp`，把 `/tmp/` 前缀改写到可写 cwd，路径只变短、原地改写仍在 `std::string` 容量内），单测在垫片下 **1244/1244 全通过**；未改任何上游源码/测试 |
| 5 | lit 统计行解析 | 见上表 #5 | 正则改 `^\s*<label>\s*:\s*(\d+)`，失败 = Failed+Timed Out+Unresolved+Unexpectedly Passed |
| 6 | lit `map_config` 找不到源码 clang/ 子树 | llvm-lit 把 `bdir/bin/../../clang/...` 当源码路径 | 构建目录必须放在源码树内（`source_folder/build-ohos`），保证 bdir/../clang 指向源码 |

## 源码修改

无补丁文件（`patches_applied: []`）。build() 内的 config.guess stub、Platform/HarmonyOS.cmake、
lit 的 `CLANG` 环境变量、gtest `/tmp` 垫片均为**构建/测试环境 workaround**，未修改任何上游
源码或上游测试（与 clang/22.1.8、clang-format-11/11.1.0 同族做法）。

## 依赖版本

- 无第三方依赖（纯 LLVM/clang 源码自足构建）
- 运行时动态依赖系统 `libc++_shared.so`（OHOS SDK 系统库，R26 合规：包内不输出系统同名 .so）

## 验证结果（实测，非估算）

```bash
# 单测（上游 gtest，FormatTests）
$ build-ohos/tools/clang/unittests/Format/FormatTests
[==========] 1244 tests from 39 test suites ran. (42715 ms total)
[  PASSED  ] 1244 tests.

# lit（clang/test/Format 套件）
$ build-ohos/bin/llvm-lit -sv clang/test/Format
-- Testing: 32 tests, 8 workers --
Testing Time: 2.57s
Total Discovered Tests: 32
  Passed: 32 (100.00%)

# 打包二进制冒烟
$ ./bin/clang-format --version
clang-format version 22.1.8
$ printf 'int  main( ){return 0;}' | ./bin/clang-format -style=LLVM
int main() { return 0; }
```

**上游测试数字**：
- 单测 FormatTests：**1244/1244 通过（100%）**，0 失败（39 test suites）
- lit clang/test/Format：**32/32 通过（100%）**，0 失败，0 unsupported
- test_package 断言：3（`--version` 可执行；`-style=LLVM input.cpp` 输出逐字节 == expected.cpp；
  `--version` 含 `clang-format version 22.1.8`）
- conanfile.py build() 打印 `UPSTREAM TESTS: unit 1244/1244 passed, lit 32/32 passed — total passed 1276 failed 0`

**实测口径与退出码**（本地实跑，非估算）：

| 项目 | 用例数 | 通过 | 失败 | 通过率 | 退出码 |
|------|-------|------|------|--------|--------|
| 上游单测 FormatTests | 1244 | 1244 | 0 | 100% | 0 |
| 上游 lit `clang/test/Format`（Passed: 32） | 32 | 32 | 0 | 100% | 0 |
| test_package 消费者断言（格式化逐字节比较 + 版本） | 3 | 3 | 0 | 100% | 0 |
| **合计** | **1279** | **1279** | **0** | **100%** | — |

> 构建目录说明：探索/调试阶段用 `build-ohos`（`CLANG_FORMAT_22_WORKSPACE` 持久工作区，
> 便于断点续编）；conan 配方在未设该变量时用 `source_folder/build-ohos`。两者为同一套
> configure/构建步骤的两种命名，测试输出一致。

**本地 CI 模拟（W3 预审，ci/conan/build_and_test.sh 实跑，exit 0）**：

```
$ CI_PACKAGES=archives/c/clang-format/22.1.8.src CI_REPO_ROOT=<repo> \
    zsh ci/conan/build_and_test.sh archives/c/clang-format/22.1.8.src
G0_RESULT=pass
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=pass: clang-format --version OK
L4_RESULT=pass: no patches
L5_RESULT=pass: bin/ has content
  Total:   1 / Success: 1 / Failed: 0
  Pass rate: 100.0% (1/1)
W3_EXIT=0
```

关键中间行（真实日志 `reports/w3-local-ci.log`）：
`[ok] L1a: test_package was executed by conan create` /
`[ok] L1c: Upstream official tests (make check/ctest) executed in build phase` /
`[ok] L1e: Negative test confirmed — test genuinely depends on clang-format`（R34 破坏性反向验证）/
`tools.build:compiler_executables` 正常注入。

> 该次 W3 为**与 CI 完全一致的路径**（未设 `CLANG_FORMAT_22_WORKSPACE`，在 conan
> `source_folder` 内从零构建），构建日志见 `reports/w3-local-ci.log`；实测同样得到
> unit 1244/1244 + lit 32/32。

## 注意事项

- **LLVM 22 布局**：clang-format 在 `clang/tools/clang-format`（非 clang-tools-extra），
  单测在 `clang/unittests/Format`（目标名 `FormatTests`），lit 测试在 `clang/test/Format`。
- 构建目录必须位于源码树内（llvm-lit map_config 依赖 bdir/../clang）。
- **lit 必须提供 `CLANG`**（LLVM 22 起 `use_llvm_tool` 不搜 PATH）；否则 `llvm-lit` 首行 fatal。
- **单测需要可写 `cwd`**（gtest CapturedStream 经 `mkstemp` 写字面量 `/tmp/...`；垫片把它
  改写到 cwd）。若直接 `cd /` 之类不可写目录运行，会再次触发 SIGABRT。
- clang-format 为独立 CLI 工具，无需像 clang 编译器那样打包 crt/builtins/资源目录；
  仅需运行时系统 `libc++_shared.so`。
---

**编译结束**: 2026-09-18
**最终状态**: built
