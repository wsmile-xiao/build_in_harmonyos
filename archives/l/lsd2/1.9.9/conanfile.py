#!/usr/bin/env python3
"""Conan recipe — lsd2 1.9.9 (CMake, standalone CLI tool).

Upstream: https://github.com/tothuhien/lsd2
LSD2 estimates rates and dates from phylogenies under least-squares models.
Upstream CMakeLists.txt builds the `lsd2` executable by default and ships no
install() rule, so package() copies the built binary manually.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class Lsd2Conan(ConanFile):
    name = "lsd2"
    version = "1.9.9"
    description = "LSD2 — least-squares methods to estimate rates and dates from phylogenies"
    license = "MIT"
    homepage = "https://github.com/tothuhien/lsd2"
    url = "https://github.com/tothuhien/lsd2"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream default: stand-alone program (USE_LSD2 off -> add_executable)
        tc.variables["USE_LSD2"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # R9: single job (this FS rejects make jobserver mkfifo)
        tc.variables["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # R9: single job (CMAKE_BUILD_PARALLEL_LEVEL=1 set in generate();
        # also this FS rejects make jobserver mkfifo)
        cmake.build()

    def package(self):
        # Upstream CMakeLists has no install(); copy the built binary directly
        copy(self, "lsd2", self.build_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]