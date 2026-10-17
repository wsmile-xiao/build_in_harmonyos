# clang-format-11 11.1.0.src 适配笔记（HarmonyOS PC · aarch64）

## Summary

- 将 LLVM clang-format 11.1.0（clang-format 代码格式化 CLI 工具）从官方 llvm-project 源码
  构建为鸿蒙 PC aarch64 原生可执行文件。
- 上游版本：11.1.0（release tag `llvmorg-11.1.0`）
- 上游仓库：https://github.com/llvm/llvm-project （官方 release tarball）
- 构建方式与 clang/20.1.8 同族策略：鸿蒙 PC 真机原生编译，不设 CMAKE_SYSTEM_NAME → 不触发
  交叉编译 → llvm-tblgen 原生编+跑。

## 编译环境

- 构建系统: CMake + Ninja（Release，仅 AArch64 target）
- 编译器: /data/service/hnp/bin/clang / clang++（设备 hnp 工具链，clang 15）
- cmake 4.1.2 / ninja 1.13.1
- 目标三元组: aarch64-unknown-linux-ohos
- 状态: built（conan create + test_package 通过）

## 编译步骤

1. 解压 `llvm-project-11.1.0.src.tar.xz`（sha256=74d2529159fd118c3eac6f90107b5611bccc6f647fdea104024183e8d5e25831，
   84,065,492 字节）。
2. `cmake -S llvm -B build-probe`（LLVM 11 布局：clang-format 在 `clang/tools/clang-format`，
   `LLVM_ENABLE_PROJECTS=clang`），配置参数见 manifest.yaml。
3. `cmake --build build-probe --target clang-format FileCheck FormatTests count not llvm-config -j 8`。
4. 上游测试实跑（R51）：单测 `FormatTests` + lit `clang/test/Format`。
5. 打包：只收 `bin/clang-format` + `LICENSE.TXT`（application，bindirs=bin）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake 4.1.2 报 "Compatibility with CMake < 3.5 has been removed" | LLVM 11 `cmake_minimum_required` 版本过旧，cmake 4.x 强制 policy 兼容 | 环境变量 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（conanfile build() 内 os.environ 注入） |
| 2 | `config-ix.cmake` 无条件调用 `config.guess` 报 "unable to guess system type"（FATAL） | 设备 `uname -s=HarmonyOS`，2011 版 config.guess 不认 | build() 覆盖 `llvm/cmake/config.guess` 为 stub：`#!/bin/sh\necho aarch64-unknown-linux-ohos` |
| 3 | cmake 提示 "System is unknown to cmake, create Platform/HarmonyOS" | cmake 无 HarmonyOS 平台模块，UNIX 变量未置 | 提供 `Platform/HarmonyOS.cmake`（`include(Platform/Linux)`）挂到 `CMAKE_MODULE_PATH`，保持 native（不设 CMAKE_SYSTEM_NAME） |
| 4 | lit 运行报 "fatal: Did not find count in .../bin" | `count`/`not`/`llvm-config` 等测试工具未随指定目标构建 | 目标列表补 `count not llvm-config FileCheck` |
| 5 | lit `map_config` 找不到源码 clang/ 子树 | llvm-lit 脚本把 `bdir/bin/../../clang/...` 当源码路径 | 构建目录必须放在源码树内（`source_folder/build-ohos`），保证 bdir/../clang 指向源码 |
| 6 | lang-preflight 报 mixed（exit 2） | llvm-project monorepo 根无顶层 CMakeLists.txt → c/cpp 族 manifest 判定被跳过；且统计含 lldb/python、openmp/compiler-rt(C) 等非构建子项目 | 判定为工具对 monorepo 布局的误报：构建相关子树 llvm 95% cpp、clang-tools-extra 96% cpp，按 R47/E13「C/C++ 混编按主体判不算 mixed」本包为 cpp；本任务为 C++ 工具按 cpp 流程完成适配（详见最终报告） |

## 源码修改

无补丁文件（build() 内的 config.guess stub 与 Platform/HarmonyOS.cmake 均为构建环境
workaround，非源码逻辑改动，与 clang/20.1.8 同族做法）。

## 依赖版本

- 无第三方依赖（纯 LLVM/clang 源码自足构建）
- 运行时动态依赖系统 `libc++_shared.so`（OHOS SDK 系统库，R26 合规：包内不输出系统同名 .so）

## 验证结果

```bash
# 单测（上游 gtest，FormatTests）
$ build-probe/tools/clang/unittests/Format/FormatTests
[==========] 760 tests from 21 test cases ran. (11893 ms total)
[  PASSED  ] 760 tests.

# lit（clang/test/Format 套件）
$ build-probe/bin/llvm-lit -sv clang/test/Format
-- Testing: 21 tests, 20 workers --
Testing Time: 1.22s
  Passed: 21

# 打包二进制冒烟
$ ./bin/clang-format --version
clang-format version 11.1.0
$ printf 'int  main( ){return 0;}' | ./bin/clang-format -style=LLVM
int main() { return 0; }
```

