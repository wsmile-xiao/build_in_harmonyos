#!/usr/bin/env python3
"""Consumer and HarmonyOS tests for pnglite 0.1.17."""
import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PngliteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        runner = os.environ.get("OHOS_TEST_RUNNER", "").strip()
        for test_binary in ("test_pnglite", "harmonyos_specific_test"):
            path = os.path.join(self.cpp.build.bindirs[0], test_binary)
            command = f"{runner} {shlex.quote(path)}" if runner else path
            self.run(command, env="conanrun")
