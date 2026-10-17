#!/usr/bin/env python3
"""Conan recipe — gason 1.0.0 (C++11 JSON parser, static library).

gason is a small dependency-free C++11 JSON parser (gason.h + gason.cpp).
Upstream provides a CMakeLists.txt building a static library plus demo
binaries; the release tarball does not include the rapidjson submodule, so
the benchmark target is disabled via patch (option BUILD_GASON_BENCHMARK=OFF).

Patch 0001 also bumps cmake_minimum_required to 3.10 (CMake >= 4.1 refuses
< 3.5) and adds install() rules for the static lib and the public header.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class GasonConan(ConanFile):
    name = "gason"
    version = "1.0.0"
    description = "A g++ optimized JSON parser"
    license = "MIT"
    homepage = "https://github.com/vivkin/gason"
    url = "https://github.com/vivkin/gason"

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
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["BUILD_GASON_BENCHMARK"] = "OFF"
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
        self.cpp_info.libs = ["gason"]
        self.cpp_info.set_property("cmake_file_name", "gason")
        self.cpp_info.set_property("cmake_target_name", "gason::gason")
