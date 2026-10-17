#!/usr/bin/env python3
"""Conan recipe — spoa 4.1.5 (CMake, C++17).

spoa: SIMD partial order alignment library (rvaser).
Core library has zero external dependencies; SIMD code falls back to
scalar path on aarch64 (OHOS) without SIMDe. CLI (spoa_exe) and upstream
tests additionally require bioparser/biosoup which are not yet published
to the ohpcd registry, so this recipe builds the library only.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class SpoaConan(ConanFile):
    name = "spoa"
    version = "4.1.5"
    description = "Spoa is a c++ library (and tool) for SIMD vectorized partial order alignment"
    license = "MIT"
    homepage = "https://github.com/rvaser/spoa"
    url = ""  # CI fills this

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
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Library-only package: disable exe/tests (their deps not published)
        tc.variables["spoa_install"] = "ON"
        tc.variables["spoa_build_exe"] = "OFF"
        tc.variables["spoa_build_tests"] = "OFF"
        # Portability: never emit -march=native / -msse4.1 (breaks CI/OHOS)
        tc.variables["spoa_optimize_for_native"] = "OFF"
        tc.variables["spoa_optimize_for_portability"] = "OFF"
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
        self.cpp_info.libs = ["spoa"]