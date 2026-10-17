#!/usr/bin/env python3
"""Conan test_package for tnef 1.4.18.

Runs the installed ``tnef`` CLI: --version, --help, and a graceful failure on a
missing input file.
"""
import json
import os

from conan import ConanFile

CHECKS = 3


class TnefTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        binary = os.path.join(package_folder, "bin", "tnef")
        script = os.path.join(self.recipe_folder, "test_tnef.sh")
        if not os.path.isfile(binary):
            raise Exception("tnef binary not found: %s" % binary)
        self.run('TNEF_BIN="%s" sh "%s"' % (binary, script))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_tnef.sh (--version/--help/missing input)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
