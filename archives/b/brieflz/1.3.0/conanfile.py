#!/usr/bin/env python3
"""Conan recipe — brieflz 1.3.0 (CMake build, static library).

brieflz is a small fast Lempel-Ziv compression library with a pure-C
single-header public API (include/brieflz.h). Built with CMake, no
third-party dependencies.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BrieflzConan(ConanFile):
    name = "brieflz"
    version = "1.3.0"
    description = "BriefLZ - small fast Lempel-Ziv compression library"
    license = "MIT"
    homepage = "https://github.com/jibsen/brieflz"
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
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # CMake 4.x removed <3.5 compatibility; brieflz requires 2.8.11
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Run upstream test suite as part of conan create (L0e evidence)
        tc.variables["BRIEFLZ_BUILD_TESTING"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # brieflz CMakeLists requires CMake >= 2.8.11; CMake >= 4.0 removed
        # <3.5 compatibility, so pass CMAKE_POLICY_VERSION_MINIMUM explicitly
        # on the configure command line.
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()
        # Upstream test suite: test/test_brieflz.c via CTest (run in build phase
        # so CI/comsumers get upstream test evidence during conan create)
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["brieflz"]
        self.cpp_info.set_property("cmake_file_name", "brieflz")
        self.cpp_info.set_property("cmake_target_name", "brieflz::brieflz")