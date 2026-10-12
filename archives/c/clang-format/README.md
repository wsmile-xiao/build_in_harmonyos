# clang-format

LLVM clang-format 代码格式化命令行工具，鸿蒙 PC aarch64 原生构建。

- 上游：https://github.com/llvm/llvm-project （官方 release `llvmorg-22.1.8` tarball）
- 许可证：Apache-2.0 WITH LLVM-exception
- 构建系统：CMake + Ninja（Release，仅 AArch64 target）

## 功能概述

`clang-format` 是 LLVM 官方代码格式化工具，按可配置的样式规则自动排版 C/C++/Java/
JavaScript/TypeScript/Objective-C/Proto/TableGen 等源码，是广泛用于 CI 与编辑器集成的
事实标准格式化器。

- 多语言支持：C/C++/C#/Java/JS/TS/ObjC/Proto/TableGen/Verilog 等（后缀由 `lit.local.cfg` 定义）
- 样式体系：内置 `LLVM`/`Google`/`Chromium`/`Mozilla`/`WebKit`/`Microsoft`/`GNU` 等预设，
  并支持 `-style='{...}'` 内联 YAML 与 `.clang-format` 配置文件逐级继承
- 常用能力：`-i` 原地修改、`--dry-run`/`--Werror` 校验、`--lines` 行范围格式化、
  `--fallback-style`、`--output-replacements-xml`、`.clang-format-ignore`、`git-clang-format` 等

## 依赖关系

- **编译依赖**：无第三方依赖（纯 llvm-project 22.1.8 源码自足构建；仅需 CMake ≥3.20 与 Ninja）
- **运行时依赖**：系统 `libc++_shared.so`（OHOS 系统库，R26 合规——包内不输出系统同名 .so）

## 鸿蒙 PC 适配

**策略**：鸿蒙 PC 真机原生编译（不设 `CMAKE_SYSTEM_NAME` → 不触发交叉编译 →
`llvm-tblgen`/`clang-tblgen` 原生编+跑），与 `clang/22.1.8`、`clang-format-11/11.1.0` 同族。

- `llvm/cmake/config.guess` 不认 `uname -s=HarmonyOS` → build() 覆盖为 stub 输出
  `aarch64-unknown-linux-ohos`（config-ix.cmake 无条件调用它）。
- 提供 `Platform/HarmonyOS.cmake`（`include(Platform/Linux)`）挂到 `CMAKE_MODULE_PATH`。
- **LLVM 22 布局**：clang-format 位于 `clang/tools/clang-format`，单测
  `clang/unittests/Format`（目标 `FormatTests`），lit 测试 `clang/test/Format`；
  googletest 在 `third-party/unittest/googletest`。
- `LLVM_ENABLE_PROJECTS=clang` 即可；构建目标 `clang-format` + 上游测试基础设施
  （FileCheck/FormatTests/count/not/llvm-config）。
- 上游测试真实运行（R51）：单测 `FormatTests` 与 lit `clang/test/Format`，build() 打印
  `UPSTREAM TESTS` 统计行留痕。
- 运行时动态依赖系统 `libc++_shared.so`（R26 合规：包内不输出系统同名 .so）。

## 产物

- `bin/clang-format` — 主程序（独立 CLI 工具，`--version` / `-style=LLVM` 等标准用法）
- `bin/git-clang-format` — git 集成脚本（对 diff/暂存区做格式化，`git clang-format` 子命令）
- `share/clang/clang-format-diff.py` — 对 patch/diff 输入做格式化（供 CI 钩子使用）
- `share/clang/clang-format.py` / `clang-format-sublime.py` / `clang-format.el` /
  `clang-format-bbedit.applescript` — vim / Sublime / Emacs / BBEdit 编辑器集成脚本

（交付物清单与上游 `clang/tools/clang-format/CMakeLists.txt` 的 `install()` 规则一一对应；
上游 `clang-format-fuzzer` 为 `EXCLUDE_FROM_ALL` 且无 install 规则，不属于交付物。）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 22.1.8.src | built | 首个适配版本（conan create + test_package 通过） |

## 参考资料

- 官网 / 文档：https://clang.llvm.org/docs/ClangFormat.html
- 源码仓库：https://github.com/llvm/llvm-project （release tag `llvmorg-22.1.8`）
- Release 下载页：https://github.com/llvm/llvm-project/releases/tag/llvmorg-22.1.8
- 同族先例归档：`archives/c/clang/22.1.8`（clang 编译器）、`archives/c/clang-format-11/11.1.0`（LLVM 11 版）
