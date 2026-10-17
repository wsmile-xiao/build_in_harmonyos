# cpmtools 2.23 适配笔记

## 上游信息
- 上游: Michael Haardt 的 cpmtools（<http://www.moria.de/~michael/cpmtools/>）
- 功能: CP/M 文件系统读写工具集 —— 列举、拷贝、删除、改属性/权限、格式化、校验
- 形态: autotools 项目，14 个 C 文件，产出 8 个命令行工具

## 源码获取
上游站点在 CI worker 上不可达。改用 **Debian pool 的 orig.tar.gz**：
```
https://deb.debian.org/debian/pool/main/c/cpmtools/cpmtools_2.23.orig.tar.gz
sha256 = 02088d41bbf4c45c32e4ce505d3030e8f6f0d0dc74e60e5f13d7e696d44f9997
```

## ⚠ 产物集合取舍（最重要的一条）

上游 `configure.in` 用**探测型可选依赖**决定第 8 个工具是否构建：

```m4
dnl Check for curses. If not found, don't build fsed.cpm
AC_CHECK_LIB(curses, printw, FSED_CPM=fsed.cpm LIBS="-lcurses $LIBS", FSED_CPM=)
if test x"$FSED_CPM" = x""; then
  AC_CHECK_LIB(ncurses, printw, FSED_CPM=fsed.cpm LIBS="-lncurses $LIBS" ...)
fi
```

`Makefile.in`：

```make
ALL = cpmls cpmrm cpmcp cpmchmod cpmchattr mkfs.cpm fsck.cpm $(FSED_CPM)
```

**探测失败时 `FSED_CPM` 置空 → ALL 里静默少一个产物，configure 不报错、不警告。**
绕过 configure 直编时必须显式决定这个取舍：

| 方案 | 结果 | 本配方 |
|---|---|---|
| 提供 ncurses（`requires = "ncurses/6.6"`，制品仓已发布） | 8 个工具全交付 | 未采用（见下） |
| 不提供，**显式声明缺口** | 7 个核心工具 | ✅ **本配方** |
| 不提供，**也不声明** | CI 全绿但产物静默缩水 —— 「假完整」 | ❌ 禁止 |

**本包的实际交付：7 个核心工具**（`cpmls` `cpmrm` `cpmcp` `cpmchmod` `cpmchattr`
`mkfs.cpm` `fsck.cpm`），**不含 `fsed.cpm`**（交互式全屏编辑器，依赖 ncurses）。
该缺口已在 `conanfile.py` 顶部、本文件、`MANIFEST.yml` 与 PR 正文中显式声明。

**若要补齐 `fsed.cpm`**：打开 `conanfile.py` 里的 `requires = "ncurses/6.6"`，
在生成的 `config.h` 中追加 `#define NEED_NCURSES 1` 与
`#define HAVE_NCURSES_NCURSES_H 1`，并把 ncurses 的 includedirs/libdirs 注入
`term_curses.c` 的编译与 `-lncurses` 链接（`term_curses.c` 会尝试
`<ncurses/ncurses.h>` / `<ncurses.h>` / `<curses.h>` 三种路径，由上述宏选择）。

## 编译要点

### 1. config.h 必须与 config.h.in **完全 parity**

tarball 里**没有** `config.h`（只有 `config.h.in`），而**每个** C 文件第 2 行都是
`#include "config.h"`。上游的 config.h.in 结构是：

```c
#undef HAVE_FCNTL_H
#ifdef HAVE_FCNTL_H
#include <fcntl.h>          /* ← 包含动作在 config.h 内部！ */
#endif
```

即「能力宏」与「`#include`」是**成对**的。手写 config.h 时**只补宏定义、漏掉 include
块**，会导致 HAVE_* 形同虚设，症状是各 TU 里 `O_RDONLY` / `LONG_MAX` /
`struct utimbuf` 处处 `undeclared`——看起来像"源码不兼容 clang"，实为 config.h 不完整。
本配方生成的 config.h 逐条补齐了 `#ifdef / #include / #endif` 块。

### 2. 字符串字面量宏放进 config.h

上游 `Makefile.in`：

```make
CPPFLAGS = @CPPFLAGS@ -DDISKDEFS=\"$(DISKDEFS)\" -DFORMAT=\"$(DEFFORMAT)\"
```

`-DDISKDEFS=\"...\"` 的跨 shell 引号转义不可靠（cmd.exe 与 POSIX sh 行为不同），
配方改为在生成的 `config.h` 里 `#define DISKDEFS "..."` / `#define FORMAT "ibm-3740"`。

### 3. 设备层只用 device_posix.c

上游默认 `DEVICE=posix`（`--with-libdsk` 才切到 libdsk），故只编
`device_posix.c`，`device_libdsk.c` 不参与构建。构建时统一传 `-DDEVICE=posix`。

## 运行验证
- 7 个工具均支持 `-h` / 无参数走自带 getopt 的 usage 分支，退出码非 0 属预期。
- 真实磁盘操作需要 CP/M 磁盘镜像与 `diskdefs` 文件（已随包安装到
  `share/cpmtools/diskdefs`；`cpmfs.c` 先试当前目录的 `diskdefs`，再试编译期
  `DISKDEFS` 路径）。

## 测试（test_package，22 条断言）
- 7 × 存在 + 7 × 可执行
- 1 × 全部 7 个工具为 ELF64/AArch64（逐条判定，汇总汇报）
- 7 × 真实执行（`-h`）：未被信号杀死、退出码不在 {126,127,255}

**注意**：断言全部用 `popen` 直读子进程输出，**不落盘 /tmp**。
