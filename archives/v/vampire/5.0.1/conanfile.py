#!/usr/bin/env python3
"""Conan recipe for vampire 5.0.1 — CMake build system.

High-performance theorem prover.
License: BSD-3-Clause

R26: static linking for terminal tools (BUILD_SHARED_LIBS=OFF).
Note: OHOS-adapted Conan 2.29.1 automatically maps os=OHOS to
      CMAKE_SYSTEM_NAME=HarmonyOS, no manual override needed (E092).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class VampireConan(ConanFile):
    name = "vampire"
    version = "5.0.1"
    description = "High-performance theorem prover"
    license = "BSD-3-Clause"
    homepage = "https://github.com/vprover/vampire"
    url = ""  # CI fills this

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
        # R26: Terminal tools must be statically linked
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "vampire", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        # vampire is a binary tool, not a library
        self.cpp_info.bindirs = ["bin"]
