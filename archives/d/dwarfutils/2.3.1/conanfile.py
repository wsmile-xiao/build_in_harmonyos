#!/usr/bin/env python3
"""Conan recipe — dwarfutils (libdwarf) 2.3.1.

dwarfutils 提供 libdwarf 库和 dwarfdump 工具，用于读取/生成 DWARF 调试信息。
构建系统：CMake
平台：OHOS aarch64 / Linux / macOS
依赖：零强制依赖（zlib/zstd 可选）
"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class DwarfutilsConan(ConanFile):
    name = "dwarfutils"
    version = "2.3.1"
    description = "libdwarf — DWARF 调试信息读取/生成库及 dwarfdump 工具"
    license = "LGPL-2.1-only"
    homepage = "https://www.prevanders.net/dwarf.html"
    url = ""

    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    options = {"with_test": [True, False]}
    default_options = {"with_test": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["DO_TESTING"] = "ON" if self.options.with_test else "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游测试：仅在 with_test=True 时执行 dwarfutils 官方测试套件
        if self.options.with_test:
            cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["dwarf"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
