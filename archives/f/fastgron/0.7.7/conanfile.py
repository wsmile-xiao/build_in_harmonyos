#!/usr/bin/env python3
"""Conan recipe — fastgron 0.7.7 (CMake, C++, terminal tool).

This template enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.layout import basic_layout


class FastgronConan(ConanFile):
    name = "fastgron"
    version = "0.7.7"
    description = "fastgron - high-performance JSON to GRON converter"
    license = "MIT"
    homepage = "https://github.com/adamritter/fastgron"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.cache_variables["BUILD_SHARED_LIBS"] = "OFF"
        # Disable optional CURL dependency (headers not available on target)
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_CURL"] = "ON"
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
        self.cpp_info.bin_dirs = ["bin"]
