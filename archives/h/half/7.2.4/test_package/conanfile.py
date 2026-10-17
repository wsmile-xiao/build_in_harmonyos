#!/usr/bin/env python3
"""test_package - layer-2 consumer validation for half (ROCm 7.2.4).

Builds a real consumer translation unit that does ``#include <half/half.hpp>``,
exercises the half<->float conversions, arithmetic and numeric edge cases with
hard checks, then links against the Conan-generated ``half::half`` interface
target and RUNS the binary (R34/PF3: the test really uses the packaged API, it
is not a print-only shell).  ``test()`` executes it with ``env="conanrun"``.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class HalfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            binary = os.path.join(self.cpp.build.bindirs[0], "test_half")
            self.run(f'"{binary}"', env="conanrun")
        else:
            self.output.warning("test_half cannot run on this host")
