#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Libmowgli2, libmowgli-2, 2.1.3, libmowgli-2 2.1.3, MIT, 
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Libmowgli2Conan(ConanFile):
    name = "libmowgli-2"
    version = "2.1.3"
    description = "libmowgli-2 2.1.3"
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
        pass

    def layout(self):
        basic_layout(self)
        # libmowgli-2 顶层 Makefile 是源码静态文件（include buildsys.mk），必须 in-source 构建
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="libmowgli-2-2.1.3.tar.gz")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # config.guess (2014) 无法识别 HarmonyOS，显式指定 build triplet
        tc.configure_args.append("--build=aarch64-linux-gnu")
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
        self.cpp_info.libs = ["mowgli-2"]
        # buildsys.mk 将头文件安装到 include/libmowgli-2/ 子目录，须显式声明
        self.cpp_info.includedirs = ["include/libmowgli-2"]
