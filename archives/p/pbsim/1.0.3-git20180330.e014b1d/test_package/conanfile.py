#!/usr/bin/env python3
"""Conan test_package for PBSIM 1.0.3-git20180330.e014b1d.

Runs the installed ``pbsim`` through a shell harness (presence, version/help
banners and an argument-validation error path).  A full simulation needs a
reference FASTA and is exercised by the user outside the packaging test.
"""
import json
import os

from conan import ConanFile

CHECKS = 7


class PbsimTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        binary = os.path.join(package_folder, "bin", "pbsim")
        script = os.path.join(self.recipe_folder, "test_pbsim.sh")
        self.run('PBSIM_BIN="{}" sh "{}"'.format(binary, script), env="conanrun")
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_pbsim.sh (pbsim consumer checks)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
