#!/usr/bin/env python3
"""Conan recipe for ada 3.3.0 — WHATWG-compliant URL parser (CMake).

ada is a header + static library C++ project using CMake.
Patches provide std::ranges polyfill for OHOS libc++ (clang 15.0.4).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AdaConan(ConanFile):
    name = "ada"
    version = "3.3.0"
    description = "WHATWG-compliant and fast URL parser written in modern C++"
    license = "MIT"
    homepage = "https://github.com/ada-url/ada"
    url = ""  # CI fills this

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
        # Disable tests/benchmarks/tools in Conan build (avoids CPM git downloads)
        tc.cache_variables["ADA_TESTING"] = False
        tc.cache_variables["ADA_BENCHMARKS"] = False
        tc.cache_variables["ADA_TOOLS"] = False
        # OHOS libc++ needs explicit linking for C++ executables
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_CXX_FLAGS"] = "-stdlib=libc++"
            tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = "-lc++ -lpthread"
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
        self.cpp_info.libs = ["ada"]
        self.cpp_info.set_property("cmake_file_name", "ada")
        self.cpp_info.set_property("cmake_target_name", "ada::ada")
        self.cpp_info.set_property("pkg_config_name", "ada")
