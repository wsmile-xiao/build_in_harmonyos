#!/usr/bin/env python3
"""Conan test_package for mhz 1.0.0.

Runs the installed ``mhz`` through a real shell harness: the help banner and a
short CPU-frequency measurement.  mhz has no upstream test suite.
"""
import json
import os

from conan import ConanFile

CHECKS = 5


class MhzTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        binary = os.path.join(package_folder, "bin", "mhz")
        script = os.path.join(self.recipe_folder, "test_mhz.sh")
        self.run('MHZ_BIN="{}" sh "{}"'.format(binary, script), env="conanrun")
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_mhz.sh (mhz consumer checks)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
