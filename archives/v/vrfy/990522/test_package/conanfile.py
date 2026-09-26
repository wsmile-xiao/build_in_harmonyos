#!/usr/bin/env python3
"""Conan test_package for vrfy 990522.

Runs the installed ``vrfy`` CLI: ``-V`` (version) and the usage output when no
address is given.
"""
import json
import os

from conan import ConanFile

CHECKS = 2


class VrfyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        binary = os.path.join(package_folder, "bin", "vrfy")
        script = os.path.join(self.recipe_folder, "test_vrfy.sh")
        if not os.path.isfile(binary):
            raise Exception("vrfy binary not found: %s" % binary)
        self.run('VRFY_BIN="%s" sh "%s"' % (binary, script))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_vrfy.sh (-V/usage)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
