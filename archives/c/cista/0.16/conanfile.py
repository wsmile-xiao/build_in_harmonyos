#!/usr/bin/env python3
"""Conan recipe — cista 0.16 (CMake header-only library).

cista is a simple, high-performance, zero-copy C++ serialization & reflection
library (header-only INTERFACE target). Upstream CMake installs only headers
plus the CMake package config; no binary is produced.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class CistaConan(ConanFile):
    name = "cista"
    version = "0.16"
    description = "A simple, high-performance, zero-copy C++ serialization & reflection library"
    license = "MIT"
    homepage = "https://github.com/felixguendling/cista"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32: platform check must use `in ("Linux", "OHOS")`, not `== "Linux"`
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                f"cista only supports Linux/OHOS/FreeBSD/Macos/Windows, current: {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        # header-only library: all settings combinations produce identical content
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake doesn't recognize OHOS as a target platform
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.variables["CISTA_INSTALL"] = "ON"
        tc.variables["CISTA_FMT"] = "OFF"      # avoid libfmt dependency
        tc.variables["CISTA_COVERAGE"] = "OFF"
        tc.variables["CISTA_USE_MIMALLOC"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # header-only: no linked binary; upstream test suite (cista-test) is
        # EXCLUDE_FROM_ALL and would need a runnable target, skipped here
        # (validated in the first-round Adapt by cross-compiling cista-test).

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cista")
        self.cpp_info.set_property("cmake_target_name", "cista::cista")
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
