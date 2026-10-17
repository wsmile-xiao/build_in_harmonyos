#!/usr/bin/env python3
"""Conan test_package for simh 3.8.1.

SIMH V3.8-1 ships no unit-test suite, so this test exercises the *installed*
package from a consumer's perspective: it takes the tested package's bin/
directory and runs every emulator, asserting each starts, prints its SCP
banner and exits cleanly on the SCP `quit` command.

The test runs from the package bin/ (not the source tree), so a passing run
proves the packaged binaries are present, executable and functional.
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class SimhTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    generators = "VirtualRunEnv"

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(dep.package_folder, "bin")
        script = os.path.join(self.recipe_folder, "test_simh.py")
        # R34: actually execute the tested package's binaries.
        self.run(f'"{sys.executable}" "{script}" "{bindir}"', env="conanrun")
