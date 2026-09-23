#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Liboggz, liboggz, 1.1.1, liboggz 1.1.1, MIT, 
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LiboggzConan(ConanFile):
    name = "liboggz"
    version = "1.1.1"
    description = "liboggz 1.1.1"
    license = "MIT"
    homepage = ""
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libogg/1.3.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        # HMDFS 大小写不敏感：tarball 根级 PATCHES(文件) 与配方导出的 patches/ 目录冲突，
        # 解压时排除该上游补丁说明文件（非构建必需）
        get(self, **self.conan_data["sources"], strip_root=True, excludes=["*PATCHES"])

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
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
        # 库文件 liboggz.a → 链接名 oggz（-loggz）
        self.cpp_info.libs = ["oggz"]
        # 头文件 <oggz/oggz.h> 包含 <ogg/ogg.h>，需向消费者传递 libogg 的 include/链接
        self.cpp_info.requires.append("libogg::libogg")
