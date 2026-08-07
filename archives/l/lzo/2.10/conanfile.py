#!/usr/bin/env python3
"""Conan recipe for lzo 2.10 — CMake build system.

Uses CMake instead of Autotools because config.status fails on HarmonyOS
(temporary directory creation not supported on HMDFS).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LzoConan(ConanFile):
    name = "lzo"
    version = "2.10"
    description = "A portable lossless data compression library"
    license = "GPL-2.0+"
    homepage = "https://www.oberhumer.com/opensource/lzo/"
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

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake doesn't recognize HarmonyOS, use Linux platform
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if not self.options.shared:
            tc.variables["BUILD_SHARED_LIBS"] = False
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
        self.cpp_info.libs = ["lzo2"]
        self.cpp_info.includedirs = ["include"]
