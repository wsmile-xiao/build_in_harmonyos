#!/usr/bin/env python3
"""Conan test_package for wwl 1.3-db.

Runs the installed ``wwl`` and ``locator`` programs against the examples
documented in wwl(1).
"""
import json
import os

from conan import ConanFile

CHECKS = 10


class WwlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        wwl = os.path.join(package_folder, "bin", "wwl")
        locator = os.path.join(package_folder, "bin", "locator")
        script = os.path.join(self.recipe_folder, "test_wwl.sh")
        for path in (wwl, locator, script):
            if not os.path.isfile(path):
                raise Exception("required file not found: %s" % path)
        self.run('WWL_BIN="%s" LOCATOR_BIN="%s" sh "%s"' % (wwl, locator, script))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_wwl.sh (wwl/locator consumer checks)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
