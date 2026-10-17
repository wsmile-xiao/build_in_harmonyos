#!/usr/bin/env python3
"""Conan recipe — tinyspline 0.6.0 (CMake build, C + C++ interfaces).

tinyspline is a small C library for NURBS/B-splines with an optional C++
interface. Build via upstream CMake with E063 fix:
  - OHOS sysroot math.h isinf() macro uses `long long` which triggers
    -Werror,-Wlong-long under upstream's -std=c89; disable error for this
    single category (E063: precise warning-class disable, not blanket -Werror).
  - Docs/examples disabled; tests kept for W3 verification.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TinysplineConan(ConanFile):
    name = "tinyspline"
    version = "0.6.0"
    description = "TinySpline is a small and convenient library for manipulating NURBS, B-Splines, and Bezier curves."
    license = "MIT"
    homepage = "https://github.com/msteinbeck/tinyspline"
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
        # E063: OHOS sysroot math.h isinf macro uses 'long long' under C89
        tc.variables["CMAKE_C_FLAGS"] = "-Wno-error=long-long"
        # R26: static by default; keep upstream defaults for the rest
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["TINYSPLINE_BUILD_EXAMPLES"] = "OFF"
        tc.variables["TINYSPLINE_BUILD_DOCS"] = "OFF"
        tc.variables["TINYSPLINE_BUILD_TESTS"] = "ON"
        # Normalize libdir (upstream GNUInstallDirs may pick lib64)
        tc.cache_variables["CMAKE_INSTALL_LIBDIR"] = "lib"
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
        self.cpp_info.libs = ["tinysplinecxx", "tinyspline"]
        # GNUInstallDirs may still pick lib64 on some toolchains; expose both
        self.cpp_info.libdirs = ["lib", "lib64"]