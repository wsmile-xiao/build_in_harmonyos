#!/usr/bin/env python3
"""Conan recipe for lzma (XZ Utils) 5.6.2 — CMake build.

Uses CMake instead of Autotools because autotools config.status
fails on HarmonyOS due to temp directory permission issues (HMDFS).
"""
from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LzmaConan(ConanFile):
    name = "lzma"
    version = "5.6.2"
    description = "LZMA/XZ tools"
    license = "Public Domain"
    homepage = "https://tukaani.org/xz/"

    package_type = "static-library"  # R26: always static, no shared option

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
        # E092: CMake doesn't recognize HarmonyOS as a platform.
        # Map to Linux which is compatible for aarch64-ohos.
        if self.settings.os in ("Linux", "OHOS"):
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # R26: System-name library (liblzma) — always static to avoid polluting /lib
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
        self.cpp_info.libs = ["lzma"]
        self.cpp_info.bindirs = ["bin"]
