#!/usr/bin/env python3
"""Conan test_package for lbt 1.2.2.

Exercises the installed ``lbt`` and ``lbt2dot`` filters: usage/error paths and
a real LTL translation piped into the GraphViz converter.
"""
import json
import os

from conan import ConanFile

CHECKS = 13


class LbtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        lbt = os.path.join(package_folder, "bin", "lbt")
        lbt2dot = os.path.join(package_folder, "bin", "lbt2dot")
        script = os.path.join(self.recipe_folder, "test_lbt.sh")
        for path in (lbt, lbt2dot, script):
            if not os.path.isfile(path):
                raise Exception("required file not found: %s" % path)
        self.run('LBT_BIN="%s" LBT2DOT_BIN="%s" sh "%s"' % (lbt, lbt2dot, script))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_lbt.sh (lbt/lbt2dot filters)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
