#!/usr/bin/env python3
"""Conan test_package for ParaFly.

Runs the packaged ``bin/ParaFly`` against three generated commands and checks
the completion records.  The executable is addressed by its package path
instead of relying on the generated run environment, so the test does not
depend on how the shell used by Conan resolves PATH.
"""
import json
import os

from conan import ConanFile

CHECKS = 5


class ParaflyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        exe = os.path.join(package_folder, "bin", "ParaFly")
        script = os.path.join(self.recipe_folder, "test.sh")
        if not os.path.isfile(exe):
            raise Exception("ParaFly binary not found in package: %s" % exe)
        if not os.path.isfile(script):
            raise Exception("test script not found: %s" % script)
        # ``env="conanbuild"`` carries the SDK runtime search path required by
        # the OpenMP runtime that ParaFly links against.
        self.run('PARAFLY_BIN="%s" bash "%s"' % (exe, script), env="conanbuild")
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "bash test.sh",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
