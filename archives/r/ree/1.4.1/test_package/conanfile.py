#!/usr/bin/env python3
"""Conan test_package for ree 1.4.1.

``fontdump`` is exercised on a synthetic ROM image (a valid 8x8 VGA font
block) and checked byte-for-byte; ``ree`` is run and must terminate with its
known /dev/mem or scanning banner.
"""
import json
import os

from conan import ConanFile

CHECKS = 9


class ReeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        ree = os.path.join(package_folder, "bin", "ree")
        fontdump = os.path.join(package_folder, "bin", "fontdump")
        script = os.path.join(self.recipe_folder, "test_ree.sh")
        for path in (ree, fontdump, script):
            if not os.path.isfile(path):
                raise Exception("required file not found: %s" % path)
        self.run('REE_BIN="%s" FONTDUMP_BIN="%s" sh "%s"' % (ree, fontdump, script))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_ree.sh (fontdump ROM scan + ree run)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
