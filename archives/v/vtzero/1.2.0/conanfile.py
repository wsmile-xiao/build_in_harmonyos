#!/usr/bin/env python3
"""Conan recipe — vtzero 1.2.0 (CMake header-only library).

vtzero is a header-only C++14 library for decoding and encoding Mapbox
vector tiles. It provides an INTERFACE-style CMake target (no compiled
artifacts); install() places the headers only.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class VtzeroConan(ConanFile):
    name = "vtzero"
    version = "1.2.0"
    description = "Tiny and fast C++ library for decoding and encoding Mapbox vector tiles"
    license = "BSD-2-Clause"
    homepage = "https://github.com/mapbox/vtzero"
    url = "https://github.com/mapbox/vtzero"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps",

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # vtzero headers include <protozero/...>; upstream CMake requires
        # Protozero >= 1.7.0 via find_package.
        self.requires("protozero/1.8.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake does not recognize OHOS as a target platform
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Upstream build calls find_package(Protozero REQUIRED) and then does
        # include_directories(SYSTEM ${PROTOZERO_INCLUDE_DIR}); CMakeDeps CONFIG
        # mode defines protozero_INCLUDE_DIRS but not PROTOZERO_INCLUDE_DIR, so
        # point that variable at the Conan-managed protozero include dir.
        protozero = self.dependencies["protozero"]
        if protozero:
            inc_dirs = protozero.cpp_info.includedirs
            if inc_dirs:
                abs_incs = [os.path.join(protozero.package_folder, i) for i in inc_dirs]
                tc.cache_variables["PROTOZERO_INCLUDE_DIR"] = ";".join(abs_incs)
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
        self.cpp_info.libs = []
