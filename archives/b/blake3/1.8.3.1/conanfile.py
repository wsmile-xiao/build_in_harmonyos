#!/usr/bin/env python3
"""Conan recipe for blake3 1.8.3.1 — CMake build system.

BLAKE3 is a fast cryptographic hash function (C implementation).
CMakeLists.txt is located in the c/ subdirectory of the source tree.
Build: static-only (R26), make -j1 (R9).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Blake3Conan(ConanFile):
    name = "blake3"
    version = "1.8.3.1"
    description = "Fast cryptographic hash function (C implementation)"
    license = "Apache-2.0"
    homepage = "https://github.com/BLAKE3-team/BLAKE3"
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
        # R26: Build static only — no .so to avoid polluting system lib paths
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # OHOS: CMake lacks a Platform/HarmonyOS module, so
        # CMAKE_SYSTEM_PROCESSOR is detected as "unknown" instead of "aarch64".
        # BLAKE3's CMakeLists.txt auto-detects NEON via CMAKE_SYSTEM_PROCESSOR,
        # which fails on OHOS. Use BLAKE3_USE_NEON_INTRINSICS to explicitly
        # enable NEON SIMD on aarch64 (CMAKE_SIZEOF_VOID_P == 8).
        # Guard with arch check to avoid build failure on x86_64 (AI Review).
        if self.settings.arch in ("armv8", "armv8_32", "armv8.3", "aarch64"):
            tc.variables["BLAKE3_USE_NEON_INTRINSICS"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMakeLists.txt is in the c/ subdirectory of the source tree
        cmake.configure(build_script_folder="c")
        # R9: Use -j1 for parallel constraint on OHOS platform
        cmake.build(cli_args=["--parallel", "1"])
        # Run upstream tests (make check) as required by CI L1 gate
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["blake3"]
