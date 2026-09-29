#!/usr/bin/env python3
"""Conan recipe — faster-utf8-validator (CMake).

The upstream repository is a single C file with a make.py build script.
This adaptation adds a CMakeLists.txt that builds the portable scalar
path (z_validate_utf8) on all targets; on x86 with -DAVX2/-DSSE4 the
same file exposes the SIMD variants, but the OHOS aarch64 build uses
the scalar fallback (no AVX2/SSE4 available on aarch64).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Fasterutf8ValidatorConan(ConanFile):
    name = "faster-utf8-validator"
    version = "cf482014d0"
    description = "Very fast UTF-8 validator (AVX2/SSE4 upstream, scalar fallback for OHOS aarch64)"
    license = "MIT"
    homepage = "https://github.com/zwegner/faster-utf8-validator"
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
        self.cpp_info.libs = ["zval"]
        self.cpp_info.set_property("cmake_file_name", "faster-utf8-validator")
        self.cpp_info.set_property("cmake_target_name", "faster-utf8-validator::faster-utf8-validator")
