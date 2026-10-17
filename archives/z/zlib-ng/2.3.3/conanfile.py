#!/usr/bin/env python3
"""Conan recipe for zlib-ng 2.3.3 - CMake build system.

zlib-ng is a drop-in replacement for zlib with optimizations.
Built with ZLIB_COMPAT=OFF to provide zlib-ng native API (zng_* functions,
<zlib-ng.h> header, libz-ng.a). Not a system same-name library (system lib
is zlib/libz), so static build is sufficient and avoids .so signing.
"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ZlibNgConan(ConanFile):
    name = "zlib-ng"
    version = "2.3.3"
    description = "zlib replacement with optimizations for 'next generation' systems"
    license = "Zlib"
    homepage = "https://github.com/zlib-ng/zlib-ng"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["ZLIB_COMPAT"] = False
        tc.variables["WITH_GTEST"] = False
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
        self.cpp_info.libs = ["z-ng"]
        self.cpp_info.set_property("cmake_file_name", "zlib-ng")
        self.cpp_info.set_property("cmake_target_name", "zlib-ng::zlib-ng")
