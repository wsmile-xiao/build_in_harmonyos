#!/usr/bin/env python3
"""Conan recipe template — CMake projects.

Usage: Replace Libdeflate, libdeflate, 1.25, Optimized DEFLATE/deflate/zlib/gzip compression library, MIT, https://github.com/ebiggers/libdeflate
       Fill in requires() and cpp_info.libs as needed.

This template enforces R26: BUILD_SHARED_LIBS=OFF for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibdeflateConan(ConanFile):
    name = "libdeflate"
    version = "1.25"
    description = "Optimized DEFLATE/deflate/zlib/gzip compression library"
    license = "MIT"
    homepage = "https://github.com/ebiggers/libdeflate"
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
        # R26: Terminal tools must be statically linked for DevBox deployment
        tc.variables["LIBDEFLATE_BUILD_SHARED_LIB"] = "OFF"
        tc.variables["LIBDEFLATE_BUILD_STATIC_LIB"] = "ON"
        # R26: cmake_layout handles CMAKE_INSTALL_PREFIX; do not hardcode it.
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
        # Actual artifact is libdeflate.a; Conan prepends "lib" prefix, so the
        # lib name (without prefix/extension) is "deflate".
        self.cpp_info.libs = ["deflate"]
        self.cpp_info.includedirs = ["include"]
        # Keep the CMake target name stable for consumers.
        self.cpp_info.set_property("cmake_file_name", "libdeflate")
        self.cpp_info.set_property("cmake_target_name", "libdeflate::libdeflate")
        self.cpp_info.set_property("pkg_config_name", "libdeflate")
