#!/usr/bin/env python3
"""Consumer-side API test for libavtp."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibavtpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
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
        if not can_run(self):
            self.output.info(
                "Cross build: libavtp consumer was built; run it on the "
                "HarmonyOS PC target."
            )
            return
        executable = os.path.join(self.cpp.build.bindirs[0], "test_libavtp")
        self.run(executable, env="conanrun")
