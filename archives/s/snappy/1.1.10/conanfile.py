#!/usr/bin/env python3
"""Conan recipe for snappy 1.1.10 — fast compression/decompression library.

Snappy is a fast data compression/decompression library developed by Google.
It aims for high speed rather than maximum compression ratio.

Build system: CMake
Library output: libsnappy
No external conan dependencies (gtest/benchmark submodules only used for
optional upstream tests, disabled here; test_package covers validation).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SnappyConan(ConanFile):
    name = "snappy"
    version = "1.1.10"
    description = "Fast compression/decompression library by Google"
    license = "BSD-3-Clause"
    homepage = "https://github.com/google/snappy"
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
        tc.variables["SNAPPY_BUILD_TESTS"] = False
        tc.variables["SNAPPY_BUILD_BENCHMARKS"] = False
        tc.variables["SNAPPY_INSTALL"] = True
        # E103/E187: snappy 1.1.10 declares cmake_minimum_required(VERSION 3.1);
        # CMake >= 4 dropped compatibility with < 3.5 policies — force minimum.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # snappy 1.1.10 builds with -Werror on Clang; snappy.cc:1293 triggers
        # -Wsign-compare with clang 15 (fixed upstream in 1.2.x). Downgrade only
        # this specific diagnostic to a warning (E293 pattern; no global -Wno-error).
        tc.extra_cxxflags.append("-Wno-error=sign-compare")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)  # no-op when no patches declared
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["snappy"]
