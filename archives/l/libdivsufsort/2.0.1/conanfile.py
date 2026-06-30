#!/usr/bin/env python3
"""Conan recipe — libdivsufsort 2.0.1 (CMake).

Build system: CMake
License: MIT
No dependencies.

R26: Static linking enforced via BUILD_SHARED_LIBS=OFF.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibdivsufsortConan(ConanFile):
    name = "libdivsufsort"
    version = "2.0.1"
    description = "Lightweight suffix-sorting library"
    license = "MIT"
    homepage = "https://github.com/y-256/libdivsufsort"
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
        # CMake 4.x removed compatibility with < 3.5
        # Must be a cache variable (-D flag) because cmake_minimum_required()
        # is processed before the toolchain file is loaded
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
        self.cpp_info.libs = ["divsufsort"]
