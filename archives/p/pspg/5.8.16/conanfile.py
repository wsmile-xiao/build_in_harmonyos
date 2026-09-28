#!/usr/bin/env python3
"""Conan recipe — pspg 5.8.16 (autotools: 预生成 configure + 手写 Makefile)

pspg 是面向表格数据的 Unix pager（psql/CSV/TSV 观看器），产物为单一
bin/pspg 可执行文件。

OHOS 适配要点（R32/R33/R9/E074/E114；先例 gtypist/2.10.1 + zzuf/0.15）：
1. 官方 tag tarball 自带预生成 configure（autoconf 2.72 生成）→ 无需
   bootstrap；configure.ac 无 AC_CANONICAL_*，不需要 config.guess，
   无需 --build 三元组。
2. 构建体系是手写根 Makefile + configure 生成 config.make（非 automake），
   in-source 构建（根 Makefile 以相对路径编译 src/*.c、对象落根目录）。
   make install 经 tools/install.sh 安装 bin/pspg。
3. ncurses/6.6 包头文件平铺（include/curses.h），而 ax_with_curses 在
   pkg-config 命中 ncursesw 后直接 AC_DEFINE HAVE_NCURSESW_CURSES_H
   （源码随后 #include <ncursesw/curses.h>）→ 生成 compat-include/
   ncursesw/ 镜像层并前置 -I（gtypist/2.10.1 已验证方案）；平铺镜像
   同时兜底 pkg-config 缺失时的 HAVE_NCURSES_H 分支。
4. readline/8.3：AX_LIB_READLINE 仅 -lreadline 链接探测（无 pkg-config），
   AutotoolsDeps 注入 LDFLAGS 即命中；上游可选依赖，require 以保留
   搜索/历史完整功能。
5. PostgreSQL 探测未命中仅 NOTICE（configure.ac 显式不报错），不需要
   libpq；clock_gettime 由 musl libc 直接提供，无需 rt。
6. E114: HMDFS 忽略 chmod，configure 内部以 umask 077 建临时目录会
   Permission denied → 生成脚本 077→022 替换，命令前置 umask 022；
   CONFIG_SHELL 缺陷（§12.38①：hnp bash 作 CONFIG_SHELL 时 autoconf
   re-exec 在 HMDFS getcwd 挂死）→ env -u CONFIG_SHELL SHELL=/bin/sh
   + 绝对路径（gtypist 同款）。
7. E074: HMDFS jobserver fifo EPERM → make -j1。
8. 上游无自动化测试套件（tests/ 仅交互式数据流生成器，Makefile 无
   test 目标）→ 按赛事规则说明原因，test_package 消费者测试真实执行
   pspg（非交互 CSV/TSV 渲染路径）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class PspgConan(ConanFile):
    name = "pspg"
    version = "5.8.16"
    description = ("pspg - Unix pager designed for table browsing "
                   "(psql/CSV/TSV viewer)")
    license = "BSD-2-Clause"
    homepage = "https://github.com/okbob/pspg"
    url = "https://github.com/okbob/pspg"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # 手写根 Makefile 以相对路径编译 src/*.c、对象落根目录 —— in-source
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # E490: 确保 configure 保留可执行位（HMDFS 忽略 chmod，这里只影响
        # 常规 Linux 环境；真机一律 sh 显式调用）
        p = os.path.join(self.source_folder, "configure")
        if os.path.exists(p):
            os.chmod(p, 0o755)

    def validate(self):
        # R32: settings.os 判断必须同时接受 Linux 与 OHOS
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pspg OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def requirements(self):
        # W0: AX_WITH_CURSES 硬依赖 ncurses（缺失时 configure 直接报错），
        # AX_WITH_CURSES_PANEL 需 panelw —— ncurses/6.6 单组件包同时提供
        # panelw/menuw/formw 与 ncursesw.pc。
        # AX_LIB_READLINE 为上游可选依赖，require readline/8.3 保留完整
        # 搜索/历史功能。
        # PostgreSQL 为上游可选（未命中仅 NOTICE），不需要 libpq。
        # MateBook 第一步：conan download 复核二进制包（R35，禁用 conan list）。
        self.requires("ncurses/6.6")
        self.requires("readline/8.3")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        # 注入 -L/-l（LDFLAGS/LIBS），供 AC 检测与最终链接命中制品仓包
        AutotoolsDeps(self).generate()
        # compat-include/ncursesw/ 镜像层（文件头 #3）：ncurses 平铺头 +
        # ncursesw/ 镜像；readline include 路径随命令行 CPPFLAGS 注入
        compat = os.path.join(self.build_folder, "compat-include")
        rl_inc = ""
        for dep in self.dependencies.host.values():
            if dep.ref.name == "ncurses":
                incdir = os.path.join(dep.package_folder,
                                      dep.cpp_info.includedirs[0])
                os.makedirs(os.path.join(compat, "ncursesw"), exist_ok=True)
                for f in os.listdir(incdir):
                    if f.endswith(".h"):
                        shutil.copy2(os.path.join(incdir, f),
                                     os.path.join(compat, "ncursesw", f))
                        shutil.copy2(os.path.join(incdir, f),
                                     os.path.join(compat, f))
            elif dep.ref.name == "readline":
                rl_inc = " ".join(
                    "-I" + os.path.join(dep.package_folder, d)
                    for d in dep.cpp_info.includedirs)
        self._cppflags = f"-I{compat} {rl_inc}".strip()

    def build(self):
        apply_conandata_patches(self)

        # E114: configure/config.status 内部以 umask 077 创建临时目录，
        # HMDFS 上组无写位导致写入失败 → 生成脚本替换（平台适配，非源码补丁）
        for script in ("configure", "config.status"):
            path = os.path.join(self.source_folder, script)
            if os.path.exists(path):
                with open(path) as f:
                    content = f.read()
                content = content.replace("umask 077", "umask 022")
                with open(path, "w") as f:
                    f.write(content)

        src = self.source_folder.replace("\\", "/")
        prefix = self.package_folder.replace("\\", "/")
        cppflags = f' CPPFLAGS="{self._cppflags}"'
        # §12.38①: hnp bash 作 CONFIG_SHELL 在 HMDFS 构建目录 getcwd 必挂
        # （autoconf re-exec 自身）→ env -u CONFIG_SHELL SHELL=/bin/sh +
        # 绝对路径（gtypist/2.10.1 已验证）；umask 022 前置（E114）
        self.run(
            f'umask 022 && env -u CONFIG_SHELL SHELL=/bin/sh '
            f'sh "{src}/configure" --prefix="{prefix}"{cppflags}',
            env="conanbuild",
        )
        # E074: HMDFS jobserver fifo EPERM → make -j1。
        # CPPFLAGS 必须在 make 命令行显式重传：手写根 Makefile（非
        # automake）不把 CPPFLAGS 落盘进 config.make，而 conanbuild env
        # 里 conan 注入的 CPPFLAGS 也不会被 env -u CONFIG_SHELL 保留出
        # 可见的注入路径（真机首验实测 pretty-csv.c 找不到
        # ncursesw/curses.h；诊断性补 CPPFLAGS 后全部 .o 一次通过）
        self.run(
            f'umask 022 && env -u CONFIG_SHELL SHELL=/bin/sh '
            f'make -j1{cppflags}',
            env="conanbuild")

    def package(self):
        # config.make 的 bindir 已指向 package_folder/bin，直接 make install
        #（install 目标依赖 all，产物已就绪；CPPFLAGS 同上须保持一致）
        cppflags = f' CPPFLAGS="{self._cppflags}"'
        self.run(
            f'umask 022 && env -u CONFIG_SHELL SHELL=/bin/sh '
            f'make install{cppflags}',
            env="conanbuild")

    def package_info(self):
        # R38: 产物为 pspg 命令行 pager（软件级 commands.json 已声明）
        self.cpp_info.bindirs = ["bin"]
