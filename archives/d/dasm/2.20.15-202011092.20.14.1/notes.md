# dasm 2.20.15-202011092.20.14.1 适配笔记

## 上游信息

- 上游: DASM（the DASM macro assembler），Matthew Dillon 1988 年起源的 8 位交叉宏汇编器
- 仓库: <https://github.com/dasm-assembler/dasm>
- 许可: GPL-2.0-or-later
- 源码版本: `src/version.h` 的 `DASM_RELEASE` = **2.20.14.1**
- 支持目标处理器: 6502 / 6803 / 68HC11 / 68705 / 68HC908 / F8
- 形态: 纯 C，无 autotools / cmake / meson。`src/` 下 11 个 `.c` 直接链接成 `dasm`，
  另有一个单文件工具 `ftohex`（bin → Intel HEX）

## 版本串的来历（重要）

平台任务给出的版本是 `2.20.15-202011092.20.14.1`，这个串不是上游版本，而是
Debian 版本

```
2.20.15~20201109+really2.20.14.1
```

经「`~` → `-`、`+really` → 空」规范化后的结果。含义是：2020-11-09 发布过
`2.20.15`，但因回归被 Debian 撤销、回退到 2.20.14.1，故 changelog 记作
"+really2.20.14.1"。

**源包文件名必须用 Debian 原始拼写**——按平台规范化串去 pool 里取会 404：

```
https://deb.debian.org/debian/pool/main/d/dasm/dasm_2.20.15~20201109+really2.20.14.1.orig.tar.gz
sha256 = ec71ffd10eeaa70bf7587ee0d79a92cd3f0a017c0d6d793e37d10359ceea663a
```

（pool 目录页实测：`dasm_2.20.15-202011092.20.14.1.orig.tar.gz` 返回 404。）

## 构建路线：不跑上游 Makefile，直编

上游 `src/Makefile` 极简（`OBJS` + 一条 `$(CC) $(CFLAGS) $(OBJS) -o dasm`），
但直接复用有两个问题：

1. 顶层 `build` 目标会 `mkdir -p bin && cp src/dasm bin/dasm`，往源码树写产物；
2. `ftohex: ftohex.o` 没有显式链接命令行，靠 **make 隐式规则**完成链接——
   换构建器就失效。

因此配方直接把 11 个核心 `.c` + 兼容实现显式编译并链接：

```python
CORE_SRCS = ["main", "ops", "globals", "exp", "symbols",
             "mne6303", "mne6502", "mne68705", "mne6811", "mnef8", "mne68908"]
```

## ★ 关键适配点：OHOS musl 没有 `strlcat`

`src/errors.c` 在 `append_level` / `append_location` / `append_information`
三处**无条件调用 `strlcat()`**，而项目内没有任何 `strlcat` 实现——它期望 libc 提供。

`strlcat`/`strlcpy` 源自 OpenBSD：

| libc | 是否提供 |
|---|---|
| OpenBSD / macOS / FreeBSD | 有（原生） |
| glibc | **2.38（2023-08）起才有** |
| **OHOS musl** | **没有** |

Debian 能编过正是靠 glibc 2.38+；在 OHOS musl 上则：

- 严格 ISO C 方言（`-std=c99`，未定义 `_POSIX_C_SOURCE`）→ 隐式函数声明，
  clang 15+ 默认按**错误**处理；
- 其他情形 → 链接期 `undefined reference to 'strlcat'`。

**解法：不改上游源码、不删调用**，用 `-include` 前置一个兼容头 + 单独编译实现：

```c
/* dasm_ohos_compat.h（经 -include 注入到每个编译单元之前） */
#include <stddef.h>
size_t dasm_compat_strlcat(char *dst, const char *src, size_t siz);
size_t dasm_compat_strlcpy(char *dst, const char *src, size_t siz);
#define strlcat dasm_compat_strlcat
#define strlcpy dasm_compat_strlcpy
```

用**宏改名**而不是条件声明，好处是两种 libc 下都安全：在已提供 `strlcat` 的
libc 上，`<string.h>` 里的原型会被一并改名成同签名的自带实现，不会重复定义。

实现必须严格复刻 OpenBSD 语义——`errors.c` 把 `strlcat` 的**返回值**当作已写长度
继续推进（截断时返回"所需的完整长度"），简单 `strncat` 会算错。

实测确认（readelf/nm）：

```
$ nm -D pkg/bin/dasm | grep strl
                 U strlen
0000000000016c24 T dasm_compat_strlcat      ← 自带实现，无 UND strlcat
$ readelf -d pkg/bin/dasm | grep NEEDED
 0x0000000000000001 (NEEDED)  Shared library: [libc.so]
```

## ★ 交付链陷阱：`conan.tools.files.copy()` 的 pattern 是相对路径 fnmatch

本包第一版 `package()` 写的是：

```python
copy(self, "dasm", src=self.source_folder, dst=bin_dst)   # ← 静默零拷贝
```

`copy()` 的 pattern 与**相对 src 的路径**做 fnmatch，不是与 basename 匹配。
以 `source_folder` 为 src 时，产物的相对路径是 `bin/dasm`，
`fnmatch("bin/dasm", "dasm")` 为假 → **一个字节都不拷，且不报任何错**。
包目录里 `bin/` 直接不存在，只有 test_package 的 `access()` 断言才能发现。

