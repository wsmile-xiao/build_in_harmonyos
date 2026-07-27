#!/usr/bin/env python3
"""Conan recipe — libxxhash (xxHash) 0.8.3.

xxHash is an extremely fast non-cryptographic hash algorithm.
Built using the unofficial CMake build system (cmake_unofficial/).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibxxhashConan(ConanFile):
    name = "libxxhash"
    version = "0.8.3"
    description = "Extremely fast non-cryptographic hash algorithm (XXH32, XXH64, XXH3, XXH128)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/Cyan4973/xxHash"
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
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["XXHASH_BUILD_XXHSUM"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="cmake_unofficial")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["xxhash"]
