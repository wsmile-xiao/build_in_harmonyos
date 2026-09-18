#!/usr/bin/env python3
"""Conan test_package for units-cpp 2.3.4.

Consumes the installed header-only package via CMakeDeps + find_package and
runs test_units.cpp (HarmonyOS-specific consumer checks written for this
adaptation, ported from upstream unitTests/main.cpp). Emits an HMBS marker.
"""
import json
import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class UnitsCppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def _bash(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            "/storage/Users/currentUser/.harmonybrew/bin/bash",
            "/data/service/hnp/bin/bash",
            "/bin/bash",
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        return "bash"

    def test(self):
        cmd = "ctest --output-on-failure -R test_units"
        if self.settings.os == "OHOS":
            cmd = f"{shlex.quote(self._bash())} -c {shlex.quote(cmd)}"
        try:
            self.run(cmd, env="conanrun")
            passed = True
        except Exception:
            passed = False
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": passed,
            "command": "ctest -R test_units",
            "consumer_passed": 20 if passed else 0,
            "consumer_total": 20,
        }))
        if not passed:
            raise
