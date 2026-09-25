# unzoo 4.4 — HarmonyOS PC (aarch64) 适配笔记

- 上游：unzoo — zoo 归档解包器，Martin Schoenert（基于 Rahul Dhesi 的 booz 2.0）
- 版本：4.4（源码 `@(#)$Id: unzoo.c,v 4.4 2000/05/29 08:56:57 sal Exp $`）
- 许可证：**Public Domain**（源码头部第 7 行原文
  `*Y  This file is in the Public Domain.`）
- 构建系统：**无**。整份分发就是一个 `unzoo.c`；唯一的构建指示是源码头部注释
  `cc -o unzoo -DSYS_IS_UNIX -O unzoo.c`（可选加 `-DSYS_HAS_MKDIR`）
- 依赖：**无**
- 包形态：`bin/unzoo`（应用包 → 软件级 commands.json，R38）
- 状态：**READY_FOR_HARMONY** —— WSL 侧已跑通完整 `conan create`（见 §6），
  HarmonyOS 真机 conan create 尚未执行

## 1. 源码来源（原始地址已失效）

所有下游打包者（Fedora / Mageia / Fink / NetBSD pkgsrc / AUR）引用的上游地址都是：

```
http://archives.math.utk.edu/software/multi-platform/gap/util/unzoo.c
```

**2026-09-20 实测该地址已失败**（HTTP 502 / 连接失败）。改用：

```
https://archive.debian.org/debian/pool/main/u/unzoo/unzoo_4.4.orig.tar.gz
```

这是 Debian 的 **pristine 上游打包**（`.orig.tar.gz` 按定义即未经修改的上游源码），
内含且仅含一个 `unzoo.c`（115328 字节，2002-05-06），**不含任何 Debian 补丁**
（Debian 自己的 strncpy/strncat 等补丁在 `debian/patches/` 里，不在 orig 包里）。

本仓库已有同类先例：cauchy（Bitbucket 上游失效 → 用 Ubuntu orig 包）、
libpipeline（同时列 Debian 与 gnupg 官方源）。此处如实记录，供评审判断。

## 2. 平台适配点（2 个补丁）

### 2.1 缺失的系统头文件（`0001`，第一处）

`unzoo.c` 只 include 了 `<stdio.h>`（其余 include 都在别的 `SYS_IS_*` 分支里），
而 `SYS_IS_UNIX` 分支实际使用了：

| 函数 | 需要 |
|---|---|
| `malloc()` / `free()` | `<stdlib.h>` |
| `strcpy()` / `strcat()` | `<string.h>` |
| `mkdir()` / `chmod()` | `<sys/stat.h>` |
| `utime()` | `<utime.h>` |

全部是隐式声明。**GCC 14+ 默认把 `-Wimplicit-function-declaration` 升级为
error**，C23 更是正式删除该语法 —— 实测：

```
$ gcc -O2 -DSYS_IS_UNIX -DSYS_HAS_MKDIR -o unzoo unzoo.c
unzoo.c:508:33: error: implicit declaration of function 'strcpy'
unzoo.c:1225:9: error: implicit declaration of function 'strcat'
unzoo.c:580:33: error: implicit declaration of function 'mkdir'
unzoo.c:617:58: error: implicit declaration of function 'utime'
unzoo.c:649:35: error: implicit declaration of function 'chmod'
```

### 2.2 `utime()` 的 LP64 缺陷（`0001`，第二处）

UNIX 分支原来是：

```c
unsigned int   Secs [2];
#define SETF_TIME(patl,secs)    (Secs[0]=Secs[1]=(secs),!utime((patl),Secs))
```

这是 V7 时代 `time_t times[2]` 原型的写法。POSIX `utime()` 收
`struct utimbuf *`，而在 LP64 目标（x86_64、aarch64/OHOS）上 `time_t` 是
**64 位**、`unsigned int` 是 32 位 —— `utime()` 会从一个 8 字节对象里读出
16 字节，写进错误的时间戳。改为与同文件 OS2_EMX 分支一致的写法：

```c
struct  utimbuf Secs;
#define SETF_TIME(patl,secs)    (Secs.actime=Secs.modtime=(secs),!utime((patl),&Secs))
```

### 2.3 没有构建文件（`0002`）

