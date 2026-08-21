#!/usr/bin/env python3
"""
Conan recipe for base16384 v2.3.2 — OHOS (OpenHarmony) aarch64 adaptation.

base16384 is a C library for encoding binary data to UTF-16BE CJK characters.
No external dependencies. CMake build system.

Patch: bump cmake_minimum_required to 3.5 for OHOS compatibility.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class Base16384Conan(ConanFile):
    name = "base16384"
    version = "2.3.2"
    description = "Encode binary files to printable UTF-16BE using CJK ideographs (2^14 alphabet)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/fumiama/base16384"
    url = ""

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
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["base16384"]
