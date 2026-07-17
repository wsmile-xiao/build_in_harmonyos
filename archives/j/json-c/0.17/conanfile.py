#!/usr/bin/env python3
"""Conan recipe - json-c 0.17 (CMake)"""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import get


class JsonCConan(ConanFile):
    name = "json-c"
    version = "0.17"
    url = "https://github.com/json-c/json-c"
    description = "JSON implementation in C"
    license = "MIT"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_TESTING"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["json-c"]