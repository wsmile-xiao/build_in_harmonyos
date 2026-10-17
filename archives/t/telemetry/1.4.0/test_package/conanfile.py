#!/usr/bin/env python3
"""Conan test_package for telemetry 1.4.0 — the L1 official test.

Consumes the packaged libraries from a downstream CMake project and runs two
test cases with CTest:

  * test_telemetry_consumer — core telemetry API (tree, files, content)
  * test_appfs_ohos         — HarmonyOS specific: FUSE3/off_t contract that
                              appFs publishes plus DT_SONAME loading of the
                              packaged shared libraries
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class TelemetryTestConan(ConanFile):
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
        # Run the consumer tests with CTest. The invocation is explicit so that
        # the test really depends on the packaged artifacts (R34/L0d).
        self.run("ctest --output-on-failure", cwd=self.build_folder, env="conanrun")
