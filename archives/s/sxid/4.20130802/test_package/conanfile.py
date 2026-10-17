#!/usr/bin/env python3
"""Conan test_package for sxid 4.20130802 (executable).

Runs the real consumer script ``test_sxid.sh`` through ``ConanFile.run()``,
which drives the installed ``bin/sxid`` against a controlled tree and asserts
its auditing contract (additions, SHA-256/inode change, log mode/rotation,
listall, spotcheck) plus the host filesystem's S_ISUID/S_ISGID capability.
"""
import json
import os

from conan import ConanFile

CHECKS = 12


class SxidTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        exe = os.path.join(package_folder, "bin", "sxid")
        script = os.path.join(self.recipe_folder, "test_sxid.sh")
        if not os.path.isfile(exe):
            raise Exception("sxid binary not found in package: %s" % exe)
        if not os.path.isfile(script):
            raise Exception("test script not found: %s" % script)
        # self.run() raises when the script exits non-zero -> real execution.
        self.run('SXID_BIN="%s" sh "%s"' % (exe, script))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_sxid.sh (sxid -V/-h/first run/change run/listall/spotcheck)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
