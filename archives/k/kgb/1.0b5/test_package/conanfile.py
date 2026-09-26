#!/usr/bin/env python3
"""Conan test_package for kgb 1.0b5.

Runs the installed ``kgb`` CLI: usage output and byte-exact compress/extract
round-trips (small file at -0, and the shipped LICENSE at the default level
with the deterministic archive checksum used by Debian's own test).
"""
import json
import os

from conan import ConanFile

CHECKS = 9


class KgbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        kgb = os.path.join(package_folder, "bin", "kgb")
        license_file = os.path.join(package_folder, "licenses", "LICENSE")
        script = os.path.join(self.recipe_folder, "test_kgb.sh")
        for path in (kgb, license_file, script):
            if not os.path.isfile(path):
                raise Exception("required file not found: %s" % path)
        self.run('KGB_BIN="%s" KGB_LICENSE="%s" sh "%s"' % (kgb, license_file, script))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_kgb.sh (kgb round-trip consumer checks)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
