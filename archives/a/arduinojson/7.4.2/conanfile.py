#!/usr/bin/env python3
"""Conan recipe for ArduinoJson 7.4.2 — header-only C++ JSON library.

ArduinoJson is a header-only library (INTERFACE CMake target). The package
installs the public headers under include/ and exposes cpp_info with the
include directory only; there is no compiled library.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class ArduinojsonConan(ConanFile):
    name = "arduinojson"
    version = "7.4.2"
    description = "ArduinoJson is a C++ JSON library for Arduino and IoT (7.4.2)"
    license = "MIT"
    homepage = "https://arduinojson.org"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Header-only library: the package build only installs headers. Do not
        # build the upstream test/fuzzing targets inside conan create; upstream
        # tests are verified separately and documented in test_package/MANIFEST.yml.
        cmake.configure(variables={"BUILD_TESTING": "OFF"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
