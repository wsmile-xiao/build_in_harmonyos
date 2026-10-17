#!/usr/bin/env python3
"""Conan recipe — 7bitdi 3.4.0 (C++17 header-only dependency injection).

7bitDI is a header-only DI container (C++17). This recipe builds the
HeaderOnly variant: nothing is compiled, the public headers under
Include/ are installed together with the upstream CMake package config.

R32 note: no settings.os branch is needed — the OHOS-adapted conan
maps os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS via CMakeToolchain.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SevenBitDiConan(ConanFile):
    name = "7bitdi"
    version = "3.4.0"
    description = "7bitDI - a C++17 dependency injection container (header-only)"
    license = "MIT"
    homepage = "https://github.com/7bitcoder/7bitDI"
    url = "https://github.com/7bitcoder/7bitDI"  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # header-only, no runtime dependencies
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 7bitDI: header-only variant, install headers + CMake config
        tc.variables["_7BIT_DI_LIBRARY_TYPE"] = "HeaderOnly"
        tc.variables["_7BIT_DI_INSTALL"] = "ON"
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
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
        # header-only: no libraries to link, headers + CMake config installed
        self.cpp_info.set_property("cmake_file_name", "7bitdi")
        self.cpp_info.set_property("cmake_target_name", "7bitdi::7bitdi")
