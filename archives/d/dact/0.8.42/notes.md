# dact 0.8.42 适配笔记

## 上游信息
- 上游: Roy Keene 的 DACT（Dynamic Adaptive Compression Tool）
- 功能: 多算法**自适应分块**压缩 —— 把输入切成块，逐块试验多种算法/参数取最小者，块间做差分
- 形态: autotools（39 个 C 文件），产出 `dact` + `libdact.a/.so`；可选 zlib/bz2/lzo/mcrypt 模块
- 主页: <https://www.rkeene.org/oss/dact/>

## 源码获取
```
https://deb.debian.org/debian/pool/main/d/dact/dact_0.8.42.orig.tar.gz
sha256 = 08c91d36b2de30c4f2e9e13a7b044c137c096db2ba8d868d1962e209dd6b2ed8
```

## 构建路线：不跑 configure，直编复刻 static 模式

上游 configure 是 autotools，但它的"可选模块"逻辑完全可推断，直编即可等价复刻：

```m4
AC_DEFUN(DC_CHK_MODULE, [
  AC_CHECK_LIB($1, main, [
    ALGO="$2 $ALGO"
    MODLIBS="-l$1 $MODLIBS"
    AC_DEFINE($3, [], [Something])
  ])
])
DC_CHK_MODULE(z,   comp_zlib.c comp_mzlib.c comp_mzlib2.c, HAVE_LIBZ)
DC_CHK_MODULE(bz2, comp_bzlib.c,                            HAVE_LIBBZ2)
```

即 **`AC_CHECK_LIB(lib, main)` 是"能链接上即算有"的惯用写法**；命中后把源文件追加进
`ALGO`、库名追加进 `MODLIBS`。

**本配方启用 zlib**（制品仓 `zlib/1.3.1`），**不启用 bz2 / lzo / mcrypt**。

## ⚠ 两处隐蔽前提（本包最容易踩的地方）

### 1. `HAVE_CONFIG_H` 必须定义 —— 否则 config.h 根本不被包含

`dact.h` 的写法是：

```c
#ifdef HAVE_CONFIG_H
#include "config.h"
#endif
```

即**包含动作被 `HAVE_CONFIG_H` 门控**。绕过 configure 直编时如果只在配方里生成了
`config.h` 却没传 `-DHAVE_CONFIG_H`，那么它**永远不会被包含**，配置里所有能力宏
全部失效 —— 症状与"宏写错了"几乎无法区分。编译命令中必须带 `-DHAVE_CONFIG_H`。

> 与 `cpmtools` 那类"宏与 `#include` 成对写在 config.h 内部"的项目是**不同**的陷阱：
> 那里是 config.h 内容不全，这里是 config.h 压根没被包含。

### 2. 能力宏必须与 `algorithms.h` 的**位置敏感表**自洽

`algorithms.h` 是一张固定长度（256）的函数指针表，逐项按宏切换：

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
#ifdef HAVE_LIBBZ2
        comp_bzlib_algo,
#else
        DACT_FAILED_ALGO,
#endif
... };
```

因此：**定义了哪个宏，就必须链接哪个 `.c`**。二者错配会造成两类故障：

- 定义了宏但没编对应 `.c` → 表里引用**未定义符号**（链接失败，好发现）；
- 该编的没编、却又没定义宏 → 算法被静默注册成 `DACT_FAILED_ALGO`
  （**编译链接都过，运行时功能静默缺失**——更危险）。

本配方让二者严格对应：

| 宏 | 对应源文件 |
|---|---|
| 始终 | `comp_plain` `comp_rle` `comp_delta` `comp_text` `comp_snibble` |
| `HAVE_LIBZ` | `comp_zlib` `comp_mzlib` `comp_mzlib2` |
| （未启用）`HAVE_LIBBZ2` | 不编 `comp_bzlib` |
| （未启用）`DEBUG` | 不编 `comp_factor` `comp_bitsums` `comp_textrle` |

`comp_lzoox/lzooy/lzota` **无需编译**：其头文件在
`(defined(USE_MODULES) && !defined(AS_MODULE)) || !defined(HAVE_LIBLZO) || …`
成立时把 `comp_lzoX_algo` 定义为 `DACT_FAILED_ALGO`（编译期别名，不产生符号）。

## 3. `AC_REPLACE_FUNCS` 与 getpass

```m4
AC_REPLACE_FUNCS(getopt strsep getpass mkstemp uname)
```

autoconf 语义：libc 有该函数就定义 `HAVE_<FUNC>`，没有就编译随包的同名 `.c`。

| 函数 | OHOS musl | 处置 |
|---|---|---|
| `getopt` | 有（且 `<getopt.h>` 存在） | 定义 `HAVE_GETOPT_H`，用系统实现 |
| `strsep` | 有 | 定义 `HAVE_STRSEP` |
| `mkstemp` | 有 | 定义 `HAVE_MKSTEMP` |
| `uname` | 有 | 定义 `HAVE_UNAME` |
| **`getpass`** | **`<unistd.h>` 完全没有声明**（glibc 会声明；musl 仅在 `_GNU_SOURCE` 下才有） | **不定义 `HAVE_GETPASS`**，编译随包 `getpass.c` |

`dact.h` 的配套约定：`#ifndef HAVE_GETPASS / #include "getpass.h" / #endif` ——
所以保持该宏未定义，声明会自动接上上游自带头文件。

> 首次构建时的报错正是这条：`ui.c:165: error: incompatible integer to pointer
> conversion assigning to 'char *' from 'int'`（`getpass` 隐式声明为 int 返回值）。
> 看起来像"老代码不兼容 clang"，实为"musl 不声明该函数"。

## 其他

- **字符串宏**：上游 Makefile 以 `-DDACT_CONFIG_FILE=\"$(CONF)\"`、`-DEXEEXT=\"\"`
  注入；本配方写进生成的 `config.h`（避开跨 shell 引号转义）。
- **不启用 `USE_MODULES`**：模块模式需 `dlopen` 与 `module_dir`；static 模式把算法
  直接链进主程序，产物自包含。
- 上游 Makefile 会生成 `dact.conf`（`version_check off` / `module_dir …` 等），
  本配方在 `build()` 中生成并安装到 `etc/dact.conf`。

## 运行验证
- `dact -h` → `usage: dact [options...] [file ...]`（dact.c 的确切输出）
- `dact -V` → 版本分支
- 真实压缩需要输入文件；真实网络版本检查已关闭（`version_check off`）。

## 测试（test_package，6 条断言）
1. `bin/dact` 存在 + 可执行
2. ELF64 / AArch64（`e_machine == 0xB7`）
3. `-h` 真实执行（未落在 126/127/128+）且输出含 `usage`
4. `etc/dact.conf` 已安装
5. `-V` 真实执行（同判据）

assertion_count = 6（上游可自动化项为 0）。

### 判据加固（吸收 AI 检视 P2/P3）
- **P2**：`popen` 经 `/bin/sh` 中转，被信号杀死的子进程由 shell 转成 **128+signum**，
  `WIFEXITED` 恒为真 → 判据把 `126/127/>=128` 一并视为"没跑起来"。
- **P3**：**循环读干管道**后才 `pclose`，避免 SIGPIPE 假通过 / 死锁。
- **不写 `/tmp`**：OHOS 上 `/tmp` 只读。
- 产物：`ELF64/AArch64`，**NEEDED 仅 libc.so**（zlib 静态链入）。
