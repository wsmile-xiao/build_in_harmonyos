#!/usr/bin/env python3
"""Conan recipe — kalign 3.5.1 (CMake).

Kalign is a fast and accurate multiple sequence alignment tool.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rmdir
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KalignConan(ConanFile):
    name = "kalign"
    version = "3.5.1"
    description = "Kalign is a fast and accurate multiple sequence alignment tool"
    license = "Apache-2.0"
    homepage = "https://github.com/TimoLassmann/kalign"
    url = "https://github.com/TimoLassmann/kalign"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "openmp": [True, False],
    }
    default_options = {
        "shared": False,
        "openmp": False,
    }

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
        tc.variables["USE_OPENMP"] = self.options.openmp
        tc.variables["ENABLE_SSE"] = False
        tc.variables["ENABLE_AVX"] = False
        tc.variables["ENABLE_AVX2"] = False
        tc.variables["BUILD_PYTHON_MODULE"] = False
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.libs = ["kalign"]
        self.cpp_info.bindirs = ["bin"]
