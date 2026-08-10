#!/usr/bin/env python3
"""Conan recipe for OpenCC (Open Chinese Convert) 1.1.9.

OpenCC is an open-source Chinese conversion library supporting
Simplified/Traditional Chinese conversion with dictionary-based engine.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class OpenccConan(ConanFile):
    name = "opencc"
    version = "1.1.9"
    description = "Open Chinese Convert - Simplified/Traditional Chinese conversion library and tools"
    license = "Apache-2.0"
    homepage = "https://github.com/BYVoid/OpenCC"

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
        tc.variables["ENABLE_DARTS"] = "ON"
        tc.variables["ENABLE_GTEST"] = "OFF"
        tc.variables["BUILD_PYTHON"] = "OFF"
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
        self.cpp_info.libs = ["opencc", "marisa"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share/opencc"]
