#!/usr/bin/env python3
"""Test the installed static library through its public C interface."""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import can_run


class LibdumbTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["LIBDUMB_TEST_OHOS"] = str(self.settings.os) == "OHOS"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_dumb"), env="conanrun")
            if str(self.settings.os) == "OHOS":
                self.run(os.path.join(self.cpp.build.bindirs[0], "test_ohos_storage"),
                         env="conanrun")