**上游测试数字**：
- 单测 FormatTests：760/760 通过（100%），0 失败
- lit clang/test/Format：21/21 通过（100%），0 失败
- test_package 断言：5（`--version` 可执行 1 + input.cpp 格式化逐字节比较 1 + 版本号 grep 1
  + bin/git-clang-format 可执行/本体/语法 1 + share/clang/* 交付物齐全 1）
- conanfile.py build() 打印 `UPSTREAM TESTS: ...` 统计行供 CI L1c 留痕

**实测口径与退出码**（本地实跑，非估算）：

| 项目 | 用例数 | 通过 | 失败 | 通过率 | 退出码 |
|------|-------|------|------|--------|--------|
| 上游单测 FormatTests (`assertions=760 failures=0`) | 760 | 760 | 0 | 100% | 0 |
| 上游 lit `clang/test/Format`（Passed: 21） | 21 | 21 | 0 | 100% | 0 |
| test_package 消费者断言（见上，5 项） | 5 | 5 | 0 | 100% | 0 |
| **合计** | **786** | **786** | **0** | **100%** | — |

> 构建目录说明：探索阶段用 `build-probe`、conan 配方内用 `source_folder/build-ohos`，
> 两者为同一套 configure/构建步骤的两种命名，测试输出一致。

**全功能 e2e（消费者视角，使用打包交付物，16/16 通过）**：

| # | 功能面 | 命令要点 | 结果 |
|---|--------|----------|------|
| 1 | 版本 | `bin/clang-format --version` | `clang-format version 11.1.0` |
| 2 | 多语言 | `--assume-filename=` C++/Java/JS/ObjC/Proto/TableGen | 6/6 成功 |
| 3 | 样式体系 | `-style=LLVM` / `Google` / 内联 YAML / `-style=file`（`.clang-format`） | 全部生效且输出互异 |
| 4 | 原地修改 | `-i` | 文件被就地格式化 |
| 5 | CI 校验 | `--dry-run --Werror` | 脏文件退出码 1 / 已格式化 0 |
| 6 | 行范围 | `--lines=1:1` | 仅第 1 行被格式化 |
| 7 | 替换集 | `--output-replacements-xml` | 输出 `<replacements …>` XML |
| 8 | 配置导出 | `--dump-config` | 输出完整样式键值 |
| 9 | 回退样式 | `-style=file --fallback-style=LLVM`（无 `.clang-format`） | 正常回退格式化 |
| 10 | 头文件排序 | `--sort-includes` | `<b.h>,<a.h>` → `<a.h>,<b.h>` |
| 11 | diff 集成 | `share/clang/clang-format-diff.py -p1`（管道输入 diff） | 输出格式化后的 diff |
| 12 | git 集成 | `git clang-format --diff` / `--force`（真实 git 仓库，仅改动行） | rc=0，工作区改动行被格式化 |
| 12b | git 保护行为 | `git clang-format`（有未暂存改动且未 `--force`） | rc=2 并提示 stage/stash（上游正确行为） |
| 13 | CLI 可用性 | `git-clang-format --help` | 输出 `usage: git clang-format [OPTIONS]` |
| 14 | 交付物齐全 | 7 项（对齐上游 `install()` 规则） | 全部在位 |
| 15 | 制品洁净 | 包内 `__pycache__`/`*.pyc` 检查 | 无（语法校验改用内存 `compile()`） |

**本地 CI 模拟（W3 预审，ci/conan/build_and_test.sh 实跑）**：

```
CI_PACKAGES=archives/c/clang-format-11/11.1.0.src   CI_BRANCH=feat/clang-format-11-11.1.0.src
→ G0_RESULT=pass / KC_RESULT=pass / JC_RESULT=pass
→ L0_RESULT=pass: all checks passed
→ L1_RESULT=pass: upstream tests + test_package executed
→ L2_RESULT=pass: clang-format --version OK, git-clang-format --help OK
→ L4_RESULT=pass: no patches
→ L5_RESULT=pass: bin/ has content
→ Pass rate: 100.0% (1/1)
```

**交付物清单**（逐条对齐上游 `clang/tools/clang-format/CMakeLists.txt` 的 `install()` 规则）：

| 交付物 | 上游安装规则 |
|--------|--------------|
| `bin/clang-format` | `add_clang_tool(clang-format)` |
| `bin/git-clang-format` | `install(PROGRAMS … DESTINATION bin)` |
| `share/clang/clang-format-diff.py` | `install(PROGRAMS … DESTINATION share/clang)` |
| `share/clang/clang-format.py` | 同上（vim 集成） |
| `share/clang/clang-format-sublime.py` | 同上（Sublime 集成） |
| `share/clang/clang-format.el` | 同上（Emacs 集成） |
| `share/clang/clang-format-bbedit.applescript` | 同上（BBEdit 集成） |

> 上游 `clang-format-fuzzer` 为 `EXCLUDE_FROM_ALL` 且无 `install()` 规则，非交付物。
> 运行时依赖：系统 `libc++_shared.so`；`git-clang-format` / `clang-format-diff.py` 为 Python
> 脚本（shebang `#!/usr/bin/env python`），另需宿主提供 `python`（或 `python3`）与 `git`。

**上游测试修改情况**：未修改任何上游测试文件（`patches_applied: []`，无 `patches/` 目录）。

## 注意事项

- **LLVM 11 布局与新版不同**：clang-format 在 `clang/tools/clang-format`（非
  clang-tools-extra），单测在 `clang/unittests/Format`（目标名 `FormatTests`），
  lit 测试在 `clang/test/Format`（.cpp RUN 行风格，非 .test 文件）。
- 构建目录必须位于源码树内（llvm-lit map_config 依赖 bdir/../clang），conan 配方中为
  `source_folder/build-ohos`。
- **交付物必须收全**：上游 `install()` 除主程序外还装 `bin/git-clang-format` 与 5 个
  `share/clang/*` 脚本；只打 `bin/clang-format` 属交付物缺项（本包已按全量收齐并加断言）。
- clang-format 为独立 CLI 工具，无需像 clang 编译器那样打包 crt/builtins/资源目录；
  仅需运行时系统 libc++_shared.so。
- `clang-format-diff.py` 会把 diff 头部中的文件名传给 clang-format，故按 diff 输入时该文件
  需存在于当前目录（上游脚本行为）。
---

**编译结束**: 2026-09-17 20:02
**最终状态**: built
