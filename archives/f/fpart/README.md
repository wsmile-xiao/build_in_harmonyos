# fpart

文件分区工具 — 按大小、文件数量或自定义分区数对文件系统中的文件进行排序和打包。

## 基本信息

- **官网**: http://contribs.martymac.org
- **作者**: Ganael LAPLANCHE <ganael.laplanche@martymac.org>
- **许可**: BSD 2-Clause
- **构建系统**: autotools

## 描述

fpart 是一个文件分区工具，它可以帮助用户将文件系统中的文件按照大小、文件数量或指定分区数进行排序和分组。主要功能：

- 按分区数 (`-n`)、文件数量 (`-f`) 或大小 (`-s`) 限制分区
- 支持实时模式（`-L`），在遍历文件系统时即时生成分区
- 支持前置/后置分区钩子命令（`-w`/`-W`）
- 输出分区到文件模板（`-o`）
- 包含/排除模式过滤（`-y`/`-x`）
- 附带 fpsync 工具，用于使用 fpart 并行同步目录

## OpenHarmony 适配说明

- musl libc 不提供 fts.h，需使用 `--enable-embfts` 启用嵌入式 fts 实现
- HMDFS 文件系统需修改 configure 中 `umask 077` 为 `umask 022`（E011）
- GitHub 源码包需先 `autoreconf -fi` 生成构建文件
