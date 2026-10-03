#!/usr/bin/env python3
"""Conan recipe for cscope 15.9 — 交互式 C 源码交叉引用浏览器（CLI）。

cscope 是经典的 C 源码浏览器 / 符号索引工具（源码级交叉引用、
函数调用关系、符号定义查找），带 curses 全屏交互界面。
许可证为 Santa Cruz Operation (SCO) 的三条款 BSD 式许可。

上游: https://sourceforge.net/projects/cscope/  （v15.9，2017-11-07）

构建:  autotools（configure + make）。唯一外部依赖 ncurses。
产物:  bin/cscope（package_type=application）、man、contrib 脚本。

R3: 四条补丁均由 `refresh-patch --auto` 生成（per-file-difflib），
    不手工落盘：
    - 0001-config.guess.patch  旧式 config.guess 增加 HarmonyOS 分支
    - 0002-config.sub.patch    识别列表补 linux-ohos*
    - 0003-configure.patch     --with-ncurses 分支链接 libncursesw；
                               HMDFS 下放宽 mktemp/mkdir 的 umask
    - 0004-src-main.c.patch    临时目录权限改 HMDFS 可写（POSIX 兼容，无平台宏）
R26: ncurses 静态链接（shared=False）。
R1: 只加 --with-ncurses=<ncurses 包目录> 一个业务参数，不加
    --build/--host，不做 CFLAGS/LIBS hack。
"""

import os
import time

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# 上游 2017 年产物（configure/config.h.in/Makefile.in/egrep.*/scanner.c）
# 与宿主 autoconf/automake/bison/flex 不同代，禁止 make 触发重新生成。
_GENERATED = (
    "configure", "config.h.in", "aclocal.m4", "Makefile.in",
    "ylwrap", "compile", "depcomp", "install-sh", "missing", "mkinstalldirs",
    "src/Makefile.in", "src/egrep.h", "src/egrep.c",
    "src/scanner.c", "src/fscanner.c",
    "doc/Makefile.in", "contrib/Makefile.in",
)


class CscopeConan(ConanFile):
    name = "cscope"
    version = "15.9"
    description = (
        "Cscope — interactive C source code browser / cross-reference tool "
        "(symbol lookup, call graph, curses UI)"
    )
    license = "BSD-3-Clause"
    homepage = "https://sourceforge.net/projects/cscope/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def configure(self):
        # cscope 只产出可执行文件，不需要共享库
        self.options.rm_safe("shared")
        self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # curses 全屏界面；制品仓 ncurses/6.6 有 OHOS/armv8 二进制
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # cscope 自带的 ncurses 探测只扫 /usr/include 等宿主路径，在
        # conan 依赖布局下必然失败并退化为 SysV `-lcurses`。直接指定
        # 依赖包目录（configure.in:153 AC_ARG_WITH(ncurses)）。
        ncurses_dir = self.dependencies["ncurses"].package_folder
        tc.configure_args.append(f"--with-ncurses={ncurses_dir}")
        tc.generate()

    def _freeze_generated(self):
        """把预生成产物时间戳统一压到“现在”，使其不早于对应的
        .in/.am/.y/.l 源文件，避免 make 触发 autoconf/automake/
        bison/flex 重新生成（宿主工具版本与 2017 产物不兼容）。"""
        now = time.time()
        for rel in _GENERATED:
            path = os.path.join(self.source_folder, rel)
            if os.path.exists(path):
                os.utime(path, (now, now))

    def build(self):
        apply_conandata_patches(self)
        self._freeze_generated()
        autotools = Autotools(self)
        autotools.configure()
        # -j1：OHOS 上 make jobserver 依赖 mkfifo，禁用并行更稳
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        # -j1：同 build()，HMDFS 上 make jobserver 依赖 mkfifo
        autotools.install(args=["-j1"])
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 工具类包：暴露 bin/ 供下游消费
        self.cpp_info.bindirs = ["bin"]
        self.output.info("cscope 15.9: bin/cscope（交互式 C 源码浏览器）")
        # R38 — CLI 工具声明
        self.conf_info.define("user.tools.cscope:exe", "cscope")
