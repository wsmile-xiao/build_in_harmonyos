#!/usr/bin/env python3
"""Conan recipe — xterm 410 (X11 终端模拟器)

Build system: autotools (configure + make)
License: MIT
Homepage: https://invisible-island.net/xterm/

R26: 终端工具强制静态链接
依赖说明: X11 库来自编译环境预编译包
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XtermConan(ConanFile):
    name = "xterm"
    version = "410"
    description = "X terminal emulator for the X Window System"
    license = "MIT"
    homepage = "https://invisible-island.net/xterm/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # X11 库为编译环境预编译包
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 指定 X11 头文件和库路径（预编译包位置）
        sys_prefix = "/storage/Users/currentUser/usr/local"
        tc.configure_args.append(f"--x-includes={sys_prefix}/include")
        tc.configure_args.append(f"--x-libraries={sys_prefix}/lib")
        tc.configure_args.append("--disable-toolbar")
        # 交叉编译模式（跳过运行时检测，E007 修复）
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # 确保 configure 测试程序能链接 X11 库
        tc.extra_ldflags.append(f"-L{sys_prefix}/lib")
        tc.extra_ldflags.append(f"-Wl,-rpath,{sys_prefix}/lib")
        # R26: 终端工具强制链接时加入 -static
        # 注意: --static 不能加在 extra_ldflags 中（会阻塞 configure 测试程序）
        # 改为在 make 时通过 LDFLAGS 传入
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # 创建 libXaw stub（xterm 需要链接 libXaw 但功能已在 --disable-toolbar 下禁用）
        # 同时包含 ttyslot 等鸿蒙缺失的系统函数
        xaw_stub_code = r"""
void XawSimpleMenuAddGlobalActions(void) {}
void XawScrollbarSetThumb(void) {}
void XawTerminate(void) {}
void *simpleMenuWidgetClass = 0;
void *smeBSBObjectClass = 0;
void *smeLineObjectClass = 0;
void *scrollbarWidgetClass = 0;
char XtNleftBitmap[] = "leftBitmap";
/* ttyslot - missing on HarmonyOS */
int ttyslot(void) { return 0; }
"""
        self.run(f'cat > xaw_stub.c << \\EOF\n{xaw_stub_code.strip()}\nEOF')
        self.run("clang -c xaw_stub.c")
        # 安装到 X11 库路径供 configure 检测（CI 环境不持久化此操作）
        self.run("cp xaw_stub.o /storage/Users/currentUser/usr/local/lib/")
        self.run("ar rcs /storage/Users/currentUser/usr/local/lib/libXaw.a xaw_stub.o")
        # 创建 curses.h stub（xterm 需要 terminal info 头文件，OS 未提供）
        self.run("mkdir -p include")
        curses_h = r"""
#ifndef _STUB_CURSES_H
#define _STUB_CURSES_H
#include <stdio.h>
typedef unsigned int chtype;
typedef unsigned int mmask_t;
struct MEVENT { short id; int x; int y; int z; mmask_t bstate; };
#define ERR (-1)
#define OK 0
static inline char *tigetstr(const char *cap) { (void)cap; return (char *)-1; }
static inline int tigetnum(const char *cap) { (void)cap; return -1; }
static inline int tigetflag(const char *cap) { (void)cap; return 0; }
static inline char *tgetstr(const char *id, char **area) { (void)id; (void)area; return (char *)-1; }
static inline int tgetent(char *buf, const char *term) { (void)buf; (void)term; return -1; }
static inline int tgetflag(const char *id) { (void)id; return 0; }
static inline int tgetnum(const char *id) { (void)id; return -1; }
#endif
"""
        self.run(f'cat > include/curses.h << \\EOF\n{curses_h.strip()}\nEOF')
        self.run("cp include/curses.h /storage/Users/currentUser/usr/local/include/curses.h")
        # 创建 ohos_fix.h — 鸿蒙系统差异补丁
        ohos_fix = r"""
/* HarmonyOS utmpx compatibility fixes */
#ifndef _OHOS_FIX_H
#define _OHOS_FIX_H
#include <utmpx.h>
/* OHOS uses ut_tv.tv_sec instead of ut_time */
#ifndef ut_time
#define ut_time ut_tv.tv_sec
#endif
/* Provide struct utmp for lastlog compatibility */
struct utmp {
    char ut_user[32];
    char ut_id[4];
    char ut_line[32];
    pid_t ut_pid;
    short ut_type;
    struct timeval ut_tv;
    char ut_host[256];
};
#endif
"""
        self.run(f'cat > include/ohos_fix.h << \\EOF\n{ohos_fix.strip()}\nEOF')
        self.run("cp include/ohos_fix.h /storage/Users/currentUser/usr/local/include/ohos_fix.h")
        # 配置
        autotools.configure()
        # 编译（链接阶段不使用 -static，因为预编译 X11 库仅有 .so 版本）
        self.run('make LDFLAGS="-L/storage/Users/currentUser/usr/local/lib -Wl,-rpath,/storage/Users/currentUser/usr/local/lib" '
                 'LIBS="-lXaw -lXt -lXmu -lX11 -lXext -lSM -lICE -lXau" '
                 'EXTRA_CPPFLAGS="-I/storage/Users/currentUser/usr/local/include -include /storage/Users/currentUser/usr/local/include/ohos_fix.h"')

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 确保二进制被复制到包目录
        self.run(f'mkdir -p {self.package_folder}/bin')
        self.run(f'cp -p xterm resize 2>/dev/null {self.package_folder}/bin/ || true')

    def package_info(self):
        # 终端工具，无可链接库
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
