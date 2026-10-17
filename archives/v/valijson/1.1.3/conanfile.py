#!/usr/bin/env python3
"""Conan recipe — valijson 1.1.3 (CMake header-only library).

valijson is a header-only C++ library for JSON Schema validation.
It uses CMake with INTERFACE library target (no compilation needed).
1.1.3 upstream switched string-to-double parsing to internal/double_parser.hpp
with automatic std::from_chars / istringstream fallback detection, so the
1.1.1-era from_chars patches are no longer required.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class ValijsonConan(ConanFile):
    name = "valijson"
    version = "1.1.3"
    description = "Header-only C++ library for JSON Schema validation"
    license = "BSD-2-Clause"
    homepage = "https://github.com/tristanpenman/valijson"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake does not recognize OHOS as a target platform
        if self.settings.os in ("Linux", "OHOS"):
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
        self.cpp_info.libs = []