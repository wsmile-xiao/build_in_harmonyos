#!/usr/bin/env python3
"""Conan recipe — detours 4.0.1 (CMake project).

Microsoft Detours: library for intercepting x86/x64/ARM/ARM64 function calls.
Source: https://github.com/microsoft/Detours

Adapted for HarmonyOS PC (aarch64) with Windows API compatibility headers
and CMake build system (replaces original NMAKE build).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class DetoursConan(ConanFile):
    name = "detours"
    version = "4.0.1"
    description = "Microsoft Detours — library for intercepting function calls"
    license = "MIT"
    homepage = "https://github.com/microsoft/Detours"
    url = ""  # CI fills this

    package_type = "static-library"

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
        # R26: static library (Detours only supports static linking)
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # E092: CMake does not recognize HarmonyOS
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
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
        self.cpp_info.libs = ["detours"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
