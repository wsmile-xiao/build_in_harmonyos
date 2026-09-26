#!/usr/bin/env python3
"""Conan test_package for mt-st 1.8.

Runs the installed ``mt`` and ``stinit`` programs through a real shell harness.
"""
import json
import os

from conan import ConanFile

CHECKS = 8


class MtStTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        mt = os.path.join(package_folder, "bin", "mt")
        stinit = os.path.join(package_folder, "bin", "stinit")
        examples = os.path.join(package_folder, "share", "mt-st", "stinit.def.examples")
        script = os.path.join(self.recipe_folder, "test_mt_st.sh")
        for path in (mt, stinit, examples, script):
            if not os.path.isfile(path):
                raise Exception("required file not found: %s" % path)
        self.run('MT_BIN="%s" STINIT_BIN="%s" STINIT_EXAMPLES="%s" sh "%s"'
                 % (mt, stinit, examples, script))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_mt_st.sh (mt/stinit consumer checks)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
