#!/usr/bin/env python3
"""Conan recipe for jansson — CMake build system.

Jansson is a C library for encoding, decoding and manipulating JSON data.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.layout import basic_layout


class JanssonConan(ConanFile):
    name = "jansson"
    version = "2.15.1"
    description = "C library for encoding, decoding and manipulating JSON data"
    license = "MIT"
    homepage = "https://github.com/akheron/jansson"
    url = "https://github.com/akheron/jansson"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

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
        tc.variables["JANSSON_BUILD_SHARED_LIBS"] = self.options.shared
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["jansson"]
