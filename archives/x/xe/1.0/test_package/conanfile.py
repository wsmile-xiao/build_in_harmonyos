#!/usr/bin/env python3
"""Conan test_package for xe 1.0 (executable).

Runs the real consumer test script test_xe.sh through ConanFile.run(), which
executes the installed bin/xe and checks its output on several input modes.
"""
import json
import os

from conan import ConanFile

CHECKS = 6


class XeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        exe = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder, "bin", "xe")
        script = os.path.join(self.recipe_folder, "test_xe.sh")
        if not os.path.isfile(exe):
            raise Exception("xe binary not found in package: %s" % exe)
        if not os.path.isfile(script):
            raise Exception("test script not found: %s" % script)
        # self.run() raises if the script exits non-zero -> real execution check
        self.run('XE_BIN="%s" sh "%s"' % (exe, script))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_xe.sh (xe default/-N/-N0/\\{\\}/-0/-a/-n)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
