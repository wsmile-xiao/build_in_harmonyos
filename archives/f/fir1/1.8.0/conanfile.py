#!/usr/bin/env python3
"""Conan recipe — fir1 1.8.0 (CMake project, C++11).

fir1: efficient finite impulse response (FIR) filter class in C++,
with LMS / NLMS adaptive filtering (https://github.com/berndporr/fir1).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Fir1Conan(ConanFile):
    name = "fir1"
    version = "1.8.0"
    description = "Efficient FIR filter class with LMS/NLMS adaptive filtering (C++)"
    license = "MIT"
    homepage = "https://github.com/berndporr/fir1"
    url = ""  # CI fills this

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
        # R26: static by default
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
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
        self.cpp_info.libs = ["fir_static"]
