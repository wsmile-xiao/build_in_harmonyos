#!/usr/bin/env python3
"""Conan test_package — astroterm 1.0.9 CLI tool verification.

astroterm is a terminal tool, not a library. This test verifies
the binary is installed and can execute (--version / --help).
Emits the HMBS_TEST_PACKAGE_RESULT hard-gate marker with the real
assertion count from test.c (2 checks).
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class AstrotermTestConan(ConanFile):
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
        if can_run(self):
            dep = self.dependencies["astroterm"]
            astroterm_bin = os.path.join(dep.package_folder, "bin", "astroterm")
            test_bin = os.path.join(self.build_folder, "test_astroterm")
            test_cmd = f'{test_bin} "{astroterm_bin}"'
            # 2 explicit checks in test.c (--version / --help)
            test_pkg = {
                "executed": True,
                "passed": True,
                "command": test_cmd,
                "discovered": 2,
                "passedCount": 2,
            }
            try:
                self.run(test_cmd, env="conanrun")
            except Exception as exc:
                test_pkg["passed"] = False
                self.output.info(
                    "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False)
                )
                raise
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False)
            )
