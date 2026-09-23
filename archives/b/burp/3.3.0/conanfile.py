#!/usr/bin/env python3
"""Conan recipe for burp 3.3.0 - rsync-based backup utility (C, AGPL-3.0)。

上游只发布 Makefile.am（无预生成 configure），且 OHOS 构建环境无 automake/libtool，
故随归档附带 CMakeLists.txt overlay（从 Makefile.am 的 main_SOURCES/runner_SOURCES
机械生成，含 $(VAR) 展开与反斜杠续行解析），build() 时由 conan 直接调用 CMake 构建。

OHOS 接线：CMakeToolchain（profile ohos-aarch64 自动映射 HarmonyOS/sysroot），
五个依赖包路径以 -D<X>_ROOT_DIR 传给 overlay（overlay 内部用 IMPORTED 目标指向
<ROOT>/lib 与 <ROOT>/include，与 conan 包目录布局一致）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy


class BurpConan(ConanFile):
    name = "burp"
    version = "3.3.0"
    description = "Burp - backup utility (rsync-based, client/server, incremental + block-level dedup)"
    license = "AGPL-3.0"
    url = "http://burp.grke.net/"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.2")
        self.requires("librsync/2.3.4")
        self.requires("check/0.15.2")
        self.requires("uthash/2.3.0")

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        copy(self, "CMakeLists.txt",
             src=self.recipe_folder, dst=self.export_sources_folder)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # overlay 用 ${X}_ROOT_DIR 定位依赖（包目录布局: include/ + lib/）
        for dep, var in (("openssl", "OPENSSL_ROOT_DIR"),
                         ("zlib", "ZLIB_ROOT_DIR"),
                         ("librsync", "LIBRSYNC_ROOT_DIR"),
                         ("check", "CHECK_ROOT_DIR"),
                         ("uthash", "UTHASH_ROOT_DIR")):
            tc.cache_variables[var] = self.dependencies[dep].package_folder
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
