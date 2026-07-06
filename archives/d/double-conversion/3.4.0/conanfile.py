#!/usr/bin/env python3
"""Conan recipe for double-conversion 3.4.0 (CMake project).

double-conversion is a C++ library for binary-decimal decimal-binary conversion
routines for IEEE doubles. It is NOT a system same-name library, so it defaults
to shared linking (R26: only system same-name libraries must be static).

R32: settings.os judgment uses `in ("Linux", "OHOS")` not `== "Linux"`.
"""
import os
import shutil
import re

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class DoubleConversionConan(ConanFile):
    name = "double-conversion"
    version = "3.4.0"
    description = "Binary-decimal and decimal-binary conversion routines for IEEE doubles"
    license = "BSD-3-Clause"
    homepage = "https://github.com/google/double-conversion"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external dependencies (R27: use  for any deps)
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
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.generate()

        # Fix compiler paths in generated toolchain: conan profile may point to
        # /data/service/hnp/bin/clang which doesn't exist in dev environment.
        cc = shutil.which(os.environ.get("CC", "clang")) or "clang"
        cxx = shutil.which(os.environ.get("CXX", "clang++")) or "clang++"
        toolchain_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.isfile(toolchain_file):
            with open(toolchain_file, "r") as f:
                content = f.read()
            content = re.sub(
                r'set\(CMAKE_C_COMPILER "[^"]*"\)',
                f'set(CMAKE_C_COMPILER "{cc}")',
                content
            )
            content = re.sub(
                r'set\(CMAKE_CXX_COMPILER "[^"]*"\)',
                f'set(CMAKE_CXX_COMPILER "{cxx}")',
                content
            )
            with open(toolchain_file, "w") as f:
                f.write(content)

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
