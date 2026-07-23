#!/usr/bin/env python3
"""Conan test_package for inih r58 — Conan L1 official test.

Uses CMake (CMakeDeps + CMakeToolchain) so the compiler is handled
by Conan toolchain, not raw shell env vars (R33).

Emits HMBS evidence markers for preflight verification:
  - HMBS_TEST_PACKAGE_RESULT: test_package consumer-side test results
  - HMBS_UPSTREAM_TEST_RESULT: upstream test suite status (no_tests)
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class InihTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()
        # Generate LD_LIBRARY_PATH for shared library runtime
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries.
        # Use bash to wrap binary execution.
        if self.settings.os == "OHOS":
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            cmd = f"{bash} -c './test_inih'"
        else:
            cmd = "./test_inih"

        rc = self.run(cmd, env="conanrun")
        passed = (rc == 0)

        # Emit HMBS evidence markers for preflight verification
        test_package_result = {
            "executed": True,
            "passed": passed,
            "command": cmd,
        }
        print(f"\nHMBS_TEST_PACKAGE_RESULT={json.dumps(test_package_result)}")

        # inih upstream unittest.sh generates baseline files rather than
        # validating test output; it requires Meson to compile test programs
        # separately. Not suitable for conan build integration.
        upstream_result = {
            "status": "no_tests",
            "framework": "none",
            "command": "N/A",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "inih upstream unittest.sh generates reference baseline files, not a test validator; requires separate Meson-based test compilation not integrated into conan recipe",
        }
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(upstream_result)}")
