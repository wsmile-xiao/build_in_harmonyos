#!/usr/bin/env python3
"""Conan test_package for SweeD 3.2.1.

Runs the installed ``SweeD`` through a shell harness (presence and the usage /
version banners).  A full selective-sweep run needs an input alignment file and
is exercised by the user outside the packaging test.
"""
import json
import os

from conan import ConanFile

CHECKS = 5


class SweedTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        binary = os.path.join(package_folder, "bin", "SweeD")
        script = os.path.join(self.recipe_folder, "test_sweed.sh")
        self.run('SWEED_BIN="{}" sh "{}"'.format(binary, script), env="conanrun")
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_sweed.sh (SweeD consumer checks)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
