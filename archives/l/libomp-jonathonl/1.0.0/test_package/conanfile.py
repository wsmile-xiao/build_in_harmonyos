#!/usr/bin/env python3
"""Consumer and HarmonyOS-specific CMake tests for libomp-jonathonl."""

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibompJonathonlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["LIBOMP_JONATHONL_TEST_OHOS"] = self.settings.os == "OHOS"
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
