# Pasco

Pasco 是 ODESSA（The Open Digital Evidence Search and Seizure Architecture）计算机取证套件里的一个
命令行工具，用来把 Windows Internet Explorer 的缓存/访问记录文件 `index.dat`（"Client Indexed Store"
格式）解析成一行一条、制表符（或 `-t` 指定分隔符）分隔的纯文本，方便直接导入表格软件做取证分析。

输出列为：`TYPE / URL / MODIFIED TIME / ACCESS TIME / FILENAME / DIRECTORY / HTTP HEADERS`。
它识别 `URL`、`LEAK`、`REDR` 三类活动记录，并支持 index.dat v4 / v5 / v5.2 三种版本头；
`-d` 走"undelete"路径（跳过哈希表，按 0x80 块步进直接扫记录），用于捞已删除条目。

## 功能概述

- 解析 Windows IE `index.dat`（缓存文件 / 访问历史 / Cookie 容器），输出可导入电子表格的分隔文本
- 支持 v4.0 / v5.0 / v5.2 结构（URL / LEAK / REDR 记录，哈希表链遍历）
- `-d` undelete 扫描（绕过哈希表，逐 0x80 块扫记录头）
- `-t <delim>` 自定义字段分隔符（默认 TAB）

## OHOS 适配

- 上游只有 `src/Makefile`（无 configure / CMake / Meson），且把编译器字面量写成 `gcc`；本平台只有
  `clang`（`/data/service/hnp/bin/clang`，无 `gcc`、无 `cc`）。补丁把命令行改成 `$(CC)`，其余保持上游原样。
- 上游 `install` 目标 `cp pasco ../bin`，而发行包内并不存在 `bin/` 目录（直接 cp 会落成一个名叫 `bin` 的
  文件）；补丁补了 `mkdir -p ../bin`。
- 无平台相关系统调用：只用 `open/close/pread/localtime/sprintf/pow` 等 POSIX 与 C 标准库，纯格式解析，
  因此不需要任何 `__OHOS__` 分支。
- 已知问题：上游源码 3 个 `int` 函数没有 `return`，且没 `#include <string.h>` 就用了 `strcpy/strncpy`；
  clang 15 只给 warning（clang 16+ 会升级成 error）。本次不改上游逻辑（R8），只在 notes 里记录。
- 输入文件是 Windows 专有取证样本，鸿蒙侧无可用的真实 `index.dat`；test_package 依据 `pasco.c` 里的
  偏移表合成最小合法样本做端到端断言（详见版本级 notes.md）。

## 依赖关系

- 编译依赖：clang + make（平台自带）
- 运行依赖：仅 libc / libm（`-lm -lc`）；Conan 层无 `requires`

## 参考资料

- 项目页：<https://sourceforge.net/projects/odessa/>（Pasco FRS 目录 `Pasco/20040505_1/`）
- 上游作者：Keith J. Jones（`Readme.txt`）
- 变更历史：发行包内 `CHANGES`
