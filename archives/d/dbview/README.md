# dbview

## 简介

dbview 是一个查看 dBase III / dBase III+ 数据库文件（`.dbf`）的命令行工具。它读取一个
DBF 文件，把记录内容、字段字典或文件头信息打印到标准输出，适合在终端里快速检查一个
DBF 文件的结构与内容，而不需要任何数据库引擎。

产物为单个命令行工具：`bin/dbview`（另附 `share/man/man1/dbview.1`）。

## 功能概述

- 默认视图：逐记录按 `字段名 : 字段值` 打印（值两端空白被去掉），记录之间空行分隔
- `-b, --browse`：dBase 浏览格式，每个字段输出原始定宽值并在其后追加分隔符
- `-t, --trim`：浏览模式下额外去掉字段值两端空白
- `-d, --delimiter`：设置浏览模式的分隔符（默认 `:`）
- `-e, --description`：打印字段字典（字段名、类型、长度、小数位）
- `-i, --info`：打印文件头信息（版本号、最后更新日期、记录数、头长度、记录长度）
- `-o, --omit`：只输出 `-e`/`-i` 的信息，不输出记录
- `-D, --deleted`：把删除标志为 `*` 的记录一并输出并标记
- `-r, --reserve`：保留字段名原文（默认把大写转小写、`_` 转空格）
- `-v, --version` / `-h` / `--help`：版本与帮助
- 支持 dBase III（版本字节 `0x03`）与 dBase III+（`0x83`）

## 使用方法

```sh
dbview data.dbf                  # 默认视图
dbview -b data.dbf               # 浏览格式
dbview -b -t -d '|' data.dbf     # 浏览格式，去空白，用 '|' 作分隔符
dbview -i -e data.dbf            # 文件头信息 + 字段字典
dbview -D data.dbf               # 连同已删除记录一起显示
dbview --version
```

## OHOS 适配

- **构建系统**：makefile。上游 Makefile 只有 `all/dbview/depend/install/clean/clobber`
  目标；`install` 目标以 `-o root -g root` 安装，并把字面量 `MAN=man` 当作 man page 的
  属主，因此在 OHOS 上不可用。配方不调用 `make install`，改用 profile 中的 clang 执行
  `make -j1 CC=<clang> CFLAGS=<profile flags>`，随后显式安装 `bin/dbview` 与
  `share/man/man1/dbview.1`。
- **源码补丁**（1 个，无平台条件编译）：
  1. `patches/0001-dbview.c.patch` 修正退出码语义。`db3_process()` 返回的是 TRUE/FALSE
     布尔值而不是进程退出码，`main()` 却直接 `exit()` 这个返回值，导致**查看成功时退出
     1、数据库打不开时反而退出 0**。取反后成功退出 0、失败退出 1，符合命令行工具的
     POSIX 约定（Debian 的 dbview 包带有同源 `negate_exit_code` 补丁，Debian 缺陷
     #439875「exit code on success should be zero」记录了该问题）。
- **上游测试**：1.0.4 不提供任何测试文件与 check/test 目标，按可审计台账记为上游 0；
  `test_package/` 补充 22 个消费者视角功能用例：`.dbf` 夹具是二进制文件，按仓库 CI 的检出约束**不随 PR 提交**，改由 `test_package/fixtures/make_fixtures.py` 在测试运行时逐字节确定性重建（生成脚本源码随 PR 提交、可审），再用人工核对的黄金 stdout 比对。
- **运行方式**：程序只用 stdio/fopen/fread/malloc，不访问 `/tmp`、locale 或任何特权接口，
  OHOS 上无需额外运行时配置。数据库文件路径由命令行给出，输出固定写 stdout。
- **已知上游限制（本次未修改）**：`db3_process()` 在 `db3_read_dic()` 失败时仍返回 TRUE，
  因此版本字节不受支持的文件（如 dBase IV `0x8B`）会打印诊断但退出码仍为 0；`main()`
  用 `strcpy()` 把数据库路径拷贝进 256 字节栈缓冲区，超长路径存在溢出风险。

## 依赖关系

- 编译依赖：C 编译器（profile 中的 `clang`），无第三方库。
- 运行依赖：`libc.so`（OHOS musl）。

## 参考资料

- 官方项目主页：https://www.infodrom.org/projects/dbview/
- 上游作者：Martin "Joey" Schulze（joey@infodrom.org）
- 许可证：GPL-2.0-or-later（上游 Makefile 声明 "either version 2 of the License, or (at
  your option) any later version"；发行 tarball 内不含 COPYING 文件）
