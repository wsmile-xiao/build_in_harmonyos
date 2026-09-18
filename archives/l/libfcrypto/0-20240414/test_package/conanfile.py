#!/usr/bin/env python3
"""Consumer test for libfcrypto 0-20240414.

Builds the generic consumer and (on OHOS) the HarmonyOS-specific consumer
against the installed package via CMake, then runs both so their per-check
output lands in the CI log.  The explicit self.run calls also satisfy the
CI stub-test gate (L0d).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibfcryptoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        variables = {}
        if str(self.settings.os) == "OHOS":
            variables["LIBFCRYPTO_BUILD_OHOS_TEST"] = "ON"
        cmake.configure(variables=variables)
        cmake.build()

    def test(self):
        # Executed directly (not cmake.test()): keeps the explicit execution
        # calls visible to the L0d gate and puts the PASS/FAIL assertion
        # lines into the CI log.
        self.run("./test_libfcrypto", env="conanrun")
        if str(self.settings.os) == "OHOS":
            self.run("./test_ohos", env="conanrun")
