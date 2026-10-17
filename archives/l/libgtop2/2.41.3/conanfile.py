#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe — libgtop2 2.41.3（GNOME 系统信息采集库 libgtop）。

上游：https://gitlab.gnome.org/GNOME/libgtop   tag 2.41.3 = commit 526a5169…
源码：https://download.gnome.org/sources/libgtop/2.41/libgtop-2.41.3.tar.xz
构建：autotools（tarball 内含预生成 configure；上游无 meson.build）
产物：libgtop-2.0（共享/静态）、include/libgtop-2.0/、lib/pkgconfig/libgtop-2.0.pc、
      libexec/libgtop_daemon2、libexec/libgtop_server2（特权辅助进程）

─ 上游直接依赖（configure.ac / Makefile.am 判据） ────────────────────────────
  * glib-2.0 >= 2.6.0 / gobject-2.0 >= 2.26.0
      configure.ac:107  PKG_CHECK_MODULES(GLIB, glib-2.0 >= … gobject-2.0 >= …)
      lib/Makefile.am:11  libgtop_2_0_la_LIBADD = $(GLIB_LIBS) …
      libgtop-2.0.pc.in:6  Requires: glib-2.0（对外传播）
      公共头文件 glibtop.h:29-30 直接 #include <glib.h> / <glib-object.h> → 头文件传染
  * proxy-libintl（intl 提供者）
      lib/read.c:36 等经 glib 的 <glib/gi18n-lib.h> 使用 ngettext()，而该头文件无条件
      #include <libintl.h>。OHOS SDK sysroot 的 libintl.h 是空壳（无 ngettext 声明），
      必须让 proxy-libintl 的 libintl.h 进入编译行；g_libintl_* 符号已被静态链接进
      libglib-2.0.so，因此只需 include 可见（实测链接无需额外参数）。

─ HarmonyOS PC（aarch64）适配改动 ────────────────────────────────────────────
  F1  patches/0001   config.guess 增加 HarmonyOS/ohos 三元组（E007）
  F2  patches/0002   config.sub 接受 ohos + 放行 linux-ohos 内核组合（E072）
  F3  patches/0003   config.status 模板 umask 077 → 022（HMDFS 上 confXXXXXX 不可写，E011）
  F4  build()        打补丁会刷新 configure 的 mtime，使 doc/stamp-vti 判定过期，
                     连带 version.texi/libgtop2.info 走 texinfo 链；OHOS 无 texinfo
                     (makeinfo)。打完补丁后还原 configure 原始 mtime，让上游随包发布
                     的 doc/libgtop2.info 直接复用（否则不仅构建失败，mdate-sh 解析
                     失败还会把 version.texi 写成 set 的环境变量转储）。
  F5  generate()     关闭 OHOS 上不可用的可选件：--without-x（无 X11/Xauth）、
                     --enable-introspection=no（g-ir-scanner 依赖闭包不完整，E212）。

