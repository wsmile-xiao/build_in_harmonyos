#!/usr/bin/env python3
"""Conan recipe — audacious 4.5.1（轻量级音频播放器核心库）。

audacious 使用自研 buildsys.mk 构建系统（非 automake），关键适配点：
  1. 仅支持源内构建（buildsys.mk 无 VPATH），layout() 必须
     folders.source == folders.build
  2. 上游无自动化测试（buildsys.mk 无 check 目标），test_package
     验证主程序 --version + 共享库安装
  3. 依赖 glib/2.88.0（configure 检测 glib-2.0 >= 2.32），
     需通过 PKG_CONFIG_PATH 提供 glib-2.0.pc / gmodule-2.0.pc
  4. D-Bus/GTK/Qt 均可禁用（OHOS 无桌面会话环境）
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class AudaciousConan(ConanFile):
    name = "audacious"
    version = "4.5.1"
    description = (
        "Audacious — lightweight audio player core library (libaudcore) "
        "and utilities (audacious/audtool)."
    )
    license = "BSD-3-Clause"
    homepage = "https://www.audacious-media-player.org/"
    url = "https://github.com/audacious-media-player/audacious"

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("glib/2.88.0")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def layout(self):
        # buildsys.mk 不支持 VPATH（out-of-source build 会报
        # "No targets specified and no makefile found"），必须源内构建
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = "conan"

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-gtk",
            "--disable-qt",
            "--disable-dbus",
            "--disable-valgrind",
            "--disable-nls",
        ])
        tc.generate()
        PkgConfigDeps(self).generate()

    def build(self):
        autotools = Autotools(self)
        # AUD_COMMON_PROGS 强制检测 gio-2.0/gio-unix-2.0（即使 D-Bus 已禁用），
        # OHOS glib 包不含 gio-unix-2.0.pc → 预设非空值跳过 pkg-config 查询
        # （configure 用 test -n "$GIO_CFLAGS" 判断，空字符串不通过）
        os.environ["GIO_CFLAGS"] = " "
        os.environ["GIO_LIBS"] = " "
        # E011: config.status 用 umask 077 创建临时目录，OHOS 沙箱下不可写
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        "umask 077", "umask 022")
        autotools.configure()
        nproc = os.cpu_count() or 4
        self.run(f"make -j{nproc}")
        # 上游无自动化测试（buildsys.mk 无 check 目标、无 TESTS、
        # 无 tests/ 目录）。消费者侧 test_package 验证核心产物。

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["audcore", "audtag"]
        self.cpp_info.requires = ["glib::glib"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
