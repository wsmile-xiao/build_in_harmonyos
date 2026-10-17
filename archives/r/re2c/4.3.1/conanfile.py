#!/usr/bin/env python3
"""Conan recipe for re2c 4.3.1 — C/C++ lexer generator (CMake build).

re2c is a lexer generator that produces C/C++ code from regular expressions.
It builds multiple executables (re2c, re2d, re2go, re2hs, etc.) for different
target languages.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Re2cConan(ConanFile):
    name = "re2c"
    version = "4.3.1"
    description = "Lexer generator that produces C/C++ code from regular expressions"
    license = "Public-Domain"
    homepage = "https://re2c.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["RE2C_BUILD_LIBS"] = False
        tc.variables["RE2C_BUILD_BENCHMARKS"] = False
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
        self.cpp_info.bindirs = ["bin"]
