#!/usr/bin/env python3
"""Conan recipe — drafter 5.1.0 (CMake project).

Native C/C++ API Blueprint Parser.
Uses CMake build system with static linking (R26).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class DrafterConan(ConanFile):
    name = "drafter"
    version = "5.1.0"
    description = "Native C/C++ API Blueprint Parser"
    license = "MIT"
    homepage = "https://github.com/apiaryio/drafter"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external dependencies - all vendored in packages/
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # CMake policy compatibility for older submodules with CMake 4.x
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
        self.cpp_info.libs = ["drafter"]
