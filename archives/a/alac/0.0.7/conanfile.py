#!/usr/bin/env python3
"""Conan 2.x recipe — ALAC (Apple Lossless Audio Codec) 0.0.7

ALAC is a lossless audio codec developed by Apple.
Source: https://github.com/macosforge/alac
Build system: CMake
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, save


class AlacConan(ConanFile):
    name = "alac"
    version = "0.0.7"
    description = "Apple Lossless Audio Codec (ALAC) - reference implementation"
    license = "Apache-2.0"
    homepage = "https://github.com/macosforge/alac"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["ALAC"]
        self.cpp_info.includedirs = ["include"]