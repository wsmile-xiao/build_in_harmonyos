#!/usr/bin/env python3
"""Consumer test for lib60870 2.4.0 (CMake).

Runs the test binary natively when the host can execute OHOS/armv8
binaries; otherwise only builds (cross CI)."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class Lib60870TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

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
            test_binary = os.path.join(self.cpp.build.bindirs[0], "test_lib60870")
            self.run(test_binary, env="conanrun")
