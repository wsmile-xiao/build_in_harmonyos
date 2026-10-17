#!/usr/bin/env python3
"""Conan recipe for base64 0.5.0 (aklomp/base64) — CMake build.

Fast Base64 stream encoder/decoder library with SIMD codecs, plus a
command-line tool (base64). BSD-2-Clause license.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class Base64Conan(ConanFile):
    name = "base64"
    version = "0.5.0"
    description = "Fast Base64 stream encoder/decoder (aklomp/base64)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/aklomp/base64"
    url = "https://github.com/aklomp/base64"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Do not fail the build on warnings; keep upstream codec set default.
        tc.variables["BASE64_WERROR"] = "OFF"
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
        self.cpp_info.libs = ["base64"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "base64")
        self.cpp_info.set_property("cmake_target_name", "aklomp::base64")
