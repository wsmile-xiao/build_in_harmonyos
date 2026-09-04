# DRAFT: OHOS 上 Check 框架临时目录优先级 + musl netdb 特性宏（civetweb 1.16）

## 问题

适配 civetweb 1.16 上游测试套件（CMake CTest + Check 单元测试框架 0.11.0）时遇到两类
OHOS 特有阻塞，经查重知识图谱均为部分覆盖、存在新增差异，故按路径 B 建立本草稿。

## 一、Check 框架临时目录优先级（TEMP > P_tmpdir > TMPDIR）

### 真实证据（civetweb 1.16）

- 命令: `ctest -R "test-private-http-message"`（civetweb-build-test）
- 首个错误: `check_msg.c:317: Unable to create temporary file for communication; may not have permissions to do so`
- 退出码: 测试 Failed（Check srunner 通信管道创建失败）

### 根因

OHOS /tmp 只读（知识图谱 E002/E265 已覆盖 /tmp 只读本身）。但 Check 框架
`open_tmp_file()` 的临时目录选择顺序为：

1. `TEMP` 环境变量（优先级最高）
2. `P_tmpdir` 宏（通常编译为 /tmp）
3. `TMPDIR` 环境变量
4. 当前目录

由于 `P_tmpdir` 优先于 `TMPDIR`，仅设置 TMPDIR 时 mkstemp 仍落到只读 /tmp 而失败。
知识图谱 E265（fatsort：覆盖 SHELL/TMPDIR/FS_IMG 绕过 /tmp 只读）覆盖了 TMPDIR 方案，
但**未覆盖 Check 框架 TEMP 优先于 P_tmpdir/TMPDIR 的这一具体顺序**。

### 修复

```bash
export TEMP="$HOME/tmp/checktmp" && mkdir -p "$TEMP"
```

设置优先级最高的 TEMP 后，全量 ctest 50 用例 44/50 通过（6 个失败为 SSL 特性关停阻塞，
非本问题）。

## 二、OHOS musl netdb 特性宏保护（gethostbyname 隐式声明）

### 真实证据（civetweb 1.16）

- 命令: `cmake -DCIVETWEB_BUILD_TESTING=ON ... && make`（unittest/public_server.c）
- 首个错误: `public_server.c:83: error: incompatible integer to pointer conversion assigning to 'struct hostent *' from 'int'`（`gethostbyname` 隐式声明）

### 根因

OHOS musl 的 `netdb.h` 把 `gethostbyname`/`gethostbyname_r` 等传统解析函数声明放在
`#ifdef _DEFAULT_SOURCE` 分支内；未定义特性宏时函数不可见，clang 在 C99/C11 下把隐式
函数声明当作错误。知识图谱 E081 覆盖"musl 隐式函数声明"大类（secure_getenv→getenv
降级），但**未覆盖 gethostbyname + _DEFAULT_SOURCE 特性宏这一具体修复方式**。

### 修复

```bash
cmake -DCMAKE_C_FLAGS="-D_DEFAULT_SOURCE" ...
```

## 适用边界

- Check 框架：适用于任何以 Check 为单测框架、且环境 /tmp 只读的 OHOS 上游库
  （civetweb/unittest 直接命中；其他用 Check 的 C 库同理）
- musl netdb 特性宏：适用于任何在 OHOS（musl sysroot）下使用 gethostbyname 等
  传统 netdb API 的库/测试，编译报隐式声明时优先尝试 -D_DEFAULT_SOURCE（或 -D_GNU_SOURCE）

## 查重差异

- 与 E002（/tmp 只读，set-env-var TMPDIR）差异：本条目指明 Check 框架 TEMP 优先、
  仅设 TMPDIR 无效的具体机制
- 与 E265（fatsort 覆盖 SHELL/TMPDIR/FS_IMG）差异：E265 为具体包方案，本条目抽象出
  Check 框架通用顺序
- 与 E081（secure_getenv→getenv 源码降级）差异：E081 是改源码；本条目是特性宏编译标志，
  不改上游源码

## 关联库

civetweb 1.16（archives/c/civetweb/1.16）