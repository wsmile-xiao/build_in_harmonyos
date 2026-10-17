#!/usr/bin/env python3
"""Conan test_package for sic 1.3 (executable).

Runs the real consumer test script test_sic.sh through ConanFile.run(), which
executes the installed bin/sic: version/usage/connection-error paths plus a
full IRC registration handshake (NICK/USER + PING/PONG) against a local server.
"""
import json
import os

from conan import ConanFile

CHECKS = 6


class SicTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        exe = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder, "bin", "sic")
        script = os.path.join(self.recipe_folder, "test_sic.sh")
        if not os.path.isfile(exe):
            raise Exception("sic binary not found in package: %s" % exe)
        if not os.path.isfile(script):
            raise Exception("test script not found: %s" % script)
        # self.run() raises if the script exits non-zero -> real execution check
        self.run('SIC_BIN="%s" sh "%s"' % (exe, script))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_sic.sh (sic -v / -Z / -h 127.0.0.1 -p 1 / IRC handshake)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
