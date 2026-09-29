#!/usr/bin/env python3
"""Conan test_package — metashell 5.0.0.

Consumer test (R34): runs the installed bin/metashell binary via test.sh
(--help, wave empty startup, wave typedef smoke). The script itself prints
the HMBS_TEST_PACKAGE_RESULT marker with explicit PASS/FAIL accounting;
this conanfile only executes it and propagates the exit code.
"""
import os
import shutil

from conan import ConanFile


class MetashellTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        script = os.path.join(self.source_folder, "test.sh")
        self.run('%s -c "cd %s && sh %s"' % (bash, self.build_folder, script), env="conanrun")
