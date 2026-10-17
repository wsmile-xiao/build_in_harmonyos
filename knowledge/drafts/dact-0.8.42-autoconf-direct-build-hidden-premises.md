# 直编 autoconf 项目的两处隐蔽前提（config.h 门控 + 功能表自洽）

> Draft: `DRAFT-DACT-AUTOCONF-DIRECT-BUILD-HIDDEN-PREMISES`
> Stem: `dact-0.8.42-autoconf-direct-build-hidden-premises` — 与同 stem 的 `.kv` 成对
> 实例：dact 0.8.42（PR !9424）

## 基本信息

- **ID**: DRAFT-DACT-AUTOCONF-DIRECT-BUILD-HIDDEN-PREMISES
- **严重度**: 2
- **类别**: autoconf, conan, config-h, feature-table
- **触发工具**: conan
- **阶段**: build

## 前提一：`config.h` 的**包含被 `HAVE_CONFIG_H` 门控**

上游头文件的标准写法：

```c
#ifdef HAVE_CONFIG_H
#include "config.h"
#endif
```

绕过 configure 直编时，常见做法是"我生成一份 config.h 写进源码目录就行" ——
但**如果没传 `-DHAVE_CONFIG_H`，这份 config.h 永远不会被包含**。

后果：配置里所有能力宏全部失效。症状是标准 POSIX 符号 `undeclared`、函数隐式声明，
**与"config.h 内容写错"几乎无法区分**，极易被误判为"老代码不兼容 clang"。

一行判据：

```bash
grep -rn 'HAVE_CONFIG_H' *.h
```

有命中 → 必须把 `-DHAVE_CONFIG_H` 当作**编译前提**写进配方（并在注释里说明原因）。

## 前提二：能力宏必须与**位置敏感的功能注册表**自洽

很多项目把可选实现放进一张固定长度、**按下标注册**的函数指针表：

```c
int (*(algorithms[256]))()={ comp_plain_algo, comp_rle_algo, comp_delta_algo, comp_text_algo,
#ifdef HAVE_LIBZ
        comp_zlib_algo, comp_mzlib_algo,
#else
        DACT_FAILED_ALGO, DACT_FAILED_ALGO,
#endif
        comp_snibble_algo, DACT_FAILED_ALGO,
#ifdef HAVE_LIBZ
        comp_mzlib2_algo,
#else
        DACT_FAILED_ALGO,
#endif
        ... };
```

于是 **"定义了哪个宏"必须与"链接了哪些 `.o`"严格对偶**。错配有两种后果：

| 错配 | 后果 | 可见性 |
|---|---|---|
| 定义了宏，但没编对应 `.c` | 链接期 `undefined symbol: comp_xxx_algo` | 易发现 |
| 没定义宏（走占位分支），但本来能编的实现也没编 | 编译链接全过，**该算法运行时静默不可用** | **难发现，更危险** |

**处置原则：宁少勿多** —— 不确定时不要定义该宏（走 `DACT_FAILED_ALGO` 是显式且
安全的失败）；一旦定义了，就必须把对应 `.o` 编进去。

本包的严格对应关系：

| 宏 | 对应源文件 |
|---|---|
| 始终 | `comp_plain` `comp_rle` `comp_delta` `comp_text` `comp_snibble` |
| `HAVE_LIBZ` | `comp_zlib` `comp_mzlib` `comp_mzlib2` |
| 未启用 `HAVE_LIBBZ2` | 不编 `comp_bzlib` |
| 未启用 `DEBUG` | 不编 `comp_factor` `comp_bitsums` `comp_textrle` |

**无需编译的模块**：`comp_lzoox/lzooy/lzota.c` —— 其头文件在
`(defined(USE_MODULES) && !defined(AS_MODULE)) || !defined(HAVE_LIBLZO) || …`
成立时把 `comp_lzoX_algo` **宏定义为** `DACT_FAILED_ALGO`，是编译期别名，不产生符号。

## 附带坑：`AC_REPLACE_FUNCS` 与 musl 不声明 `getpass`

```m4
AC_REPLACE_FUNCS(getopt strsep getpass mkstemp uname)
```

autoconf 语义：**libc 有该函数 → 定义 `HAVE_<FUNC>`；没有 → 编译随包同名 `.c`**。

| 函数 | OHOS musl | 处置 |
|---|---|---|
| `getopt` | 有（且 `<getopt.h>` 存在） | 定义 `HAVE_GETOPT_H`，用系统实现 |
| `strsep` / `mkstemp` / `uname` | 有 | 分别定义 `HAVE_STRSEP` / `HAVE_MKSTEMP` / `HAVE_UNAME` |
| **`getpass`** | **`<unistd.h>` 完全没有声明**（glibc 会声明；musl 仅 `_GNU_SOURCE` 下才有） | **不定义 `HAVE_GETPASS`**，编译随包 `getpass.c` |

首次构建的真实报错：

```
ui.c:165:6: error: incompatible integer to pointer conversion
            assigning to 'char *' from 'int' [-Wint-conversion]
```

（`getpass` 被隐式声明为返回 `int`。）**看起来像"1990 年代老代码不兼容 clang 15"，
实为 musl 头文件差异。** 上游的配套约定是
`#ifndef HAVE_GETPASS / #include "getpass.h" / #endif` —— 保持宏未定义，
声明自动接上随包头文件。

## 可复用清单（动手前跑三条 grep）

```bash
grep -rn 'HAVE_CONFIG_H' *.h                    # ① 是否需要 -DHAVE_CONFIG_H
grep -rn 'AC_REPLACE_FUNCS\|AC_CHECK_LIB.*main' configure.in   # ② 哪些函数/库走"有则用、无则编"
grep -n 'algorithms\[\|_algo,' *.h              # ③ 是否存在位置敏感功能表
```

## 边界与查重

- 与同批 **cpmtools**（`config.h` 必须与 `config.h.in` 完全 parity，宏与 `#include` 成对写在
  config.h **内部**）的区别：那条是**config.h 内容不全**；本条是 **config.h 压根没被包含**
  （门控未打开）。判据（`grep HAVE_CONFIG_H` vs `grep -c '^#include' config.h`）与处置均不同。
- 与同批 **dds2tar**（疏漏 Makefile 注入物）的区别：那条讲 Makefile 的命令行宏与 OBJ；
  本条讲头文件门控与**运行时注册表自洽性**，后者甚至能在编译全过的情况下造成功能静默缺失。
- 与同批 **cvs-fast-export**（生成产物 vs 再生成规则）无交集。
- 正式库以 `HAVE_CONFIG_H` / `AC_REPLACE_FUNCS` / 位置敏感注册表检索无相关条目。

## 关联

- 配方 PR：**!9424**（dact 0.8.42 适配 HarmonyOS PC，分支 `feat/dact-0.8.42`）
- 平台任务：#6981（dact 0.8.42）
- 本 Issue 与 PR 双向关联；草稿经主编审核后由 promote 流程转入正式知识库。
