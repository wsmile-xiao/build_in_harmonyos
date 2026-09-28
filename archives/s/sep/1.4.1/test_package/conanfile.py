#!/usr/bin/env python3
"""Conan consumer tests for SEP 1.4.1 on HarmonyOS PC."""

import json
import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class SepTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "CMakeLists.txt", "*.c"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _run_target(self, name):
        executable = os.path.join(self.cpp.build.bindir, name)
        runner = self.conf.get(
            "user.sep:qemu_runner", default="", check_type=str
        ).strip()
        command = "{} {}".format(runner, shlex.quote(executable)).strip()
        self.run(command, env="conanrun")

    def test(self):
        self._run_target("test_sep")
        self._run_target("test_sep_errors")
        self._run_target("test_sep_ohos")
        marker = {
            "executed": True,
            "passed": True,
            "command": "test_sep && test_sep_errors && test_sep_ohos",
            "discovered": 3,
            "passedCount": 3,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
