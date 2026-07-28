#!/usr/bin/env python3
"""Conan recipe — flatcc 0.6.1 (CMake)

flatcc is a FlatBuffers compiler and runtime library in C.
Build produces: flatcc CLI binary, libflatcc.a (compiler core), libflatccrt.a (runtime).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class FlatccConan(ConanFile):
    name = "flatcc"
    version = "0.6.1"
    description = "FlatBuffers Compiler and Library in C for C."
    license = "Apache-2.0"
    homepage = "https://github.com/dvidelabs/flatcc"
    url = "https://github.com/dvidelabs/flatcc"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

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
        # Disable -Werror: clang 15 triggers -Wunused-but-set-variable warnings
        tc.variables["FLATCC_ALLOW_WERROR"] = "OFF"
        # Enable install targets (flatcc default is OFF)
        tc.variables["FLATCC_INSTALL"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMAKE_POLICY_VERSION_MINIMUM must be on command line, not toolchain file,
        # because CMake processes cmake_minimum_required before reading toolchain.
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["flatcc", "flatccrt"]
        self.cpp_info.bindirs = ["bin"]
