#!/usr/bin/env python3
"""Conan test_package for memo 1.7.1.

Runs the installed ``memo`` CLI: --version, --help, and an add/list round-trip
in a temporary HOME.
"""
import json
import os

from conan import ConanFile

CHECKS = 3


class MemoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        binary = os.path.join(package_folder, "bin", "memo")
        script = os.path.join(self.recipe_folder, "test_memo.sh")
        if not os.path.isfile(binary):
            raise Exception("memo binary not found: %s" % binary)
        self.run('MEMO_BIN="%s" sh "%s"' % (binary, script))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_memo.sh (--version/--help/add+list)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
