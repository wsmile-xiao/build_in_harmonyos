# clang-format-11

LLVM clang-format 代码格式化命令行工具（v11.1.0），鸿蒙 PC aarch64 原生构建。

- 上游：https://github.com/llvm/llvm-project （官方 release `llvmorg-11.1.0` tarball）
- 许可证：Apache-2.0 WITH LLVM-exception
- 构建系统：CMake + Ninja（Release，仅 AArch64 target）

## 功能概述

`clang-format` 是 LLVM 官方代码格式化工具，按可配置的样式规则自动排版
C/C++/Java/JavaScript/Objective-C/Proto/TableGen 等源码，是广泛用于 CI 与编辑器集成的
事实标准格式化器。

- 多语言支持：由 `--assume-filename` / 文件后缀选择语言（C/C++/C#/Java/JS/TS/ObjC/Proto/TableGen 等）
- 样式体系：内置 `LLVM`/`Google`/`Chromium`/`Mozilla`/`WebKit`/`Microsoft`/`GNU` 等预设，
  支持 `-style='{...}'` 内联 YAML 与 `.clang-format` 配置文件逐级继承
- 常用能力：`-i` 原地修改、`--dry-run`/`--Werror` 校验、`--lines` 行范围格式化、
  `--fallback-style`、`--output-replacements-xml`、`-style=file` 等
- git 集成：`git-clang-format`（只格式化改动的行，见下）
- 编辑器/CI 集成：`share/clang/` 提供 vim / Emacs / Sublime / BBEdit / diff 脚本

## 鸿蒙 PC 适配

**策略**：鸿蒙 PC 真机原生编译（不设 `CMAKE_SYSTEM_NAME` → 不触发交叉编译 →
`llvm-tblgen` 原生编+跑），与 `clang/20.1.8` 同族。

- `config.guess` 不认 `uname -s=HarmonyOS` → build() 覆盖为 stub 输出
  `aarch64-unknown-linux-ohos`（config-ix.cmake 无条件调用它）。
- cmake 4.1.2 需 `CMAKE_POLICY_VERSION_MINIMUM=3.5`；提供
  `Platform/HarmonyOS.cmake`（`include(Platform/Linux)`）挂到 `CMAKE_MODULE_PATH`。
- **LLVM 11 布局**：clang-format 位于 `clang/tools/clang-format`（非
  clang-tools-extra），单测 `clang/unittests/Format`，lit 测试 `clang/test/Format`。
- `LLVM_ENABLE_PROJECTS=clang` 即可；构建目标 `clang-format` + 测试基础设施
  （FileCheck/FormatTests/count/not/llvm-config）。
- 上游测试真实运行（R51）：单测 **760/760** 通过（100%），lit **21/21** 通过
  （100%），build() 打印 `UPSTREAM TESTS` 统计行留痕。
- 运行时动态依赖系统 `libc++_shared.so`（R26 合规：包内不输出系统同名 .so）。

## 产物

交付物与上游 `clang/tools/clang-format/CMakeLists.txt` 的 `install()` 规则一一对应（全功能，非子集）：

- `bin/clang-format` — 主程序（独立 CLI，`--version` / `-style=LLVM` / `-i` / `--dry-run` 等标准用法）
- `bin/git-clang-format` — git 集成脚本（`git clang-format` 子命令，只格式化改动的行；Python 脚本，
  运行时需要 `python`/`python3`）
- `share/clang/clang-format-diff.py` — 对 patch/diff 输入做格式化（供 CI/提交钩子使用）
- `share/clang/clang-format.py` / `clang-format-sublime.py` / `clang-format.el` /
  `clang-format-bbedit.applescript` — vim / Sublime / Emacs / BBEdit 编辑器集成脚本

> 上游 `clang-format-fuzzer` 为 `EXCLUDE_FROM_ALL` 且无 `install()` 规则，不属于交付物。
> 运行时动态依赖系统 `libc++_shared.so`；`git-clang-format` 另需宿主提供 `python3` 与 `git`。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 11.1.0.src | built | 首个适配版本（conan create + test_package 通过；上游测试 781/781，交付物全覆盖，本地 CI 模拟 L0-L5 全过） |
