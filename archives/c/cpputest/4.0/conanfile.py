#!/usr/bin/env python3
"""Conan recipe for CppUTest 4.0 on HarmonyOS PC.

CppUTest is a lightweight C/C++ unit test framework (plain CMake).
Built as a static library (libCppUTest.a + libCppUTestExt.a); its own
test suite is not part of the default CMake build (no add_subdirectory).
Consumers use it at build time only (e.g. WeeChat upstream unit tests).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches


class CpputestConan(ConanFile):
    name = "cpputest"
    version = "4.0"
    description = "CppUTest — C/C++ unit test framework (xUnit style)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/cpputest/cpputest"
    url = "https://github.com/cpputest/cpputest"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False], "with_extensions": [True, False]}
    default_options = {"shared": False, "fPIC": True, "with_extensions": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CPPUTEST_FLAGS"] = False      # use Conan-provided flags only
        tc.variables["MEMORY_LEAK_DETECTION"] = True
        tc.variables["EXTENSIONS"] = self.options.with_extensions
        tc.variables["WERROR"] = False
        tc.variables["COVERAGE"] = False
        tc.variables["MAP_FILE"] = False
        # R51: build the upstream dogfood suite (tests/CppUTest +
        # tests/CppUTestExt) and run it via ctest in build(); the framework's
        # build-time discovery registers one ctest entry per test case.
        tc.variables["TESTS"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # cpputest 4.0 declares cmake_minimum_required below 3.5; CMake >= 4
        # refuses to configure without this flag. It must be a command-line
        # cache variable (toolchain file loads only at project(), i.e. after
        # cmake_minimum_required has already been processed).
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()
        # R51: upstream tests must actually execute (CppUTestTests +
        # CppUTestExtTargets suites, atomic ctest entries via build-time
        # discovery). Failures propagate as a non-zero exit.
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        libs = ["CppUTest"]
        if self.options.with_extensions:
            libs.append("CppUTestExt")
        self.cpp_info.libs = libs
        self.cpp_info.set_property("pkg_config_name", "cpputest")
