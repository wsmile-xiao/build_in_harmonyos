#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Libdxfrw, libdxfrw, 0.5.12, libdxfrw 0.5.12, MIT, 
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

import os
import shutil


class LibdxfrwConan(ConanFile):
    name = "libdxfrw"
    version = "0.5.12"
    description = "libdxfrw 0.5.12"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/LibreCAD/libdxfrw"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        # 官方 tarball 中 ar-lib/config.guess/config.sub/depcomp/install-sh/ltmain.sh/missing
        # 是悬空的绝对路径符号链接（指向 /usr/share/automake-1.12*），CI 干净环境不可用。
        # 随配方打包真实脚本，source() 中解压后替换。
        copy(self, "build-aux/*", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 修复官方 tarball 中悬空的 automake 辅助脚本符号链接（E490/E011 相关）
        for name in ("ar-lib", "config.guess", "config.sub", "depcomp",
                     "install-sh", "ltmain.sh", "missing"):
            target = os.path.join(self.source_folder, name)
            if os.path.islink(target) or not os.path.exists(target):
                here = os.path.join(self.export_sources_folder, "build-aux", name)
                if os.path.isfile(here):
                    if os.path.lexists(target):
                        os.unlink(target)
                    shutil.copy2(here, target)
                    os.chmod(target, 0o755)
        # E011: HMDFS 上 umask 077 导致 config.status 临时目录不可写（subs1.awk Permission denied）
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            data = open(configure, "r", encoding="utf-8", errors="replace").read()
            if "umask 077" in data:
                open(configure, "w", encoding="utf-8").write(data.replace("umask 077", "umask 022"))
                os.chmod(configure, 0o755)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 安装头文件位于 include/libdxfrw0/（libdxfrw.pc 中 Cflags: -I${includedir}/libdxfrw@LIBRARY_AGE@）
        self.cpp_info.includedirs = ["include/libdxfrw0"]
        self.cpp_info.libs = ["dxfrw"]
