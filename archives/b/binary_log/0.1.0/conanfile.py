#!/usr/bin/env python3
"""Conan recipe for binary_log 0.1.0, a header-only C++20 logger."""
from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class BinarylogConan(ConanFile):
    name = "binary_log"
    version = "0.1.0"
    description = "Fast binary logger for C++"
    license = "MIT"
    homepage = "https://github.com/p-ranav/binary_log"
    url = "https://github.com/p-ranav/binary_log"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        # Header-only package contents do not vary with the build settings.
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4.1 on OHOS otherwise looks for the absent Platform/HarmonyOS.cmake.
        if self.settings.os in ("Linux", "OHOS"):
            if self.settings.os == "OHOS":
                tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # The upstream test target is gated by developer mode.  Keep optional
        # tools and examples out of the package build because they are not part
        # of the installed header-only library.
        tc.variables["BINARY_LOG_DEVELOPER_MODE"] = True
        tc.variables["BUILD_TESTING"] = True
        tc.variables["BUILD_UNPACKER"] = False
        tc.variables["BUILD_BENCHMARKS"] = False
        tc.variables["BUILD_EXAMPLES"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if not cross_building(self):
            cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "binary_log")
        self.cpp_info.set_property("cmake_target_name", "binary_log::binary_log")
        self.cpp_info.libs = []
        # Upstream installs headers below include/binary_log/; expose that
        # directory so consumers keep using <binary_log/binary_log.hpp>.
        self.cpp_info.includedirs = ["include/binary_log"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
