#!/usr/bin/env python3
"""Conan recipe — microsoft-proxy 4.0.1 (header-only C++20 INTERFACE library).

Downstream expects:
  find_package(msft_proxy4 REQUIRED)
  target_link_libraries(... PRIVATE msft_proxy4::proxy)

Header-only: no compiled artifacts; upstream CMake installs
include/proxy/*.h (+ v4/*.ixx module unit) and the msft_proxy4 CMake config.
Reference: archives/t/tsl-hopscotch-map/2.4.0/ (header-only CMake pattern).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class MsftProxy4Conan(ConanFile):
    name = "microsoft-proxy"
    version = "4.0.1"
    description = (
        "A library that accelerates C++ development by means of "
        "runtime polymorphism (header-only)"
    )
    license = "MIT"
    homepage = "https://github.com/microsoft/proxy"
    url = ""  # CI fills this
    topics = ("proxy", "runtime-polymorphism", "c++", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R32: OHOS is built with the Linux-family host semantics; upstream
        # CMake has no OHOS-specific logic beyond standard platform detection.
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Do not let the top-level project pull googletest/fmt/benchmarks/docs
        # via FetchContent inside the recipe build; tests run via test_package.
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["PROXY_BUILD_MODULES"] = False
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
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "msft_proxy4")
        self.cpp_info.set_property("cmake_target_name", "msft_proxy4::proxy")