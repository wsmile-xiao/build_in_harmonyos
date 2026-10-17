#!/usr/bin/env python3
"""Conan test_package for libblocksruntime 0.4.1.

Consumes the installed static runtime through CMakeDeps + find_package and
runs three consumers via CTest:
  * test_upstream   — the upstream 0.4.1 test (verbatim test/main.c)
  * test_blocks_c   — independent C consumer (block classes/lifecycle/byref)
  * test_blocks_cpp — C++ consumer, without an explicit -fblocks (proves the
                      packaged runtime propagates the flag)
"""
import json
import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibBlocksRuntimeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
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
        cmd = "ctest --output-on-failure"
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
            "command": "ctest (test_upstream, test_blocks_c, test_blocks_cpp)",
            "consumer_passed": 3 if passed else 0,
            "consumer_total": 3,
            "upstream_passed": 1 if passed else 0,
            "upstream_total": 1,
        }))
        if not passed:
            raise
