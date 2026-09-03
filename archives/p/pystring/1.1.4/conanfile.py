#!/usr/bin/env python3
"""Conan recipe — pystring 1.1.4 (CMake)"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class PystringConan(ConanFile):
    name = "pystring"
    version = "1.1.4"
    description = "pystring is a collection of C++ functions which match the interface and behaviors of python's string methods"
    license = "MIT"
    homepage = "https://github.com/imageworks/pystring"
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
        get(self, **self.conan_data["sources"], strip_root=True, filename="pystring-1.1.4.tar.gz")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # pystring's CMakeLists.txt uses cmake_minimum_required(VERSION 3.2)
        # which is incompatible with CMake 4.x; this flag enables old policies
        # Must be passed as CLI arg, not toolchain var (needed before cmake_minimum_required)
        cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # CMakeLists.txt doesn't install headers; copy them manually
        copy(self, "pystring.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["pystring"]
