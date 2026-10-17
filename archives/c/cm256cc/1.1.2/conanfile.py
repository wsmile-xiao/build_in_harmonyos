#!/usr/bin/env python3
"""Conan recipe — cm256cc 1.1.2 (CMake).

cm256cc is a fast GF(256) Cauchy MDS block erasure code library (C++11).
Upstream builds a SHARED library only. BUILD_TOOLS additionally builds the
upstream cm256_test / cm256_tx / cm256_rx tools; the tools are kept so the
upstream test binary ships with the package.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class Cm256ccConan(ConanFile):
    name = "cm256cc"
    version = "1.1.2"
    description = "Fast GF(256) Cauchy MDS block erasure code library for C++"
    license = "GPL-3.0-only"
    homepage = "https://github.com/f4exb/cm256cc"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cm256cc supports Linux/OHOS only, got {self.settings.os}"
            )
        if not self.options.shared:
            # upstream CMakeLists hardcodes add_library(cm256cc SHARED ...)
            raise ConanInvalidConfiguration(
                "cm256cc upstream builds a shared library only"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # ARM64 NEON is mandatory upstream; the CMakeLists enables it itself.
        # Keep the upstream test tools so cm256_test ships with the package.
        tc.variables["BUILD_TOOLS"] = True
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
        self.cpp_info.libs = ["cm256cc"]
        # upstream test/demo tools when BUILD_TOOLS is enabled
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "cm256cc")
        self.cpp_info.set_property("pkg_config_name", "libcm256cc")
        # The installed headers select their SIMD typedef block through the
        # same macro the library was compiled with; ARM64 builds use NEON via
        # sse2neon (mirrors the CMakeLists ARM64 branch).
        if str(self.settings.arch) in ("armv8", "armv8_64", "aarch64"):
            self.cpp_info.defines = ["USE_NEON"]
