# malbolge

## 简介

Malbolge 是 Ben Olmstead 于 1998 年设计的异构编程语言（esoteric programming language），以但丁《神曲》中地狱第八圈命名。其设计目标是"尽可能难以编写与理解"，被认为是已知最难编程的图灵完备语言之一。本包提供官方参考解释器。

## 功能概述

- `malbolge <file.mal>` — 执行 Malbolge 程序文件
- 无 `--help` / `--version` 选项：命令行接口极简（`argc != 2` 时报 `invalid command line`）
- 程序文件不存在时报 `can't open file`
- 源文件含非法字符时报 `invalid character in source file`
- 输入文件过长（>59049 字符）时报 `input file too long`

## OHOS 适配

- 上游为单个 `malbolge.c` 源文件（public domain），无 tarball / 无 Makefile / 无构建系统 / 无测试套件。配方 `source()` 用 `tools.files.get()` 下载官方 `.c` 文件，`build()` 直接调用从 Conan conf `tools.build:compiler_executables` 动态取得的 C 编译器编译单文件（`clang -O2 -o malbolge malbolge.c`）。
- 不硬编码编译器路径、SDK 版本或 Worker 路径：编译器一律从 `tools.build:compiler_executables` 取，缺省回退 `clang`（on PATH）。
- 上游无任何 Makefile 写死 gcc/g++/cc 的问题（无 Makefile），无需补丁。
- 上游无任何测试套件（见版本级 `manifest.yaml` knowledge_gained 与 `test_package/MANIFEST.yml` 上游测试审计），test_package 以可执行文件真实运行 + 官方 `nop.mal` 示例程序冒烟测试接入。test_package 共 5 项检查：①无参数 → `invalid command line` 退出 1；②不存在文件 → `can't open file` 退出 1；③非法字符源文件 → `invalid character in source file` 退出 1；④官方 `nop.mal`（Ben Olmstead，2 字节 `DP`）执行后立即终止、退出 0、无输出；⑤以 `nop.mal` 的 `DP` 核心包裹空白（space/tab/newline）生成纯 ASCII 临时 fixture，验证 reference loader 跳过非指令字符、立即终止、退出 0、无输出且 stderr 不出现 `invalid character`。全部 fixture 为纯 ASCII，不依赖外部 `timeout`（5 个输入均确定终止）。

## 依赖关系

- 编译依赖：无（仅需 C 编译器 + libc）
- 运行依赖：无

## 参考资料

- 官网/源码: https://esoteric.sange.fi/orphaned/malbolge/
- 源文件: https://esoteric.sange.fi/orphaned/malbolge/malbolge.c
- License: public domain（源码头注释明确声明：*"I hereby place it in the public domain"*）
- Homebrew formula: https://github.com/Homebrew/homebrew-core/blob/HEAD/Formula/m/malbolge.rb（同源、同版本 0.1.0、同 sha256）