正确写法是以 `<source>/src` 为 src（此时相对路径就是 `dasm`）：

```python
src = os.path.join(self.source_folder, "src")
copy(self, "dasm", src=src, dst=bin_dst)
```

对照：`copy(self, "*", src=<sf>/machines, dst=...)` 之所以正常，是因为 `*` 能匹配
含 `/` 的相对路径。

## ★ 消费者测试陷阱：`-std=c99` 隐藏 `popen` 声明 → 段错误

`test_package` 里用 `popen`/`pclose` 直读子进程输出。在**严格 ISO C**方言下
（显式 `-std=c99`，未定义 `_POSIX_C_SOURCE`），glibc 与 musl **都**会隐藏
`popen`/`pclose` 的声明：

```console
warning: implicit declaration of function 'popen'
warning: initialization of 'FILE *' from 'int' makes pointer from integer
→ 运行时段错误（实测 glibc 2.35：exit 139）
```

修法：在 test 源文件**所有 `#include` 之前**加

```c
#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#endif
```

CMake 默认用 gnu 方言不暴露该问题，只有显式 `-std=c99` 才复现——所以本地
"用严格标准编一遍"是有价值的自查动作。

## 测试：上游自带完整回归套件

上游 `test/` 是一套货真价实的回归套件，`test/run_tests.sh` 分两段：

- **strict=off**：对每个 `*.bin.ref`，跑
  `../bin/dasm NAME.asm -f1 -oNAME.bin -LNAME.list.txt -DINEEPROM`，
  再 `cmp NAME.bin NAME.bin.ref`；
- **strict=on**：对每个 `*.fail`，加 `-S` 期望报错，并校验期望错误码。

`.bin.ref` 的布局是 **2 字节小端 origin 头 + 机器码**（`-f1` 原始格式）。

**本地实测（WSL/Ubuntu 22.04 + gcc 11.4 复刻配方构建）：**

```
executed 93 tests, 85 OK, 8 failed, result: need to investigate in 1 test-cases
```

8 个未通过项全部是**上游既有状态**，与本次适配无关：

| 未通过项 | 性质 |
|---|---|
| `selftest/0_no_assembly`、`selftest/1_no_binary`、`selftest/2_hexref_missing`、`selftest/3_binary_different` | `selftest/` 是**元测试目录**：故意制造各类失败，用来验证 harness 自己能识别失败 |
| `selftest/5_must_fail`、`selftest/6_false_positive_fail`、`selftest/7_false_positive_fail` | 同上，元测试的期望值本身标注不全 |
| `atari7800/spritesample` | 上游 Makefile 头部已注明 "demo.asm doesn't compile!" 一类既知失败 |

选择这 12 个用例内嵌进 `test_package/test_cases.h`（全部取自非 strict 段
`binary is same, pass` 的用例，且满足「无 `.args`、源码不引用外部文件」）：

```
6502_16h  6502_16l  stawx  jmpiw  forced_addrmode  addressexpression
multiline_comment  same_names  declare_var_mac  recursive_macro0
toobigword  string_conversion
```

覆盖：强制字节/字寻址与高位/低位取用、`.wx` 强制寻址、立即数间接、
地址表达式 `.`/`*` 语义、多行注释、同名符号、宏内声明变量、递归宏、
数值越界、字符串转换。origin 覆盖 0x0000 / 0x0100 / 0x0801 / 0x1000 / 0x8000 / 0xF800。

> 注意：`doublemacro`、`toobigword` 等在上游**同时**登记了 `.bin.ref` 与 `.fail`。
> strict 段会把同名 `.bin` **清空为 0 字节**，所以逐字节复核必须在非 strict 段之后
> 单独重跑，否则会误判为 mismatch。

## 验证证据

| 项 | 结果 |
|---|---|
| 配方构建（OHOS clang，`conan create`） | 通过，`Built target test_dasm` |
| `bin/dasm` | 203552 B，ELF64 AArch64 PIE，`NEEDED` 仅 `libc.so` |
| `bin/ftohex` | 16720 B，ELF64 AArch64 PIE |
| `strlcat` | 由 `dasm_compat_strlcat` 提供，动态符号表无 UND strlcat |
| test_package（**真实 OHOS aarch64 制品实跑**） | **38 passed, 0 failed** |
| 上游套件（本地 gcc 复刻） | 93 tests, 85 OK, 8 failed（8 项均上游既有元测试/既知失败） |

test_package 的 38 项包含 12 个上游用例的**逐字节**比对（origin 头 + 机器码）、
`ftohex` 的 Intel HEX 往返（首字符 `:` + EOF 记录 `:00000001FF`）、用法横幅与
`ERROR_COMMAND_LINE(1)` 退出码、以及机器头/手册页的随包安装断言。

## 随包资源

```
bin/dasm  bin/ftohex
share/dasm/machines/{atari2600,atari7800,68hc11,68hc908,channel-f}/*
share/doc/dasm/{ChangeLog,NEWS,README,LICENSE,dasm.txt,ftohex.txt}
share/man/man1/dasm.1
```

`machines/atari2600/{vcs.h,macro.h}` 等是用户写 2600 汇编时经 `-I` 引入的
寄存器/宏定义，Debian 包同样随包分发，故一并安装。
