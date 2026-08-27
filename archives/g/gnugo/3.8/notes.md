# GNU Go 3.8 编译笔记

## 编译过程摘要

GNU Go 3.8 是一个围棋游戏引擎，使用 autotools 构建系统。

### 关键步骤

1. **下载源码**：从 GNU FTP 服务器下载 gnugo-3.8.tar.gz
2. **解决平台限制**：
   - `/tmp` 只读文件系统，需要设置 TMPDIR=~/tmp
   - HMDFS 文件系统限制，config.status 无法在当前目录创建临时目录，需要修改脚本
3. **修复编译错误**：
   - 重复符号错误：meaningless_black_moves 和 meaningless_white_moves
   - 解决方案：将 liberty.h 中的变量定义改为 extern 声明，在 unconditional.c 中添加实际定义
4. **编译和安装**：
   - `./configure --prefix=$DEFAULT_PREFIX`
   - `make -j1`
   - `make install DESTDIR=$TEST_PREFIX`
5. **功能测试**：`make check` 执行回归测试
6. **预编译包制作**：手动打包（strip、签名）
7. **本地安装验证**：`make install`（不带 DESTDIR）

## 遇到的问题及解决方案

### 问题 1：HMDFS 文件系统限制

**问题描述**：
- configure 脚本尝试在 `/tmp` 创建临时文件，但 `/tmp` 是只读文件系统
- config.status 尝试在当前目录创建临时目录（如 `./confXXXXXX`），但 HMDFS 文件系统不允许

**解决方案**：
- 设置 TMPDIR 环境变量：`export TMPDIR=~/tmp`
- 修改 config.status 脚本，使其在 TMPDIR 中创建临时目录

**影响范围**：
- 这是 HarmonyOS/HMDFS 平台的通用问题，所有 autotools 构建的软件都可能遇到

### 问题 2：重复符号错误

**问题描述**：
```
ld.lld: error: duplicate symbol: meaningless_black_moves
>>> defined at liberty.h:860 (mkpat.o)
>>> defined at liberty.h:860 (dfa.o)

ld.lld: error: duplicate symbol: meaningless_white_moves
>>> defined at liberty.h:861 (mkpat.o)
>>> defined at liberty.h:861 (dfa.o)
```

**解决方案**：
- 将 `liberty.h` 中的变量定义改为 extern 声明：
  ```c
  extern int meaningless_black_moves[BOARDMAX];
  extern int meaningless_white_moves[BOARDMAX];
  ```
- 在 `unconditional.c` 中添加实际定义：
  ```c
  int meaningless_black_moves[BOARDMAX];
  int meaningless_white_moves[BOARDMAX];
  ```

**根本原因**：
- 原始代码在头文件中直接定义全局变量（而非 extern 声明）
- 多个源文件包含该头文件时，每个都会定义这些变量，导致链接时重复符号错误
- 这是一个典型的 C 语言编程错误，违反了"头文件只声明，源文件定义"的原则

### 问题 3：ncurses 未检测到

**问题描述**：
- configure 未检测到 ncurses/curses.h，导致无彩色输出支持

**解决方案**：
- 不影响核心功能，跳过此问题
- gnugo 可以正常运行，只是缺少彩色终端输出

## 补丁说明

### 0002-engine-liberty.h.patch

修改 `engine/liberty.h`，将全局变量定义改为 extern 声明：
- `int meaningless_black_moves[BOARDMAX]` → `extern int meaningless_black_moves[BOARDMAX]`
- `int meaningless_white_moves[BOARDMAX]` → `extern int meaningless_white_moves[BOARDMAX]`

### 0001-engine-unconditional.c.patch

修改 `engine/unconditional.c`，在 `#include "liberty.h"` 后添加变量定义：
```c
/* Unconditionally meaningless moves - defined here as declared extern in liberty.h */
int meaningless_black_moves[BOARDMAX];
int meaningless_white_moves[BOARDMAX];
```

## 编译统计

- 编译时间：约 5 分钟
- 编译警告：约 100+ 个（大部分为旧式 C 函数声明警告）
- 编译错误：1 个（重复符号）
- 安装文件大小：7.5MB（strip 后）
- 预编译包大小：8.1MB

## 功能验证

- `gnugo --version` 输出正确：GNU Go 3.8
- `make check` 执行回归测试：13 个测试套件
- 本地安装验证：成功

## 知识提取记录

### L1 平台真理（应写入 knowledge/）

1. **HMDFS config.status 临时文件限制**
   - HMDFS 文件系统不允许在当前目录创建临时目录
   - autotools 的 config.status 脚本使用 `mktemp -d "./confXXXXXX"` 创建临时目录
   - 解决方案：修改 config.status 使用 TMPDIR 创建临时文件
   - 影响范围：所有 autotools 构建的软件

2. **重复符号问题模式**
   - 头文件中直接定义全局变量会导致重复符号错误
   - 正确做法：头文件中使用 extern 声明，源文件中定义
   - 这是常见的 C 语言编程错误

---

**编译结束时间**：2026-06-16 10:57
**最终状态**：built（编译成功，已验证）
---

**编译结束**: 2026-08-27 12:12
**最终状态**: built