补丁新增 `GNUmakefile`，把头部注释里的编译指示翻成 GNU make 规则，并带上
`-DSYS_IS_UNIX -DSYS_HAS_MKDIR`；编译器与标志取自 Conan toolchain 环境
（`$(CC)` / `$(CPPFLAGS)` / `$(CFLAGS)` / `$(LDFLAGS)`），不写死 `cc`（R33）。

> 新增文件补丁用 `diff -u /dev/null b/GNUmakefile` 的 `/dev/null` 约定，
> 否则 `patch -p1` 会非交互地停下来问 `File to patch:`。

## 3. 上游测试清点（R51 三步法第 1 步）

| 项 | 值 | 依据 |
|---|---|---|
| `upstream_test_targets` | **0** | 分发只有一个 .c 文件，无任何构建/测试目标 |
| `upstream_test_files` | **0** | 无测试源文件、无测试数据 |
| `upstream_case_total` | **0** | 上游不提供用例。**确认的 0**，不是 UNKNOWN |

## 4. 我们补的验证：真实 zoo 归档往返

`test_package/conanfile.py` 现场构造一个符合 zoo 规范的归档并跑完整流程。
构造过程中逐条撞出来、并且都实测复现过的格式细节：

| # | 现象 | 原因 |
|---|---|---|
| 1 | 报 `found bad directory entry in archive`（成员本身完全正确） | 目录遍历**靠 `posnxt == 0` 的结束项终止**，不是靠 EOF（unzoo.c:2392-2398）。缺结束项必然报错 |
| 2 | 报 `unknown method, you need a later version` | 目录项 `majver=2` 且 `minver>1` 被拒（unzoo.c:2570）；minver 必须写 0 |
| 3 | 字段读出来全是错的 | 多字节字段是**小端**（`WordReadArch` 把第 0 字节放进 bit 0-7） |
| 4 | `error, CRC failed` | CRC 是**反射 CRC-16**（poly `0xA001`、初值 0、无末尾异或），与 `CRC_BYTE` 宏一致 |

四项断言（实测结果）：

```
$ unzoo -l good.zoo
Length    CF  Size Now  Date      Time
--------  --- --------  --------- --------
      36   0%       36   0     80 00:00:00   HELLO.TXT
--------  --- --------  --------- --------
      36   0%       36     1 files                       rc=0

$ unzoo -x good.zoo
HELLO.TXT 	-- extracted as binary                     rc=0
$ cmp HELLO.TXT <payload>       → 一致
```

> `extracted` 这一行本身就是 CRC 通过的证据：unzoo 只在
> `Crc == Entry.crcdat` 时才打印它，否则打印 `error, CRC failed`。

## 5. 观察到的上游缺陷（不修，仅记录）

`unzoo.c:1481`：`BlckReadArch(Descript.text,20L); Descript.text[20] = '\0';`
—— 对 `char text[20]` 写越界一字节（落在同一结构体紧接着的字段上）。
属上游既有缺陷，与本次适配无关，本配方不修改。

## 6. 补充：WSL 侧完整 `conan create` 实测（本机原生 Linux profile）

| 现象 | 根因 | 修法 |
|---|---|---|
| `source()` 抛 `Can't untar a tgz containing files in the root with strip_root enabled` | Debian 的 orig 包把 `unzoo.c` 放在压缩包**根目录**（没有顶层目录） | 去掉 `strip_root=True`；与 triangle 的扁平 zip 同理 |

最终本机 `conan create` 结果：

```
unzoo/4.4: Sources correctly downloaded from .../unzoo_4.4.orig.tar.gz
unzoo/4.4: RUN: make -j1
unzoo/4.4: Package created
test package: RUN: unzoo -l good.zoo > view.log 2>&1
test package: RUN: unzoo -x good.zoo > extract.log 2>&1
→ 无异常，test_package 三项断言全过
```

## 7. 待真机验证内容（READY_FOR_HARMONY 清单）

1. `conan create`（clang 15 / aarch64-ohos）：补头文件 + struct utimbuf 后
   能否编译、`utime()` 是否不再有 LP64 问题
2. test_package 的 zoo 往返三项断言（构造归档与 CRC 都在 Python 侧完成，
   与目标平台无关，理论上应与 x86_64 结果一致）
3. 软件级 commands.json 是否被 CI L0k 接受
