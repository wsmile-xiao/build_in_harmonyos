#!/usr/bin/env python3
"""Conan recipe for cpmtools 2.23 — CP/M 磁盘镜像读写工具集。

上游是 autotools 项目（14 个 C 文件），产出 8 个命令行工具：
    cpmls cpmcp cpmrm cpmchmod cpmchattr mkfs.cpm fsck.cpm  (+ fsed.cpm)
本配方直接驱动 OHOS clang 复刻上游 Makefile 的 7 个核心工具（不含 fsed.cpm）。

⚠ 产品集合取舍（必读）：
上游 configure.in 用 **探测型可选依赖** 决定是否构建第 8 个工具：

    AC_CHECK_LIB(curses,  printw, FSED_CPM=fsed.cpm LIBS="-lcurses $LIBS")
    AC_CHECK_LIB(ncurses, printw, FSED_CPM=fsed.cpm LIBS="-lncurses $LIBS" ...)

找不到 curses/ncurses 时 `FSED_CPM` 置空，**Makefile 的 ALL 里就静默少一个产物**——
configure 不报错、不警告。绕过 configure 直编时必须**显式决定**这个取舍：

* 本配方（默认）：不提供 ncurses → 交付 7 个核心工具，`fsed.cpm`（交互式全屏
  编辑器）不构建。已在 notes.md 与 PR 正文显式声明该功能缺口。
* 若要启用 `fsed.cpm`：把下面的 `requires` 打开为 `self.requires("ncurses/6.6")`
  （制品仓已发布），并在 `_config_h()` 里追加 `#define NEED_NCURSES 1` 与
  `#define HAVE_NCURSES_NCURSES_H 1`，再把 ncurses 的 includedirs/libdirs 注入
  编译/链接命令（term_curses.c + `-lncurses`）。**最不可接受的做法是既不提供、
  也不声明** —— 那样 CI 全绿但产物静默缩水，属于"假完整"。

其他适配要点：
- tarball 里没有 config.h（只有 config.h.in），而 device_posix.c / term_curses.c
  都会 `#include "config.h"` —— 配方需**自行生成**该头（本次只开 POSIX 相关宏）。
- 上游不用 libdsk（默认 `DEVICE=posix`），故设备层用 device_posix.c；
  device_libdsk.c 不参与构建。
- 产物统一安装到 bin/，均为 ELF64/AArch64、NEEDED 仅 libc.so（无 ncurses 时）。
"""
import json
import os

from conan import ConanFile
from conan.tools.files import copy, get

# 上游 Makefile 的 ALL 列表（不含 $(FSED_CPM)）
TOOLS = ["cpmls", "cpmrm", "cpmcp", "cpmchmod", "cpmchattr", "mkfs.cpm", "fsck.cpm"]
# 每个工具都链接同一组公共目标文件（对应上游 Makefile 的 $(OBJ) + $(DEVICEOBJ)）
COMMON_OBJS = ["cpmfs.o", "getopt.o", "getopt1.o", "device_posix.o"]

