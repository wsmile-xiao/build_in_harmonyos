#!/usr/bin/env python3
"""Conan recipe — desproxy 0.1.0 (autotools, command-line tool suite).

desproxy 是一组命令行工具（desproxy / desproxy-inetd / desproxy-socksserver /
desproxy-dns / socket2socket），用于将 TCP 流量隧道穿过 HTTP 代理。
纯 C、无外部依赖，autotools 构建。

HarmonyOS 适配要点:
  - 老式 C 代码在 desproxy.h 中直接定义全局变量（非 extern 声明），
    现代编译器默认 -fno-common 会触发 multiple definition 链接错误，
    通过 AutotoolsToolchain 注入 -fcommon（构建参数层修复，不修改源码）。
  - Makefile.in 无 VPATH，不支持 out-of-tree 构建 → in-source 构建。
  - 手写 install-sh 不尊重 DESTDIR → package() 手动 copy 二进制。
  - 1990s autoconf 生成的 config.status 依赖 $TMPDIR/csXXXXXX (mktemp -d)
    创建临时目录；OHOS worker 上 $TMPDIR 可能解析到不可写路径
    (Permission denied → Makefile 未生成)，配方显式把 TMPDIR 指向
    conan 构建目录（确定可写）。
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, chdir, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

BINS = ("desproxy", "desproxy-inetd", "desproxy-socksserver", "desproxy-dns", "socket2socket")


class DesproxyConan(ConanFile):
    name = "desproxy"
    version = "0.1.0"
    description = "A TCP tunnel for HTTP proxies (desproxy tool suite)"
    license = "GPL-2.0"
    homepage = "https://sourceforge.net/projects/desproxy/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 老 C 代码（头文件内定义全局变量）在 GCC>=10 / Clang 默认
        # -fno-common 下产生 multiple definition，注入 -fcommon 兼容。
        tc.extra_cflags.append("-fcommon")
        tc.generate()
        # 1990s autoconf config.status 用 $TMPDIR/csXXXXXX (mktemp -d) 建临时
        # 目录；OHOS 的 toybox mktemp -d 创建临时目录权限异常导致
        # "Permission denied" 且 Makefile 未生成。配方显式把 TMPDIR 指向
        # conan 构建目录（确定可写），配合 0001 patch 的当前目录兜底。
        env = Environment()
        env.define("TMPDIR", self.build_folder)
        # OHOS sysroot 的 libintl.h 不声明 gettext，源码在 HAVE_LIBINTL_H
        # 分支下 include libintl.h 后 clang 隐式函数声明报错
        # (-Wimplicit-function-declaration → error)。desproxy 为 CLI 工具，
        # i18n 非必需：预置 autoconf 缓存变量使 libintl.h 检测结果为 no，
        # config.h 不定义 HAVE_LIBINTL_H，源码走无 gettext 宏分支。
        env.define("ac_cv_header_libintl_h", "no")
        env.vars(self, scope="build").save_script("buildenv")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # desproxy Makefile.in 无 VPATH（1990s autoconf 产物），不支持
        # out-of-tree 构建，必须在源码目录内 in-source 构建。
        with chdir(self, self.source_folder):
            autotools.configure()
            autotools.make(args=["-j1"])

    def package(self):
        # 手写 install-sh 不尊重 DESTDIR，手动 copy 5 个二进制到 bin/
        for bin_name in BINS:
            copy(self, bin_name,
                 os.path.join(self.source_folder, "src"),
                 os.path.join(self.package_folder, "bin"),
                 keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
