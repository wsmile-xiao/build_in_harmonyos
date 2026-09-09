#!/usr/bin/env python3
"""Conan recipe — libcsptr 2.0.4 (CMake, pure C static library).

Upstream: https://github.com/Snaipe/libcsptr
Build system: CMake (add_library(csptr STATIC ...)); header + smalloc/sfree API.
R26: static-only for system-name library (no shared install targets upstream).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibcsptrConan(ConanFile):
    name = "libcsptr"
    version = "2.0.4"
    description = "libcsptr 2.0.4 — C smart pointer library"
    license = "MIT"
    homepage = "https://github.com/Snaipe/libcsptr"
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
        # R26: system-name library defaults to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Upstream CMakeLists declares cmake_minimum_required(VERSION 2.8);
        # CMake >= 4.0 removed <3.5 compatibility, so pin the policy floor
        # via command-line cache (CMakeToolchain filters policy variables).
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["csptr"]
