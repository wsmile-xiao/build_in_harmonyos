#!/usr/bin/env python3
"""Consumer test for the itsy_bitsy/0.8 header-only Conan package (CMake)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class ItsyBitsyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_CXX_STANDARD"] = "17"
        tc.cache_variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        if self.settings.os in ("Linux", "OHOS"):
            # CMake has no HarmonyOS platform module; the OHOS clang toolchain
            # stays in use, only the platform name is mapped to the compatible
            # Unix branch.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Print the failing case's own assertion output in the log.  It must be
        # a plain string: a Python list is serialised as its repr into the
        # generated "make test" rule and ctest then rejects it.
        tc.cache_variables["CMAKE_CTEST_ARGUMENTS"] = "--output-on-failure"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "2"], build_tool_args=["-j2"])

    def test(self):
        # 5 behavioural cases registered in CMakeLists.txt (CTest).  Keep the
        # consumer suite on the same -j2 budget as the main recipe: bare
        # cmake.test() would inject the profile's tools.build:jobs (-j20).
        cmake = CMake(self)
        cmake.test(build_tool_args=["-j2"])
        # Direct execution of the consumer binary, independent of CTest.
        binary = os.path.join(self.cpp.build.bindirs[0], "test_itsy_bitsy")
        self.run(f'"{binary}" bit_span', env="conanrun")
