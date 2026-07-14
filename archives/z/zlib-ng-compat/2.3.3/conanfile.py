#!/usr/bin/env python3
"""Conan recipe for zlib-ng-compat 2.3.3 — CMake build system.

zlib is a system same-name library (/lib/libz.so*), so it must be built
static-only (R26) to avoid polluting system library paths.
Built with ZLIB_COMPAT=ON to provide zlib-compatible API.
"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ZlibNgCompatConan(ConanFile):
    name = "zlib-ng-compat"
    version = "2.3.3"
    description = "zlib-ng built in zlib-compat mode, drop-in replacement for zlib"
    license = "Zlib"
    homepage = "https://github.com/zlib-ng/zlib-ng"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

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
        # R26: zlib is a system same-name library, must build static
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # ZLIB_COMPAT=ON provides zlib-compatible API (libz.a instead of libz-ng.a)
        tc.variables["ZLIB_COMPAT"] = "ON"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        tc.variables["WITH_GTEST"] = "OFF"
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
        # With ZLIB_COMPAT=ON, the library is named libz.a (zlib-compatible name)
        self.cpp_info.libs = ["z"]