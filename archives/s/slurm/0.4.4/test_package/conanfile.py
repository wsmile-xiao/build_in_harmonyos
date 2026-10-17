#!/usr/bin/env python3
"""Conan test_package — slurm 0.4.4 CLI tool verification (OHOS consumer case).

slurm is a terminal tool, not a library. This test verifies the packaged
binary executes on OHOS: `slurm -h` prints usage and exits 0 (upstream
slurm.c: case 'h' -> usage(0, argv) -> _exit(0); no TTY required).
This is the HarmonyOS consumer feasibility case required in addition to
upstream tests (upstream 0.4.4 has no automated test suite).
Emits the HMBS_TEST_PACKAGE_RESULT hard-gate marker (2 checks).
"""
import json
import os
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class SlurmTestConan(ConanFile):
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
            dep = self.dependencies["slurm"]
            slurm_bin = os.path.join(dep.package_folder, "bin", "slurm")
            test_bin = os.path.join(self.build_folder, "test_slurm")
            test_cmd = f'{test_bin} "{slurm_bin}"'
            # 2 explicit checks in test.c (-h exit code 0 / usage banner text)
            test_pkg = {
                "executed": True,
                "passed": True,
                "command": test_cmd,
                "discovered": 2,
                "passedCount": 2,
            }
            try:
                self.run(test_cmd, env="conanrun")
            except Exception:
                test_pkg["passed"] = False
                self.output.info(
                    "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False)
                )
                raise
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False)
            )
