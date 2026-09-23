#!/usr/bin/env python3
"""Conan test_package — vixl 5.1.0.

Builds a CMake consumer that links against the packaged static libvixl and
runs a real MacroAssembler/Decoder/Simulator round-trip.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class VixlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # OHOS toolchain binaries (clang / cmake / ninja) share one directory
        # (e.g. /data/service/hnp/bin); the test environment PATH may not
        # include it, so point CMake at cmake via the compiler's directory.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "")
        if cc:
            bindir = os.path.dirname(str(cc))
            if bindir:
                self.conf.define(
                    "tools.cmake:cmake_program", os.path.join(bindir, "cmake")
                )

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise Exception("No bindirs found — test binary was not built")
            bin_path = os.path.join(bindirs[0], "test_vixl")
            if not os.path.isfile(bin_path):
                raise Exception(f"Test binary not found: {bin_path}")
            self.run(f"\"{bin_path}\"", env="conanrun")
