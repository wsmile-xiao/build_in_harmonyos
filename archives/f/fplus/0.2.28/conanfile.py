#!/usr/bin/env python3
"""Conan recipe — fplus 0.2.28 (header-only CMake library).

FunctionalPlus is a header-only C++14 library. The upstream project
provides a CMake INTERFACE target (FunctionalPlus::fplus) and an official
conanfile.txt requiring doctest for tests only (not for consumers).
"""
from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
import os


class FplusConan(ConanFile):
    name = "fplus"
    version = "0.2.28"
    description = "FunctionalPlus - helps you write concise and readable C++ code"
    license = "BSL-1.0"
    homepage = "https://github.com/Dobiasd/FunctionalPlus"
    url = "https://github.com/Dobiasd/FunctionalPlus"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Header-only: no compilation needed.

    def package(self):
        # Header-only: copy include tree into package
        copy(self, pattern="*", src=os.path.join(self.source_folder, "include"), dst=os.path.join(self.package_folder, "include"))
        copy(self, pattern="LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "FunctionalPlus")
        self.cpp_info.set_property("cmake_target_name", "FunctionalPlus::fplus")
        self.cpp_info.components["fplus"].libs = []
        self.cpp_info.components["fplus"].set_property("cmake_target_name", "FunctionalPlus::fplus")