─ 上游测试 ───────────────────────────────────────────────────────────────────
  上游无自动化测试套件（无 tests/ 目录，无 check_PROGRAMS/TESTS）；
  唯一可运行入口是 examples/ 的 20 个样例（noinst_PROGRAMS，--with-examples 默认 yes）。
  实测 19/20 退出码 0；`disk` 样例因 /proc/diskstats 对非 root 返回 EACCES 而 abort，
  属平台限制（libgtop 的 disk/mount 信息本需 setuid 辅助进程），非适配缺陷。
  统计与逐项结果见 test_package/MANIFEST.yml、notes.md 与 reports/。
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class Libgtop2Conan(ConanFile):
    name = "libgtop2"
    version = "2.41.3"
    description = ("GNOME libgtop — portable library to retrieve system information "
                   "(CPU, memory, swap, load, uptime, processes, disks, network)")
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libgtop"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("gnome", "system-monitor", "libgtop", "procfs")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # R32: OHOS 归入 Linux 家族，不能用 == "Linux"；libgtop 的 sysdeps 只有 linux 分支可用
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux/OHOS, not {self.settings.os}")

    def requirements(self):
        # configure.ac:107 —— glib-2.0 / gobject-2.0；公共头文件传染 glib.h/glib-object.h
        self.requires("glib/2.88.3", transitive_headers=True, transitive_libs=True)
        # lib/read.c 使用 ngettext()：proxy-libintl 提供带 ngettext 声明的 libintl.h
        self.requires("proxy-libintl/0.5")

    def build_requirements(self):
        # configure.ac:107 PKG_CHECK_MODULES 需要 pkg-config；固定制品仓版本，不依赖宿主实现
        self.tool_requires("pkgconf/3.0.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # E490：部分 HarmonyOS PC 适配路径复制源码树时会丢失可执行位，而 autotools
        # 辅助脚本必须以可执行方式调用（configure / config.guess / config.sub / …）。
        for name in ("configure", "config.guess", "config.sub", "install-sh",
                     "missing", "depcomp", "compile", "ltmain.sh"):
            path = os.path.join(self.source_folder, name)
            if os.path.isfile(path):
                os.chmod(path, os.stat(path).st_mode | 0o111)

    def generate(self):
        # autotools configure 用 PKG_CHECK_MODULES 发现 glib-2.0/gobject-2.0；
        # 生成的 .pc 落在 generators_folder，需显式让 configure 看到（见下）。
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        # F5: OHOS 无 X11（daemon 的 Xauth 分支随之关闭）；g-ir-scanner 不可用
        tc.configure_args.extend([
            "--without-x",
            "--enable-introspection=no",
            "--with-examples=yes",
        ])
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        # PkgConfigDeps 的 .pc 不会自动进入 PKG_CONFIG_PATH；以 VAR=value 形式传给
        # configure，既作用于本次 configure，也写进生成的 Makefile（本仓惯例）。
        tc.configure_args.append(f"PKG_CONFIG_PATH={self.generators_folder}")
        tc.generate()

    def build(self):
        # F4: 必须在打补丁前记录 configure 的 mtime —— 补丁刷新 mtime 会让
        # doc/stamp-vti（依 $(top_srcdir)/configure）判定过期，进而重建
        # version.texi / doc/libgtop2.info 并调用 makeinfo（OHOS 无 texinfo）。
        configure = os.path.join(self.source_folder, "configure")
        stat_result = os.stat(configure)
        apply_conandata_patches(self)
        os.utime(configure, (stat_result.st_atime, stat_result.st_mtime))

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        Autotools(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 与 Debian libgtop2 打包一致：libtool 归档文件对消费者无用（dh_install 同款删除）
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for name in os.listdir(libdir):
                if name.endswith(".la"):
                    os.remove(os.path.join(libdir, name))

    def package_info(self):
        self.cpp_info.libs = ["gtop-2.0"]
        # 头文件安装到 ${includedir}/libgtop-2.0（glibtop.h + glibtop/*.h），
        # 上游 libgtop-2.0.pc 的 Cflags 同为 -I${includedir}/libgtop-2.0
        self.cpp_info.includedirs = ["include/libgtop-2.0"]
        # libgtop_server2 / libgtop_daemon2 装在 libexec/（特权辅助进程，OHOS 上不可
        # setuid），不是给消费者用的 CLI，故不暴露 bin/
        self.cpp_info.bindirs = []
        # libgtop-2.0 依赖 glib 的 glib-2.0/gobject-2.0 组件；proxy-libintl 提供
        # intl（ngettext）符号，静态归档消费者链接时需要，故一并传播（Conan 要求
        # 所有直接依赖都出现在 cpp_info.requires 中）。
        self.cpp_info.requires = [
            "glib::glib",
            "glib::gobject",
            "proxy-libintl::proxy-libintl",
        ]
        self.cpp_info.set_property("pkg_config_name", "libgtop-2.0")
        self.cpp_info.set_property("cmake_file_name", "libgtop2")
        self.cpp_info.set_property("cmake_target_name", "libgtop2::libgtop2")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl", "pthread", "rt"]
