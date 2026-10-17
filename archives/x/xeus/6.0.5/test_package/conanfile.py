#!/usr/bin/env python3
"""Test package for xeus 6.0.5.

Tests that the xeus library can be consumed by a downstream project:
1. CMake find_package(xeus) works
2. Headers are installed correctly
3. Library links successfully
4. Basic API usage (xinterpreter inheritance, xjson utilities)
5. OHOS consumer test: verify xeus kernel protocol types are usable
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import copy


class XeusTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # nlohmann_json needed for test compilation (transitive header dependency)
        self.requires("nlohmann_json/3.12.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Test 1: C++ test executable that links xeus and uses API
        test_exe = os.path.join(self.cpp.build.bindirs[0], "test_xeus_consumer")
        if os.path.isfile(test_exe):
            self.run(test_exe, env="conanrun")

        # Test 2: OHOS-specific consumer test (type usability probe)
        # Verify that xeus types can be instantiated and used in a
        # real consumer scenario (kernel protocol message handling).
        ohos_test = os.path.join(self.cpp.build.bindirs[0], "test_ohos_xeus")
        if os.path.isfile(ohos_test):
            self.run(ohos_test, env="conanrun")
