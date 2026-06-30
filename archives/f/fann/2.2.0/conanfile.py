#!/usr/bin/env python3
"""Conan recipe — fann 2.2.0 (CMake build system)

R26: Static linking for terminal tools (BUILD_SHARED_LIBS=OFF).
"""

import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class FannConan(ConanFile):
    name = "fann"
    version = "2.2.0"
    description = "Fast Artificial Neural Network Library (FANN)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/libfann/fann"
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
        # R26: Terminal tools must be statically linked
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # CMake 4.x compatibility for old cmake_minimum_required(VERSION 2.8)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
        self.cpp_info.libs = ["fann", "floatfann", "doublefann", "fixedfann"]