CONFIG_H = """\
/* config.h — 由 cpmtools recipe 生成（上游该文件由 configure 从 config.h.in 产出）
 *
 * ★ 关键：config.h.in 里「能力宏」与「#include」是**成对**出现的，头文件的包含
 *   动作发生在 config.h **内部**。因此手写 config.h 时**不能只补宏定义**，
 *   必须连同 `#ifdef X / #include <x.h> / #endif` 块一起补齐；否则 HAVE_* 宏
 *   形同虚设，症状是各 TU 里 O_RDONLY / LONG_MAX / struct utimbuf 等处处
 *   undeclared（看起来像"源码不兼容 clang"，实为 config.h 不完整）。
 *
 * 本文件开启 POSIX 侧能力；不使用 libdsk、不使用 ncurses（见文件顶部取舍说明）。
 * DISKDEFS / FORMAT 对应上游 Makefile 的
 *   CPPFLAGS ... -DDISKDEFS=\\"$(DISKDEFS)\\" -DFORMAT=\\"$(DEFFORMAT)\\"
 * 放在 config.h 里可避开跨 shell 的引号转义问题。
 */
#define HAVE_FCNTL_H 1
#ifdef HAVE_FCNTL_H
#include <fcntl.h>
#endif

#define HAVE_LIMITS_H 1
#ifdef HAVE_LIMITS_H
#include <limits.h>
#endif

#define HAVE_UNISTD_H 1
#ifdef HAVE_UNISTD_H
#include <unistd.h>
#endif

#define HAVE_SYS_TYPES_H 1
#ifdef HAVE_SYS_TYPES_H
#include <sys/types.h>
#endif

#define HAVE_SYS_STAT_H 1
#ifdef HAVE_SYS_STAT_H
#include <sys/stat.h>
#endif

#define HAVE_UTIME_H 1
#ifdef HAVE_UTIME_H
#include <utime.h>
#endif

/* 以下能力在 OHOS 上不使用 */
/* #undef HAVE_WINDOWS_H */
/* #undef HAVE_WINIOCTL_H */
/* #undef HAVE_LIBDSK_H */
/* #undef HAVE_SYS_UTIME_H */
/* #undef NEED_NCURSES */
/* #undef HAVE_NCURSES_NCURSES_H */
/* #undef _FILE_OFFSET_BITS */
/* #undef _LARGE_FILES */

/* 磁盘定义文件路径（上游 Makefile 的 -DDISKDEFS；cpmfs.c 先试 ./diskdefs 再试此处） */
#ifndef DISKDEFS
#define DISKDEFS "/usr/share/cpmtools/diskdefs"
#endif
/* 默认磁盘格式（上游 Makefile 的 -DFORMAT） */
#ifndef FORMAT
#define FORMAT "ibm-3740"
#endif

#ifndef _POSIX_PATH_MAX
#define _POSIX_PATH_MAX 256
#endif

#ifndef environ
extern char **environ;
#endif
"""


class CpmtoolsConan(ConanFile):
    name = "cpmtools"
    version = "2.23"
    description = "Tools to access CP/M file systems"
    license = "GPL-2.0-or-later"
    homepage = "http://www.moria.de/~michael/cpmtools/"
    topics = ("cpm", "filesystem", "disk-image", "cli")
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
    # 若要启用 fsed.cpm（交互式编辑器），打开下面这行并见文件顶部说明：
    # requires = "ncurses/6.6"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        """解析 C 编译器：conf > CC 环境变量 > 裸 clang（R33：不在 self.run 里做 shell 展开）。"""
        compilers = self.conf.get("tools.build:compiler_executables")
        if isinstance(compilers, str):
            try:
                compilers = json.loads(compilers)
            except ValueError:
                compilers = None
        if isinstance(compilers, dict) and compilers.get("c"):
            return compilers["c"]
        return os.environ.get("CC", "clang")

    def build(self):
        cc = self._cc()
        src = self.source_folder
        # 生成 config.h（上游由 configure 生成；tarball 只有 config.h.in）
        with open(os.path.join(src, "config.h"), "w", encoding="utf-8") as f:
            f.write(CONFIG_H)
        # 上游 configure 对 GCC/clang 追加了一长串 -W 选项并把警告视为噪声；
        # 这里保留可编译的最小集合（-Wno-* 抵消上游代码里已知的旧式写法告警）。
        cflags = (os.environ.get("CFLAGS", "")
                  + " -O2 -Wall -DDEVICE=posix"
                  + " -Wno-unused-parameter -Wno-cast-qual -Wno-pointer-arith"
                  + " -Wno-write-strings -Wno-missing-prototypes")
        # 编译公共目标文件
        for o in COMMON_OBJS:
            self.run(f'cd {src} && {cc} {cflags} -c {o[:-2]}.c -o {o}')
        # 逐个工具：编译主源 + 链接公共 OBJ（等价于上游 Makefile 的每个 target）
        objs = " ".join(COMMON_OBJS)
        for t in TOOLS:
            self.run(f'cd {src} && {cc} {cflags} -c {t}.c -o {t}.o')
            self.run(f'cd {src} && {cc} {cflags} {t}.o {objs} -o {t}')

    def package(self):
        bin_dst = os.path.join(self.package_folder, "bin")
        doc_dst = os.path.join(self.package_folder, "share", "doc", "cpmtools")
        man_dst = os.path.join(self.package_folder, "share", "man", "man1")
        for t in TOOLS:
            copy(self, t, src=self.source_folder, dst=bin_dst)
        copy(self, "diskdefs", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "cpmtools"))
        copy(self, "README", src=self.source_folder, dst=doc_dst)
        copy(self, "COPYING", src=self.source_folder, dst=doc_dst)
        copy(self, "*.1", src=self.source_folder, dst=man_dst)
        for t in TOOLS:
            p = os.path.join(bin_dst, t)
            if os.path.isfile(p):
                os.chmod(p, 0o755)
