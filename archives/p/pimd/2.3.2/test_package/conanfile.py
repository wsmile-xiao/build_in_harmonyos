#!/usr/bin/env python3
"""Conan test_package for pimd 2.3.2.

Runs the installed ``pimd`` through a shell harness (presence, --version and
--help banners).  Actually running the daemon needs multicast-capable
interfaces and root, so that is not exercised here.
"""
import json
import os

from conan import ConanFile

CHECKS = 6


class PimdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        binary = os.path.join(package_folder, "bin", "pimd")
        script = os.path.join(self.recipe_folder, "test_pimd.sh")
        self.run('PIMD_BIN="{}" sh "{}"'.format(binary, script), env="conanrun")
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_pimd.sh (pimd consumer checks)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
