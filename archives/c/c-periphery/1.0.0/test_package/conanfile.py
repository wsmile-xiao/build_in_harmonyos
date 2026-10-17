#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class CPeripheryTestConan(ConanFile):
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
        # Runs the consumer binary. It links periphery.a and exercises the
        # core API + error-handling paths of all five subsystems. Expected to
        # PASS on hardware-less OHOS: every assertion verifies the real
        # no-hardware error semantics (error codes, errno, messages), which is
        # the verifiable surface in a CI build environment.
        if not cross_building(self):
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_periphery"),
                     env="conanrun")
