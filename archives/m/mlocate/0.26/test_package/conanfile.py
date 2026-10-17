#!/usr/bin/env python3
"""Conan test_package for mlocate.

Runs the packaged ``locate`` and ``updatedb`` to create and query a database.
The package ``bin`` directory is injected into PATH explicitly, so the test is
independent of the shell startup files used by Conan to launch the script.
"""
import json
import os

from conan import ConanFile

CHECKS = 4


class MlocateTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = os.path.join(self.dependencies[self.tested_reference_str].package_folder, "bin")
        for tool in ("locate", "updatedb"):
            if not os.path.isfile(os.path.join(bindir, tool)):
                raise Exception("%s binary not found in package: %s" % (tool, bindir))
        script = os.path.join(self.recipe_folder, "test.sh")
        if not os.path.isfile(script):
            raise Exception("test script not found: %s" % script)
        self.run('MLOCATE_BINDIR="%s" bash "%s"' % (bindir, script))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "bash test.sh",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
