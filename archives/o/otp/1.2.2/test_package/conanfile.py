#!/usr/bin/env python3
"""Conan test_package for otp 1.2.2 (executable).

Runs the real consumer test script test_otp.sh through ConanFile.run(), which
executes the installed bin/otp and checks deterministic output plus the MD5
signature file against known-good values.
"""
import json
import os

from conan import ConanFile

CHECKS = 4


class OtpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        exe = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder, "bin", "otp")
        script = os.path.join(self.recipe_folder, "test_otp.sh")
        if not os.path.isfile(exe):
            raise Exception("otp binary not found in package: %s" % exe)
        if not os.path.isfile(script):
            raise Exception("test script not found: %s" % script)
        # self.run() raises if the script exits non-zero -> real execution check
        self.run('OTP_BIN="%s" sh "%s"' % (exe, script))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_otp.sh (otp -U / -rTEST -n4 / -m md5 / -n7 -d4)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
