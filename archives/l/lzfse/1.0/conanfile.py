#!/usr/bin/env python3
"""Conan recipe for lzfse — LZFSE compression library by Apple.

lzfse uses CMake as its build system. This recipe builds the static library
and command-line tool.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LzfseConan(ConanFile):
    name = "lzfse"
    version = "1.0"
    description = "LZFSE compression library and command line tool by Apple"
    license = "BSD-3-Clause"
    homepage = "https://github.com/lzfse/lzfse"
    url = "https://github.com/lzfse/lzfse"

    package_type = "library"

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
        tc.variables["LZFSE_DISABLE_TESTS"] = True
        # CMake 4.x removed compat with < 3.5; lzfse's CMakeLists declares 2.8.6
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
        self.cpp_info.set_property("cmake_target_name", "lzfse::lzfse")
        self.cpp_info.libs = ["lzfse"]
