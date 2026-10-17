#!/usr/bin/env python3
"""Conan recipe — clog 1.3.0 (CMake).

Clog is a colorized log tail utility: a filter that colorizes log files
according to rules in ~/.clogrc.
Build system: CMake. Upstream tarball bundles libshared submodule.
Upstream ships no test suite in the release tarball (see test_package/MANIFEST.yml).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
import os


class ClogConan(ConanFile):
    name = "clog"
    version = "1.3.0"
    description = "Colorized log tail utility, a filter that colorizes log files by rules"
    license = "MIT"
    homepage = "https://gothenburgbitfactory.org/clog/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

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
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Upstream declares cmake_minimum_required(VERSION 2.8). With CMake >= 4
        # the <3.5 compat was removed; CMAKE_POLICY_VERSION_MINIMUM must reach
        # CMake as a -D command-line definition (before CMakeLists is parsed).
        # Passing it via CMakeToolchain variables lands in the toolchain file,
        # which is read AFTER the cmake_minimum_required check, so it cannot
        # fix the configure error (true failure observed on HMBS CMake 4.4.3).
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()
        # No upstream test suite in the release tarball (test/ excluded from
        # CPack source, test_SRCS empty upstream). See test_package/MANIFEST.yml
        # audit; consumer tests in test_package/ cover the binary instead.

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
