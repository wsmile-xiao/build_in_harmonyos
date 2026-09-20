#!/usr/bin/env python3
"""Conan L1 test package for disk-filltest 0.8.2 (command-line tool)."""

import os
import sys

from conan import ConanFile


class DiskFilltestTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        executable = os.path.join(dep.package_folder, "bin", "disk-filltest")
        script = os.path.join(self.recipe_folder, "test_disk_filltest.py")

        # No can_run() early return: the suite must fail when the package
        # binary is missing (R34 / CI L1e destructive check).
        self.run(
            '"%s" "%s" "%s"' % (sys.executable, script, executable),
            env="conanrun",
        )
