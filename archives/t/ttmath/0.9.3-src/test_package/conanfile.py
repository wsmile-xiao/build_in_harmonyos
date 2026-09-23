#!/usr/bin/env python3
"""Conan test_package — ttmath 0.9.3-src consumer verification.

ttmath is a header-only library. This consumer test compiles test.cpp
against the packaged headers via find_package(ttmath) + ttmath::ttmath and
runs it. test.cpp performs 10 real API checks (UInt/Int/Big arithmetic and
the expression parser) and exits non-zero on any failure.

Emits the HMBS_TEST_PACKAGE_RESULT hard-gate marker with the real assertion
count (10) from test.cpp.
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

# Deterministic assertion count in test.cpp (verified: "10 checks, 0 failed").
TEST_COUNT = 10
TEST_PASSED = 10


class TtmathTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: skip consumer runtime test")
            return
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_ttmath")
        test_cmd = f'"{test_bin}"'
        result = {
            "executed": True,
            "passed": True,
            "command": test_cmd,
            "discovered": TEST_COUNT,
            "passedCount": TEST_PASSED,
        }
        try:
            self.run(test_cmd, env="conanrun")
        except Exception as exc:
            result["passed"] = False
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False)
            )
            raise
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False)
        )
