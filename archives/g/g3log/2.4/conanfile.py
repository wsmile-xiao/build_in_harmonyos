#!/usr/bin/env python3
"""Conan recipe — g3log 2.4 (CMake project).

g3log is a C++ logging library; upstream CMakeLists.txt declares
cmake_minimum_required(3.2), which CMake >= 4.0 refuses without an explicit
policy floor, so we set CMAKE_POLICY_VERSION_MINIMUM=3.5 at configure time.
FindBacktrace on the HarmonyOS sysroot needs the include dir passed
explicitly (execinfo.h lives under the OHOS sysroot usr/include).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class G3LogConan(ConanFile):
    name = "g3log"
    version = "2.4"
    description = "g3log is a C++11 logging library that is focused on asynchronous, crash-safe logging"
    license = "MIT"
    homepage = "https://github.com/KjellKod/g3log"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "with_tests": [True, False]}
    default_options = {"shared": False, "with_tests": False}

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
        # CMake >= 4.0 removes compatibility with cmake_minimum_required < 3.5
        # (upstream CMakeLists.txt bumped via patches/0003-CMakeLists.txt.patch)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Upstream unit tests are gtest-based; keep them out of the library package
        tc.variables["ADD_G3LOG_UNIT_TEST"] = "ON" if self.options.with_tests else "OFF"
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
        self.cpp_info.libs = ["g3log"]