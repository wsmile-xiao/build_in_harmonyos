# mpage 2.5.8 for HarmonyOS

## 概述

mpage 在 HarmonyOS/OpenHarmony (aarch64) 上的适配记录。mpage 用于将多页文本缩小
排列后在一张纸上打印（PostScript 输出）。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | mpage |
| 版本 | 2.5.8 |
| 官方主页 | https://www.mesa.nl/pub/mpage/ |
| 源码下载 | https://www.mesa.nl/pub/mpage/mpage-2.5.8.tgz |
| SHA-256 | `2351e91d25794b358df6618f17a7013a28d350ec20408fe06f8123dc4673fe93` |
| License | GPL-2.0-or-later |
| 构建系统 | plain Makefile（无 configure） |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS PC (OHOS 6.0) |
| 架构 | aarch64 (armv8) |
| 编译器 | clang 15.0.4 (target `aarch64-unknown-linux-ohos`) |
| libc | musl (`/lib/ld-musl-aarch64.so.1`) |

## 适配说明

mpage 2.5.8 是纯 Makefile 项目，Makefile 硬编码 `CC=gcc`、`CFLAGS=-O2 -s ...`、
`PREFIX=/usr/local`。OHOS 上**无源码改动**，仅在 make 命令行覆盖：

```bash
make -j1 CC=clang PREFIX="<package_folder>"
```

- `CC=clang`：OHOS 工具链无 gcc，必须指定 clang。
- `PREFIX=<package_folder>`：将安装布局重定向到 Conan 包目录。
- `-j1`：Makefile 为顺序 `.o → link`，并行 `-jN` 在 OHOS 受限挂载上触发
  `jobserver mkfifo: Operation not permitted`。
- **零补丁**（`patches: []`）。K&R 风格非原型函数定义在 clang 15 下仅产生 46 条
  `-Wdeprecated-non-prototype` 警告，无错误。

## 上游测试审计

- `Makefile` / `smakefile` / `smakefile.ppc` 均无 `test`/`check` 目标。
- `Test/` 目录仅含 4 个示例输入文件（`All.chars`/`nonl`/`tabtest`/`testpage`），
  无测试驱动脚本、无期望输出、无 Makefile 目标引用它们。
- 无 `tests/`、无 autotools `make check`、无 gtest、无 CI 流水线。
- 结论：**上游无任何自动化测试套件**，已在 `test_package/MANIFEST.yml` 如实声明。

## test_package 设计

消费者测试向打包好的 `mpage` 喂入最小文本输入并校验 PostScript 输出：

1. `mpage -V` → stderr 含 `mpage version 2.5.8`。
2. `mpage sample.txt` → stdout 为 `%!PS-Adobe-2.0` PostScript 流。
3. `%%Creator:` 行含 `mpage 2.5.8 May 2023`。
4. `%%DocumentMedia:` 行含默认页面 `A4`。

详见 [2.5.8/notes.md](./2.5.8/notes.md)。
