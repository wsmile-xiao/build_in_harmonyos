#!/usr/bin/env python3
"""Conan recipe for generator 0.4.0 (CMake header-only library)."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class GeneratorConan(ConanFile):
    name = "generator"
    version = "0.4.0"
    description = "Single-header C++20 coroutine generator"
    license = "CC0-1.0"
    homepage = "https://github.com/TartanLlama/generator"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"run_upstream_tests": [True, False]}
    default_options = {"run_upstream_tests": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.options.run_upstream_tests:
            self.requires("catch2/2.13.10-r0", visible=False)

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True, filename="generator-0.4.0.tar.gz")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        if self.options.run_upstream_tests:
            CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["GENERATOR_BUILD_TESTS"] = bool(self.options.run_upstream_tests)
        tc.variables["GENERATOR_BUILD_PACKAGE"] = True
        tc.variables["GENERATOR_BUILD_PACKAGE_DEB"] = False
        tc.variables["GENERATOR_BUILD_PACKAGE_RPM"] = False
        tc.variables["GENERATOR_BUILD_PACKAGE_MSI"] = False
        tc.variables["CMAKE_CXX_STANDARD"] = 20
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.run_upstream_tests:
            cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "generator")
        self.cpp_info.set_property("cmake_target_name", "tl::generator")
        self.cpp_info.libs = []
