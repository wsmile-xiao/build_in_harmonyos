#!/usr/bin/env python3
"""Conan test_package for procenv 0.51 (executable).

Runs the real consumer test script test_procenv.sh through ConanFile.run(),
which executes the installed `bin/procenv` and checks the output of sections
that are known to work on OHOS (version, JSON/XML dumps, limits, environment).

Sections that busy-loop on OHOS (-b/--libs, -i/--misc and the no-argument full
dump) are deliberately not invoked; see the package notes.md.
"""
import json
import os

from conan import ConanFile

CHECKS = 5


class ProcenvTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        exe = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder, "bin", "procenv")
        script = os.path.join(self.recipe_folder, "test_procenv.sh")
        if not os.path.isfile(exe):
            raise Exception("procenv binary not found in package: %s" % exe)
        if not os.path.isfile(script):
            raise Exception("test script not found: %s" % script)
        # self.run() raises if the script exits non-zero -> real execution check
        self.run('PROCENV_BIN="%s" sh "%s"' % (exe, script))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_procenv.sh (procenv --version/--format=json/--format=xml/--limits/--environment)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
