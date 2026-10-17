#!/usr/bin/env python3
"""Conan consumer tests for libprotoc 31.1 (CMake)."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibprotocTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libprotoc's CMake config exposes absl/utf8_range targets that the
        # consumer has to be able to resolve, so pull the same dependencies in.
        self.requires("abseil-cpp/20260107.1")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()

        libprotoc = self.dependencies["libprotoc"]
        abseil = self.dependencies["abseil-cpp"]
        tc = CMakeToolchain(self)
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl"
        ).replace("\\", "/")
        tc.variables["Protobuf_DIR"] = os.path.join(
            libprotoc.package_folder, "lib", "cmake", "protobuf"
        ).replace("\\", "/")
        tc.variables["utf8_range_DIR"] = os.path.join(
            libprotoc.package_folder, "lib", "cmake", "utf8_range"
        ).replace("\\", "/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run(
                "ctest --output-on-failure --no-tests=error",
                cwd=self.build_folder,
                env="conanrun",
            )
