#!/usr/bin/env python3
"""Conan recipe for pika (PikaPython) 1.14.0 — CMake build system.

PikaPython is an ultra-lightweight C-language Python interpreter kernel.
The upstream CMakeLists.txt compiles src/*.c into a static library
pika-core and installs headers to include/pika.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PikaConan(ConanFile):
    name = "pika"
    version = "1.14.0"
    description = "Ultra-lightweight C-language Python interpreter kernel"
    license = "MIT"
    homepage = "https://github.com/pikasTech/PikaPython"
    url = "https://github.com/pikasTech/PikaPython"

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
        # PikaPython builds as a static library (pika-core)
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
        self.cpp_info.libs = ["pika-core"]
        self.cpp_info.includedirs = ["include/pika"]
