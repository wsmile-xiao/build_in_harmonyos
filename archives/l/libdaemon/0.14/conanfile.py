#!/usr/bin/env python3
"""Conan recipe for libdaemon 0.14 — Lightweight C library for writing UNIX daemons.

Autotools (configure + make). R26: 默认静态编译。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibdaemonConan(ConanFile):
    name = "libdaemon"
    version = "0.14"
    description = "Lightweight C library for writing UNIX daemons"
    license = "LGPL-2.1"
    homepage = "https://0pointer.de/lennart/projects/libdaemon/"
    url = "https://0pointer.de/lennart/projects/libdaemon/"

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

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: 静态编译，避免污染系统库路径
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
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
        # 库文件名为 libdaemon.a，CMakeDeps find_library 会自动加 lib 前缀，
        # 因此 libs 必须写去前缀的 "daemon"，否则在 HarmonyOS（CMake 未知平台）上
        # find_library(NAMES libdaemon) 会错误地查找 liblibdaemon.a 而失败。
        self.cpp_info.libs = ["daemon"]
