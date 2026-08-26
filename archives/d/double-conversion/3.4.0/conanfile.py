#!/usr/bin/env python3
"""Conan recipe for double-conversion 3.4.0 (CMake project).

double-conversion is a C++ library for binary-decimal decimal-binary conversion
routines for IEEE doubles. It is NOT a system same-name library, so it defaults
to shared linking (R26: only system same-name libraries must be static).

R32: settings.os judgment uses `in ("Linux", "OHOS")` not `== "Linux"`.
R33: compiler paths come from Conan profile (tools.build:compiler_executables),
     no shell env vars or manual toolchain rewriting.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class DoubleConversionConan(ConanFile):
    name = "double-conversion"
    version = "3.4.0"
    description = "Binary-decimal and decimal-binary conversion routines for IEEE doubles"
    license = "BSD-3-Clause"
    homepage = "https://github.com/google/double-conversion"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "library"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external dependencies
        pass

    def layout(self):
        # Use "_build" instead of default "build" to avoid conflict with
        # the Bazel BUILD file on case-insensitive HMDFS filesystem (R21)
        cmake_layout(self, build_folder="_build")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # double-conversion is NOT a system same-name library -> default shared (R26)
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_TESTING"] = False
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
        self.cpp_info.libs = ["double-conversion"]
        # R32: settings.os judgment must use `in ("Linux", "OHOS")`
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = []
