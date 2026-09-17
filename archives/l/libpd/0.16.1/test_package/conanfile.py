#!/usr/bin/env python3
"""Consumer test for libpd 0.16.1 (real C API / DSP usage).

Builds libpd_test.c against the installed libpd target and runs it: the
program loads the fixture patch, round-trips a bang and a float through
bound receivers, and processes a real [osc~ 440] -> [dac~] signal chain.
The process exits non-zero if any assertion fails.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy


class LibpdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # CMake has no OHOS platform module; the OHOS clang is
            # Linux-compatible and targets aarch64-linux-ohos by default.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        # The fixture patch is loaded at runtime from the build folder.
        copy(self, "*.pd", self.source_folder, self.build_folder)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        executable = os.path.join(self.cpp.build.bindirs[0], "libpd_test")
        # libpd_openfile(name, dir) resolves name relative to dir, so pass the
        # fixture basename plus the folder that holds it.
        self.run(
            f'"{executable}" libpdtest.pd "{self.build_folder}"',
            env="conanrun",
            cwd=self.build_folder,
        )
