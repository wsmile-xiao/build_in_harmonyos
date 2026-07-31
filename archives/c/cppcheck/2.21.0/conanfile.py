#!/usr/bin/env python3
"""Conan recipe — cppcheck 2.21.0 (CMake, C++ static analysis tool)."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class CppcheckConan(ConanFile):
    name = "cppcheck"
    version = "2.21.0"
    license = "GPL-3.0-or-later"
    author = "cppcheck"
    url = "https://github.com/cppcheck-opensource/cppcheck"
    homepage = "https://cppcheck.sourceforge.io/"
    description = "Static analysis of C/C++ code"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_GUI"] = "OFF"
        tc.variables["BUILD_TESTS"] = "OFF"
        tc.variables["HAVE_RULES"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
