#!/usr/bin/env python3
"""Conan recipe for u8g2 2.36.2 — CMake projects.

u8g2 is a monochrome graphics library for embedded displays.
The upstream CMakeLists.txt builds csrc/*.c into libu8g2 and
installs headers to include/u8g2 plus a CMake package config.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class U8G2Conan(ConanFile):
    name = "u8g2"
    version = "2.36.2"
    description = "u8g2 monochrome graphics library for embedded displays"
    license = "BSD-2-Clause"
    homepage = "https://github.com/olikraus/u8g2"
    url = "https://github.com/olikraus/u8g2"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 默认静态链接（可通过 options.shared 开启动态）
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["u8g2"]
        self.cpp_info.includedirs = ["include"]