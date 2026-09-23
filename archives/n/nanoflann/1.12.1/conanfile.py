#!/usr/bin/env python3
"""Conan recipe — nanoflann 1.12.1 (CMake header-only library).

nanoflann is a C++ header-only library for KD-tree / KNN search. Upstream
installs a single header (include/nanoflann.hpp) plus the CMake package config
(nanoflann::nanoflann INTERFACE target); no binary is produced.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class NanoflannConan(ConanFile):
    name = "nanoflann"
    version = "1.12.1"
    description = "C++ header-only library for KD-tree / KNN search"
    license = "BSD-3-Clause"
    homepage = "https://github.com/jlblancoc/nanoflann"
    url = ""  # CI fills this

    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32: platform check must use `in ("Linux", "OHOS")`, not `== "Linux"`
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                f"nanoflann only supports Linux/OHOS/FreeBSD/Macos/Windows, current: {self.settings.os}")

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
        tc.variables["NANOFLANN_BUILD_EXAMPLES"] = "OFF"
        tc.variables["NANOFLANN_BUILD_TESTS"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # header-only: upstream unit tests (examples/ and tests/ are not built
        # as ALL targets here); runtime KNN verification is done in test_package.

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "nanoflann")
        self.cpp_info.set_property("cmake_target_name", "nanoflann::nanoflann")
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
