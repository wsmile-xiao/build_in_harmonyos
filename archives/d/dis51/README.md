# dis51

## 简介

dis51 是一个面向 Unix 类系统的 8051 微控制器反汇编器。它从标准输入读取 Intel HEX
格式的目标文件，从命令行给出的入口地址出发跟踪分支与调用，把可达地址标记为代码，
其余为数据，向标准输出生成可在任意标准 8051 汇编器上汇编的汇编语言文件（数据部分
用 `DB` 指令表示）。对常见的 SFR 与位地址，输出会使用符号名（如 `P1`、`SBUF`、
`EA`）而不是裸地址。

产物为单个命令行工具：`bin/dis51`。

## 功能概述

- Intel HEX 输入解析（32 位地址扩展记录、校验和检查）
- 从命令行入口地址出发的两遍反汇编：pass 1 跟踪代码并给跳转目标分配标签，pass 2 输出汇编
- 多入口地址：对间接跳转 `JMP @A+DPTR` 造成的跳转表，可多次给出入口地址分段反汇编
- SFR / SFR 位地址符号化（`P0`~`P3`、`PSW`、`ACC`、`B`、`IE`、`IP`、`TCON`、`TMOD`、
  `SCON`、`SBUF`、`PCON`、`P1.0`、`EA`、`TR0` 等）
- `-l` 列表模式：每条指令前附带地址与该指令的原始字节，并给出 `DB` 的 ASCII 注释
- 唯一的非法操作码 `A5` 会给出诊断并降级为数据

## 使用方法

```sh
dis51 < input.hex > output.asm          # 默认从地址 0 开始反汇编
dis51 -l < input.hex > output.lst       # 列表模式（地址 + 字节）
dis51 16 < input.hex                    # 从入口地址 16（十进制）开始
dis51 -l 0x100 0x200 < input.hex        # 列表模式，入口地址可用 0x 前缀
dis51 --version
dis51 --help
```

## OHOS 适配

- **构建系统**：makefile。上游 Makefile 只有 `default/dis51/shared/clean` 目标，没有
  configure 与 install，配方用 `make -j1 CC=<profile clang>` 构建后显式安装
  `bin/dis51`（与 `licenses/COPYING`）。
- **源码补丁**（3 个，全部为上游缺陷修复与 CLI 可测性补充，无平台条件编译）：
  1. `pass2.c` 用字面量格式串调用 `fprintf`，消除 `-Wformat-security`；
  2. `global.c` 的 `lbl[]` 定义与 `global.h` 声明对齐为 `unsigned short`（标签数超过
     32767 时不再变负）；
  3. `main.c` 在读取标准输入之前处理 `--version`/`--help`，使 CLI 通过 L2 smoke test
     且不会因为等待 HEX 输入而失败。
- **上游测试**：0.5 不提供任何测试文件与 check/test 目标，按可审计台账记为上游 0；
  `test_package/` 补充 12 个消费者视角功能用例（Intel HEX 夹具 + 人工核对的黄金清单）。
- **运行方式**：程序只走 stdin/stdout，没有临时目录、locale 或特权要求，OHOS 上无需
  额外运行时配置。

## 依赖关系

- 编译依赖：C 编译器（profile 中的 `clang`），无第三方库。
- 运行依赖：`libc.so`（OHOS musl）。

## 参考资料

- 官方发布页：https://plit.de/asem-51/dis51.html
- 上游作者：David Sullins（djs@naspa.net），0.5 发布于 2003-11-21
- 许可证：GPL-2.0-only
