#!/usr/bin/env python3
"""Conan recipe — libucl 0.9.4 (CMake build system).

Build system: CMake (CMakeLists.txt present, no configure script).
License: BSD-2-Clause.
R26: Static linking enforced via BUILD_SHARED_LIBS=OFF.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibuclConan(ConanFile):
    name = "libucl"
    version = "0.9.4"
    description = "Universal Configuration Library (UCL) — a configuration parser library"
    license = "BSD-2-Clause"
    homepage = "https://github.com/vstakhov/libucl"
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
        # R26: Terminal tools must be statically linked
        tc.cache_variables["BUILD_SHARED_LIBS"] = "OFF"
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
        self.cpp_info.libs = ["ucl"]
