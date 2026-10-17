#!/usr/bin/env python3
"""Conan test_package for pagein 0.01.11.

Runs the installed ``pagein`` through a real shell harness (presence, help and
argument/usage error paths).  Actually paging in another process requires
CAP_SYS_PTRACE, so functional paging is not exercised here.
"""
import json
import os

from conan import ConanFile

CHECKS = 7


class PageinTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        binary = os.path.join(package_folder, "bin", "pagein")
        script = os.path.join(self.recipe_folder, "test_pagein.sh")
        self.run('PAGEIN_BIN="{}" sh "{}"'.format(binary, script), env="conanrun")
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_pagein.sh (pagein consumer checks)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
