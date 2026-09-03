#!/usr/bin/env python3
"""Conan recipe for cbitset 0.4.0 on HarmonyOS PC."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get


class CbitsetConan(ConanFile):
    name = "cbitset"
    version = "0.4.0"
    description = "Simple bitset library in C"
    license = "MIT"
    homepage = "https://github.com/lemire/cbitset"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        copy(self, "conandata.yml", dst=".", src=self.recipe_folder)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CBITSET_BUILD_TESTS"] = True
        tc.variables["CBITSET_BUILD_BENCHMARKS"] = False
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
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["cbitset"]
        self.cpp_info.set_property("cmake_file_name", "cbitset")
        self.cpp_info.set_property("cmake_target_name", "cbitset::cbitset")
