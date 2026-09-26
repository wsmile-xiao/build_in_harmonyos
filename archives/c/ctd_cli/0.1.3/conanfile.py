#!/usr/bin/env python3
"""Conan recipe for ctd_cli 0.1.3 (CMake, C++20, static library).

Upstream: https://gitlab.com/slavic-demons/korgorusze/compile_time_defined_cli
Adapted for HarmonyOS PC (arm64, OHOS, clang 15 / libc++).
Patch set replaces std::ranges algorithms (missing in LLVM 15 libc++)
with portable std:: algorithms.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class CtdcliConan(ConanFile):
    name = "ctd_cli"
    version = "0.1.3"
    description = "Compile time defined CLI - Modern C++20 Command Line Interface with strongly typed arguments"
    license = "MIT"
    homepage = "https://gitlab.com/slavic-demons/korgorusze/compile_time_defined_cli"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Upstream test/fuzzing/embedded targets are not part of the packaged library.
        tc.variables["CTD_CLI_TEST_BUILD"] = "OFF"
        tc.variables["CTD_CLI_FUZZING_TEST_BUILD"] = "OFF"
        tc.variables["CTD_CLI_EMBEDDED_TARGET_TEST_BUILD"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["ctd_cli"]
