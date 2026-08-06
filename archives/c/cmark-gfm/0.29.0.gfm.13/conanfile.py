#!/usr/bin/env python3
"""Conan recipe — cmark-gfm 0.29.0.gfm.13 (GitHub Flavored Markdown parser).

GitHub Flavored Markdown (GFM) parser and renderer - C implementation
of CommonMark with GitHub extensions.
Build system: CMake
License: BSD-2-Clause

Builds static libraries only to avoid OHOS ELF signature issues with shared libs.
"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CmarkGfmConan(ConanFile):
    name = "cmark-gfm"
    version = "0.29.0.gfm.13"
    description = "GitHub Flavored Markdown (GFM) parser and renderer - C implementation of CommonMark with GitHub extensions"
    license = "BSD-2-Clause"
    homepage = "https://github.com/github/cmark-gfm"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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
        # Build static only to avoid OHOS ELF signature issues with shared libs
        tc.variables["CMARK_SHARED"] = "OFF"
        tc.variables["CMARK_STATIC"] = "ON"
        if self.settings.os in ("Linux", "OHOS"):
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["cmark-gfm", "cmark-gfm-extensions"]
        self.cpp_info.bindirs = ["bin"]
