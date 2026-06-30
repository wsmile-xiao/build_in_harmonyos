#!/usr/bin/env python3
"""Conan recipe — CMake project (zxc 0.9.1).

High-performance asymmetric lossless compression library.
Build system: CMake
License: BSD-3-Clause

This template enforces R26: BUILD_SHARED_LIBS=OFF for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ZxcConan(ConanFile):
    name = "zxc"
    version = "0.9.1"
    description = "High-performance asymmetric lossless compression library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/hellobertrand/zxc"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external dependencies
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: Terminal tools must be statically linked for DevBox deployment
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # Disable -march=native for portability
        tc.variables["ZXC_NATIVE_ARCH"] = "OFF"
        # Disable LTO for compatibility
        tc.variables["ZXC_ENABLE_LTO"] = "OFF"
        # OHOS workaround: CMake doesn't recognize HarmonyOS, so force Linux/aarch64
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
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
        self.cpp_info.libs = ["zxc"]
        # Required for static linking: disables dllimport/dllexport annotations
        self.cpp_info.defines.append("ZXC_STATIC_DEFINE")
