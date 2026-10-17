# libblzf

极速 LZF 数据压缩库（上游 liblzf）及 `lzf(1)` 压缩命令行工具。

- 上游：https://software.schmorp.de/pkg/liblzf.html（Marc Alexander Lehmann）
- 许可证：BSD-2-Clause OR GPL-2.0-or-later
- 类型：库 + 命令行工具（tool，产物含 `bin/lzf`）

## 功能概述

- LZF 压缩/解压：`lzf_compress` / `lzf_decompress`（见 `lzf.h`）
- `lzf(1)` 工具：文件与管道的压缩解压（`lzf [-dufhvb] [file ...]`）

## OHOS 适配

- Autotools 构建，预生成 `configure`，无需 autoreconf，无外部依赖。
- 只产出静态 `lib/liblzf.a`（上游不构建 `.so`），无系统库污染风险。
- 手写 `Makefile.in` 不支持 `DESTDIR`，`package()` 用 prefix 显式覆盖安装。
- 上游无测试套件；按 `no_tests` 口径输出 HMBS 标记，消费者测试在 `test_package/`（6 个 ctest 用例：5 API + 1 CLI）。

## 依赖

- 编译：系统 clang + sh/make；无外部 Conan 依赖
- 运行：静态库 + 单文件 CLI，无额外动态库

## 参考

- 上游主页：https://software.schmorp.de/pkg/liblzf.html
- 各版本详情见 `3.6.1/notes.md`
